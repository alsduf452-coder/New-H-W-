import hashlib
from pathlib import Path
from unittest.mock import Mock
import pytest
import requests
from fastapi.testclient import TestClient
from sync_api import create_app
from cloud_store import Repository, ConflictError
from domain import FIELDS
from excel_sync import pending_excel, MAX_FILE
from sample_data import sample_items
from local_sync.agent import sync_once, stable_read, load_config, SyncError

TOKEN = 'test-token-' + 'x'*40


def client_and_repo(mapping=None):
    repo = Repository()
    client = TestClient(create_app(repo, TOKEN, mapping=mapping or {}))
    return client, repo


def send(client, content, revision=0):
    return client.post('/v1/source/workbook', content=content, headers={'Authorization': 'Bearer '+TOKEN, 'If-Match': str(revision), 'Content-Type': 'application/octet-stream', 'X-Content-SHA256': hashlib.sha256(content).hexdigest()})


def status(client):
    return client.get('/v1/source/status', headers={'Authorization':'Bearer '+TOKEN}).json()


def test_auth_and_missing_configuration_fail_closed(monkeypatch):
    monkeypatch.delenv('SYNC_TOKEN', raising=False)
    with pytest.raises(ValueError, match='SYNC_TOKEN'):
        create_app()
    client, repo=client_and_repo()
    assert client.get('/v1/source/status').status_code==401
    assert client.post('/v1/source/workbook', content=b'private').status_code==401
    assert repo.list_items()==[]


def test_ingest_persists_previews_pending_audit_and_rejects_stale_upload():
    client, repo=client_and_repo(); rows=sample_items()
    response=send(client,pending_excel(rows))
    assert response.status_code==200
    assert response.json()['pending_status']=='applied'
    assert len(repo.list_items())==3
    assert 'PENDING' in repo.local_previews('local-excel')
    assert repo.list_events()[0]['actor']=='local-excel-sync'
    rows[0]['내용']='로컬에서 변경'
    assert send(client,pending_excel(rows),0).status_code==409
    assert repo.local_status('local-excel')['revision']==1
    assert send(client,pending_excel(rows),1).status_code==200
    assert repo.list_items()[0]['내용']=='로컬에서 변경'
    assert repo.list_items()[0]['버전']==2


def test_mapping_warning_retains_preview_and_existing_pending():
    client, repo=client_and_repo({'pending_sheet':'없는 시트'})
    repo.save_item(sample_items()[0], 'existing')
    response=send(client,pending_excel(sample_items()))
    assert response.status_code==200
    assert response.json()['pending_status']=='mapping_required'
    assert len(repo.list_items())==1
    assert repo.local_previews('local-excel')


def test_corrupt_oversized_or_modified_body_cannot_change_database():
    client, repo=client_and_repo()
    assert send(client,b'not an excel file').status_code==422
    content=pending_excel(sample_items())
    headers={'Authorization':'Bearer '+TOKEN,'If-Match':'0','Content-Type':'application/octet-stream','X-Content-SHA256':'wrong'}
    assert client.post('/v1/source/workbook',content=content,headers=headers).status_code==400
    headers['Content-Length']=str(MAX_FILE+1)
    assert client.post('/v1/source/workbook',content=b'',headers=headers).status_code==413
    assert repo.local_status('local-excel')=={'revision':0}
    assert not repo.list_items()


def test_conflict_keeps_pending_and_snapshot_but_shows_latest_preview():
    client,repo=client_and_repo(); rows=sample_items()
    send(client,pending_excel(rows))
    old_snapshot=repo.source_snapshot('local:local-excel')
    repo.save_item(dict(rows[0],내용='앱 편집'),'editor',1)
    rows[0]['내용']='Excel 편집';rows[1]['내용']='동반 변경'
    response=send(client,pending_excel(rows),1)
    assert response.json()['pending_status']=='conflict'
    assert repo.list_items()[0]['내용']=='앱 편집'
    assert repo.list_items()[1]['내용']!='동반 변경'
    assert repo.source_snapshot('local:local-excel')==old_snapshot
    assert status(client)['resend_required']
    assert any('Excel 편집' in row for row in repo.local_previews('local-excel')['PENDING']['rows'])


def test_ingestion_failure_rolls_back_baseline_preview_and_items(monkeypatch):
    client,repo=client_and_repo()
    original=repo.apply_plan
    def fail(*args,**kwargs):
        original(*args,**kwargs)
        raise ConflictError('injected transaction failure')
    monkeypatch.setattr(repo,'apply_plan',fail)
    response=send(client,pending_excel(sample_items()))
    assert response.status_code==409
    assert repo.local_status('local-excel')=={'revision':0}
    assert repo.source_snapshot('local:local-excel') is None
    assert repo.list_items()==[]
    assert repo.list_events()==[]


