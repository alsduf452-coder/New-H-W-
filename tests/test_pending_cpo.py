from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import hashlib
import pytest
from openpyxl import Workbook,load_workbook
from fastapi.testclient import TestClient
from pending_cpo import parse_cpo,HEADERS
from domain import ValidationError
from cloud_store import Repository
from sync_api import create_app
from local_sync.agent import load_config,sync_once
from classic_cloud import model


def fixture():
    b=Workbook();s=b.active;s.title='Summary';s.append(['A6 BP-04 · sample'])
    s=b.create_sheet('CPO Pending Item');s.append(['sample']);s.append(HEADERS)
    states=['완료','고객 전달 완료','Monitoring','준비 완료','SDC 검토중','추후 진행','미완료']
    for n,state in enumerate(states,1):
        s.append(['설계' if n<3 else '생기',n,'sample item','sample detail','sample plan','미정' if n==7 else '2026-11-10',None,state,'note',1 if n<3 else 0.5])
    s.append(['비고',3,'linked note'])
    out=BytesIO();b.save(out);return out.getvalue()


def test_cpo_status_notes_dates_and_identity():
    r=parse_cpo(fixture());assert (r['count'],r['done'])==(7,2)
    assert r['details'][2]['관련 메모']=='linked note'
    f=model.pending_frame({'previews':{'__pending_data__':r}})
    assert len(model.filter_pending(f,scope='주요 항목'))==7
    assert f.iloc[2]['원본 상태']=='Monitoring' and f.iloc[2]['상태']=='미완료'
    assert f.iloc[2]['진척도']=='50%' and len(r['warnings'])==1
    b=load_workbook(BytesIO(fixture()));s=b['CPO Pending Item'];s.cell(3,3,'changed');s.cell(3,1,'S/W')
    out=BytesIO();b.save(out)
    assert [d['ID'] for d in parse_cpo(out.getvalue())['details']]==[d['ID'] for d in r['details']]
    assert parse_cpo(fixture(),'another-source')['details'][0]['ID']!=r['details'][0]['ID']


@pytest.mark.parametrize('kind',['duplicate','unknown_status','orphan_note','bad_progress','missing_header'])
def test_invalid_cpo_fails_closed(kind):
    b=load_workbook(BytesIO(fixture()));s=b['CPO Pending Item']
    if kind=='duplicate':s.append([c.value for c in s[3]])
    elif kind=='unknown_status':s.cell(3,8,'unknown')
    elif kind=='orphan_note':s.cell(10,2,999)
    elif kind=='bad_progress':s.cell(3,10,101)
    else:s.cell(2,1,'missing')
    out=BytesIO();b.save(out)
    with pytest.raises(ValidationError):parse_cpo(out.getvalue())


def test_api_and_agent_keep_6g_and_cpo_isolated(tmp_path):
    repo=Repository();token='x'*43
    repo.ingest_local('pending-excel',0,{'file_hash':'old','mapping_hash':'old','mode':'pending_octa'}, {'6G':{'rows':[['old']]}},[])
    old=repo.local_previews('pending-excel')
    client=TestClient(create_app(repo,token,mapping={'mode':'hw'},sources={'pending-8g':{'mode':'pending_cpo'}}))
    class Transport:
        def get(self,url,headers,**kwargs):return client.get('/v1/source/status',headers=headers)
        def post(self,url,headers,data,**kwargs):return client.post('/v1/source/workbook',headers=headers,content=data)
    p=tmp_path/'cpo.xlsx';p.write_bytes(fixture())
    cfg={'server_url':'https://example.test','excel_path':p,'source_id':'pending-8g'}
    assert '7건 반영' in sync_once(cfg,token,Transport(),0)
    assert sync_once(cfg,token,Transport(),0)=='변경 없음'
    assert repo.local_previews('pending-excel')==old
    assert repo.list_items()==[]  # CPO is snapshot-only; original editable Pending stays untouched.
    assert repo.local_status('pending-8g')['pending_records']==7
    p.write_bytes(b'invalid workbook')
    with pytest.raises(ValueError):sync_once(cfg,token,Transport(),0)
    assert repo.local_status('pending-8g')['revision']==1


def test_optional_config_and_duplicate_source(tmp_path):
    p=tmp_path/'config.toml'
    text=f"server_url='https://example.test'\nexcel_path='{tmp_path}/hw.xlsx'\npending_excel_path='{tmp_path}/6g.xlsx'\npending8_excel_path='{tmp_path}/cpo_v*_*.xlsx'\n"
    p.write_text(text);c=load_config(p)
    assert c['pending8_source_id']=='pending-8g'
    p.write_text(text+"pending8_source_id='pending-excel'\n")
    with pytest.raises(ValueError):load_config(p)


def test_generation_switch_clears_filters_and_does_not_fallback():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'classic_app.py')).run()
    app.text_input(key='classic_search').set_value('old search').run()
    next(b for b in app.button if b.label=='8G').click().run()
    assert not app.exception
    assert app.text_input(key='classic_search').value==''
    assert any(h.value=='8G · PENDING 현황' for h in app.header)
    assert any('파일 수신' in i.value for i in app.info)
    assert not app.dataframe
    next(b for b in app.button if b.label=='PENDING List REV관리').click().run()
    assert any('REV 관리 정보가 없습니다' in i.value for i in app.info)
    next(b for b in app.button if b.label=='6G').click().run()
    assert not app.exception and app.dataframe


def test_scheduled_and_manual_workers_include_8g(tmp_path,monkeypatch):
    import sys
    from datetime import datetime
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'local_sync'))
    import daily_sync,manual_sync
    from test_manual_sync import setup
    session=setup(tmp_path,monkeypatch)
    p=tmp_path/'config.toml';p.write_text(p.read_text()+f"pending8_excel_path='{tmp_path}/8g.xlsx'\n")
    calls=[]
    def sync(config,*args):calls.append(config.get('source_id','local-excel'));return '전송 완료'
    assert daily_sync.run(tmp_path,datetime(2026,11,10,9),sync)==0
    assert calls==['local-excel','pending-excel','hw-15','pending-8g']
    calls.clear()
    assert manual_sync.run(tmp_path,datetime(2026,11,10,14),sync,lambda:session)==0
    assert calls==['local-excel','pending-excel','hw-15','pending-8g']
