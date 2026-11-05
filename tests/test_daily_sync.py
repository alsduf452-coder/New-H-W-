import importlib.util
import sys
from pathlib import Path
from datetime import datetime
import json
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'local_sync'))
from daily_sync import eligible,run
from agent import SyncError


def setup(root):
    (root/'schedule.json').write_text(json.dumps({'paused':False,'absence':[]}))
    (root/'config.toml').write_text(f"server_url='https://example.com'\nexcel_path='{root}/hw.xlsx'\npending_excel_path='{root}/pending.xlsx'\nhw15_excel_path='{root}/hw15.xlsx'\n")


def test_absence_pause_and_no_late_catchup():
    assert eligible({'paused':True},datetime(2026,11,4,9))[0] is False
    s={'absence':[{'start':'2026-11-04','end':'2026-11-06'}]}
    for day in (4,5,6):assert not eligible(s,datetime(2026,11,day,9))[0]
    assert eligible(s,datetime(2026,11,7,9))[0]
    assert not eligible({},datetime(2026,11,7,9,1))[0]
    assert not eligible({},datetime(2026,11,7,8,59))[0]


def test_failure_stops_all_sources_and_retries_only_next_day(tmp_path,monkeypatch):
    setup(tmp_path);monkeypatch.setenv('LOCAL_SYNC_TOKEN','x'*43)
    calls=[]
    def fail(*args):calls.append(1);raise SyncError('connection failed')
    assert run(tmp_path,datetime(2026,11,4,9),fail)==1
    assert len(calls)==1
    assert run(tmp_path,datetime(2026,11,4,9),fail)==0
    assert len(calls)==1
    assert run(tmp_path,datetime(2026,11,5,9),fail)==1
    assert len(calls)==2


def test_three_files_once_and_no_token_in_logs(tmp_path,monkeypatch):
    setup(tmp_path);token='private-value-'+'x'*43;monkeypatch.setenv('LOCAL_SYNC_TOKEN',token)
    calls=[]
    def ok(config,*args):calls.append(config.get('source_id','local-excel'));return '전송 완료'
    assert run(tmp_path,datetime(2026,11,4,9),ok)==0
    assert calls==['local-excel','pending-excel','hw-15']
    assert token not in (tmp_path/'daily-state'/'2026-11.log').read_text()


def test_bad_settings_and_missing_token_never_transmit(tmp_path,monkeypatch):
    setup(tmp_path);monkeypatch.delenv('LOCAL_SYNC_TOKEN',raising=False)
    def forbidden(*args):raise AssertionError('must not transmit')
    assert run(tmp_path,datetime(2026,11,4,9),forbidden)==1
    (tmp_path/'schedule.json').write_text('bad')
    assert run(tmp_path,datetime(2026,11,5,9),forbidden)==1


def test_automatic_waits_for_manual_lock_then_runs(tmp_path,monkeypatch):
    import daily_sync
    from contextlib import contextmanager
    setup(tmp_path);monkeypatch.setenv('LOCAL_SYNC_TOKEN','x'*43)
    locks=iter([False,True])
    @contextmanager
    def lock(root):yield next(locks)
    monkeypatch.setattr(daily_sync,'sync_lock',lock)
    monkeypatch.setattr(daily_sync.time,'sleep',lambda seconds:None)
    calls=[]
    assert run(tmp_path,datetime(2026,11,5,9,0,1),lambda *args:calls.append(1) or '완료')==0
    assert len(calls)==3
    assert (tmp_path/'daily-state'/'2026-11-05.attempt').exists()


def test_automatic_lock_timeout_is_logged(tmp_path,monkeypatch):
    import daily_sync
    from contextlib import contextmanager
    setup(tmp_path)
    @contextmanager
    def lock(root):yield False
    monkeypatch.setattr(daily_sync,'sync_lock',lock)
    clock=iter([0,181]);monkeypatch.setattr(daily_sync.time,'monotonic',lambda:next(clock))
    assert run(tmp_path,datetime(2026,11,5,9))==1
    assert '대기 시간 초과' in (tmp_path/'daily-state'/'2026-11.log').read_text()