class AgentTransport:
    def __init__(self, client):
        self.client=client
        self.posts=0
    def get(self,url,headers,**kwargs):
        return self.client.get('/v1/source/status',headers=headers)
    def post(self,url,headers,data,**kwargs):
        self.posts+=1
        return self.client.post('/v1/source/workbook',headers=headers,content=data)


def test_agent_end_to_end_retry_idempotence_and_changes(tmp_path):
    client,repo=client_and_repo(); transport=AgentTransport(client)
    path=tmp_path/'sample.xlsx';rows=sample_items();path.write_bytes(pending_excel(rows))
    config={'server_url':'https://example.test','excel_path':path}
    assert '3건' in sync_once(config,TOKEN,transport,0)
    assert sync_once(config,TOKEN,transport,0)=='변경 없음'
    assert transport.posts==1
    rows[0]['내용']='PC 파일 저장';path.write_bytes(pending_excel(rows))
    assert '1건' in sync_once(config,TOKEN,transport,0)
    assert repo.list_items()[0]['내용']=='PC 파일 저장'
    assert len(repo.list_events())==4
    # Simulate acknowledgement loss: next status sees committed hash, no duplicate events.
    assert sync_once(config,TOKEN,transport,0)=='변경 없음'
    assert len(repo.list_events())==4


def test_agent_network_failure_does_not_expose_token(tmp_path):
    session=Mock();session.get.side_effect=requests.ConnectionError('secret '+TOKEN)
    with pytest.raises(SyncError) as error:
        sync_once({'server_url':'https://example.test','excel_path':tmp_path/'x.xlsx'},TOKEN,session,0)
    assert TOKEN not in str(error.value)


def test_agent_rejects_unencrypted_url_and_unstable_file(tmp_path, monkeypatch):
    config=tmp_path/'config.toml'
    config.write_text("server_url='http://example.test'\nexcel_path='/tmp/example.xlsx'")
    with pytest.raises(SyncError,match='HTTPS'):
        load_config(config)
    path=tmp_path/'sample.xlsx';path.write_bytes(b'first')
    monkeypatch.setattr('local_sync.agent.time.sleep',lambda _: path.write_bytes(b'second version'))
    with pytest.raises(SyncError,match='저장 중'):
        stable_read(path)


def test_mapping_change_requests_same_file_again():
    client,repo=client_and_repo();send(client,pending_excel(sample_items()))
    assert not status(client)['resend_required']
    other=TestClient(create_app(repo,TOKEN,mapping={'pending_sheet':'Other'}))
    assert status(other)['resend_required']


def test_exact_20mb_file_accepted_and_over_limit_rejected():
    from io import BytesIO
    from zipfile import ZipFile, ZIP_STORED
    base=pending_excel(sample_items())
    probe=BytesIO(base)
    with ZipFile(probe,'a',compression=ZIP_STORED) as archive:
        archive.writestr('padding.bin',b'')
    padding=MAX_FILE-len(probe.getvalue())
    out=BytesIO(base)
    with ZipFile(out,'a',compression=ZIP_STORED) as archive:
        archive.writestr('padding.bin',b'0'*padding)
    content=out.getvalue()
    assert len(content)==MAX_FILE
    client,repo=client_and_repo()
    assert send(client,content).status_code==200
    assert send(client,content+b'0',1).status_code==413
    assert len(repo.list_events())==3


def test_local_preview_screen_and_header_selection():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_string('''
import streamlit as st
from cloud_store import Repository
from local_ui import render_local
from excel_sync import pending_excel
from sample_data import sample_items
from workbook_mapping import workbook_view
if 'repo' not in st.session_state:
    repo=Repository()
    previews, pending, warning=workbook_view(pending_excel(sample_items()), {})
    previews={k:{**v, 'rows':[[str(c) if c is not None else '' for c in r] for r in v['rows']]} for k,v in previews.items()}
    repo.ingest_local('local-excel',0,{'file_hash':'test','mapping_hash':'test','warning':warning},previews,pending)
    st.session_state.repo=repo
render_local(st.session_state.repo, {}, 'postgres', show_sheets=True)
''').run(timeout=30)
    assert not app.exception
    assert not app.error
    assert len(app.tabs)==2
    app.number_input[0].set_value(1).run()
    assert not app.exception
    assert list(app.dataframe[0].value.columns)[0]=='ID'
