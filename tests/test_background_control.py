from types import SimpleNamespace
from fastapi.testclient import TestClient
from sync_api import create_app
from cloud_store import Repository
from sync_control import SyncControl
from local_sync.background_launcher import run,CREATE_NO_WINDOW


def test_consoleless_launcher_arguments_and_exit(tmp_path):
    captured={}
    def execute(command,**kwargs):captured.update(command=command,**kwargs);return SimpleNamespace(returncode=7)
    assert run(tmp_path,True,execute)==7
    assert captured['creationflags']==CREATE_NO_WINDOW
    assert captured['command'][-1]=='-Manual'
    assert str(tmp_path/'run_daily.ps1') in captured['command']
    assert captured['cwd']==str(tmp_path)
    def fail(*args,**kwargs):raise OSError('secret-token-do-not-log')
    assert run(tmp_path,False,fail)==1
    assert 'secret-token' not in (tmp_path/'daily-state'/'launcher.log').read_text()


def test_control_disabled_by_default(monkeypatch):
    monkeypatch.delenv('SYNC_CONTROL_TOKEN',raising=False)
    c=TestClient(create_app(Repository(),'x'*43))
    assert c.post('/mcp').status_code==404
    assert c.post('/v1/control/sync').status_code==404


def test_scoped_auth_and_queue_coalescing(monkeypatch):
    monkeypatch.setenv('SYNC_CONTROL_TOKEN','c'*43)
    repo=Repository();c=TestClient(create_app(repo,'x'*43));h={'Authorization':'Bearer '+'c'*43}
    assert c.post('/v1/control/sync').status_code==401
    assert c.post('/v1/control/sync',headers={'Authorization':'Bearer '+'x'*43}).status_code==401
    assert c.post('/v1/manual/claim',headers=h).status_code==401
    a=c.post('/v1/control/sync',headers=h).json();assert a['status']=='pending'
    assert c.post('/v1/control/sync',headers=h).json()['request_id']==a['request_id']
    control=SyncControl(repo.engine);assert control.claim()['request_id']==a['request_id']
    control.finish(a['request_id'],'done','complete')
    assert c.get('/v1/control/sync',headers=h,params={'request_id':a['request_id']}).json()['status']=='done'
    assert c.get('/v1/control/sync',headers=h,params={'request_id':'a'*32}).json()['status']=='superseded'


def test_mcp_protocol_and_no_notification_writes(monkeypatch):
    monkeypatch.setenv('SYNC_CONTROL_TOKEN','c'*43)
    repo=Repository();c=TestClient(create_app(repo,'x'*43));h={'Authorization':'Bearer '+'c'*43}
    def rpc(method,params={}):return c.post('/mcp',headers=h,json={'jsonrpc':'2.0','id':1,'method':method,'params':params}).json()
    assert rpc('initialize',{'protocolVersion':'2025-03-26'})['result']['protocolVersion']=='2025-03-26'
    assert len(rpc('tools/list')['result']['tools'])==2
    assert c.post('/mcp',headers=h,json={'jsonrpc':'2.0','method':'tools/call','params':{'name':'request_excel_sync'}}).status_code==202
    assert SyncControl(repo.engine).status()=={}
    assert rpc('tools/call',{'name':'request_excel_sync','arguments':{'command':'bad'}})['error']['code']==-32602
    assert rpc('tools/call',{'name':'request_excel_sync','arguments':{}})['result']['isError'] is False
    assert rpc('tools/call',{'name':'get_excel_sync_status','arguments':{}})['result']['isError'] is False
