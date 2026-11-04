from datetime import datetime
from pathlib import Path
import sys
import json
from unittest.mock import Mock
from fastapi.testclient import TestClient
from cloud_store import Repository
from sync_control import SyncControl
from sync_api import create_app
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'local_sync'))
from manual_sync import run,permitted
from agent import SyncError


def test_queue_coalesces_claims_and_expires():
    repo=Repository();control=SyncControl(repo.engine,initialize=True)
    first=control.request('user',now=100)
    assert control.request('other',now=101)['request_id']==first['request_id']
    assert control.claim(now=102)['request_id']==first['request_id']
    assert control.claim(now=103) is None
    assert not control.finish('bad','done','')
    assert control.finish(first['request_id'],'done','complete',now=104)
    second=control.request('user',now=105)
    assert second['request_id']!=first['request_id']
    assert control.claim(now=406) is None
    assert control.status(now=406)['status']=='expired'
    assert repo.list_items()==[]


def test_api_auth_result_validation_and_completion():
    repo=Repository();api=TestClient(create_app(repo,'x'*43,mapping={'mode':'hw'}))
    control=SyncControl(repo.engine);request=control.request('user')
    assert api.post('/v1/manual/claim').status_code==401
    headers={'Authorization':'Bearer '+'x'*43}
    assert api.post('/v1/manual/claim',headers=headers).json()['request']['request_id']==request['request_id']
    assert api.post('/v1/manual/claim',headers=headers).json()['request'] is None
    assert api.post('/v1/manual/result',headers=headers,json={'request_id':request['request_id'],'status':'invalid'}).status_code==422
    assert api.post('/v1/manual/result',headers=headers,json={'request_id':request['request_id'],'status':'done','summary':'ok'}).status_code==200
    assert control.status()['status']=='done'


def setup(root,monkeypatch):
    (root/'schedule.json').write_text(json.dumps({'paused':False,'absence':[]}))
    (root/'config.toml').write_text(f"server_url='https://example.com'\nexcel_path='{root}/hw.xlsx'\npending_excel_path='{root}/pending.xlsx'\nhw15_excel_path='{root}/hw15.xlsx'\n")
    monkeypatch.setenv('LOCAL_SYNC_TOKEN','x'*43)
    session=Mock();session.__enter__=Mock(return_value=session);session.__exit__=Mock(return_value=False)
    claim=Mock(status_code=200);claim.json.return_value={'request':{'request_id':'a'*32}}
    result=Mock(status_code=200);result.json.return_value={'ok':True}
    session.post.side_effect=[claim,result]
    return session


def test_worker_manual_outside_0900_three_files_and_failure_stop(tmp_path,monkeypatch):
    session=setup(tmp_path,monkeypatch);calls=[]
    def sync(config,*args):calls.append(config.get('source_id','local-excel'));return '전송 완료'
    assert run(tmp_path,datetime(2026,11,4,14),sync,lambda:session)==0
    assert calls==['local-excel','pending-excel','hw-15']
    assert session.post.call_args.kwargs['json']['status']=='done'
    session=setup(tmp_path,monkeypatch);calls=[]
    def fail(*args):calls.append(1);raise SyncError('failed')
    assert run(tmp_path,datetime(2026,11,4,15),fail,lambda:session)==1
    assert calls==[1]
    assert session.post.call_args.kwargs['json']['status']=='failed'
    session.reset_mock()
    assert run(tmp_path,datetime(2026,11,4,16),fail,lambda:session)==0
    session.post.assert_not_called()


def test_absence_makes_no_network_calls(tmp_path,monkeypatch):
    session=setup(tmp_path,monkeypatch)
    (tmp_path/'schedule.json').write_text(json.dumps({'absence':[{'start':'2026-11-04','end':'2026-11-06'}]}))
    assert run(tmp_path,datetime(2026,11,4,14),session_factory=lambda:session)==0
    session.post.assert_not_called()
