import os
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'local_sync'))
from agent import resolve_excel,SyncError,load_config


def test_newest_matching_file_and_ignore_lock_file(tmp_path):
    a=tmp_path/'HW_(test)_20260101.xlsx';b=tmp_path/'HW_(test)_20260102.xlsx'
    a.touch();b.touch();os.utime(a,ns=(1,1));os.utime(b,ns=(2,2))
    (tmp_path/'~$HW_(test)_20260103.xlsx').touch()
    (tmp_path/'OTHER_20260103.xlsx').touch()
    pattern=tmp_path/'HW_(test)_*.xlsx'
    assert resolve_excel(pattern)==b
    c=tmp_path/'HW_(test)_20260103.xlsx';c.touch()
    assert resolve_excel(pattern)==c
    assert resolve_excel(a)==a


def test_missing_tied_or_wildcard_folder_fails_closed(tmp_path):
    with pytest.raises(SyncError,match='없습니다'):resolve_excel(tmp_path/'HW_*.xlsx')
    for n in ('HW_a.xlsx','HW_b.xlsx'):
        p=tmp_path/n;p.touch();os.utime(p,ns=(10,10))
    with pytest.raises(SyncError,match='여러 개'):resolve_excel(tmp_path/'HW_*.xlsx')
    with pytest.raises(SyncError,match='폴더 경로'):resolve_excel(tmp_path/'*'/'HW_*.xlsx')


def test_config_preserves_patterns(tmp_path):
    c=tmp_path/'config.toml';c.write_text(f"server_url='https://example.com'\nexcel_path='{tmp_path}/HW45_*.xlsx'\npending_excel_path='{tmp_path}/*_Pending.xlsx'\nhw15_excel_path='{tmp_path}/HW15_*.xlsx'\n")
    config=load_config(c)
    assert config['excel_path'].name=='HW45_*.xlsx'
    assert config['pending_source_id']=='pending-excel'
