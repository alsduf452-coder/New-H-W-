from io import BytesIO
from unittest.mock import Mock
from openpyxl import Workbook
import pytest
from workbook_mapping import workbook_view
from cloud_store import Repository
from domain import FIELDS, payload
from sample_data import sample_items


def workbook(rows, headers=FIELDS):
    book = Workbook(); sheet=book.active; sheet.title='업무'
    sheet.append(['업무 현황']); sheet.append(list(headers))
    for row in rows:
        sheet.append([row.get(f) for f in FIELDS])
    buf=BytesIO();book.save(buf);return buf.getvalue()


def test_custom_header_and_mapping():
    rows=sample_items()
    headers=['고유번호', *FIELDS[1:]]
    previews, incoming, warning=workbook_view(workbook(rows,headers), {'pending_sheet':'업무','header_row':2,'columns':{'ID':'고유번호'}})
    assert warning is None
    assert incoming == [payload(r) for r in rows]
    assert '업무' in previews


def test_missing_mapping_and_formula_block_ingestion():
    content=workbook(sample_items())
    previews, incoming, warning=workbook_view(content,{'pending_sheet':'업무','header_row':1})
    assert previews and incoming is None and warning
    rows=sample_items(); rows[0]['내용']='=1+1'
    _, incoming, warning=workbook_view(workbook(rows),{'pending_sheet':'업무','header_row':2})
    assert incoming is None and warning


def test_three_way_sync_and_atomic_conflict():
    repo=Repository(); rows=[payload(r) for r in sample_items()]
    assert repo.sync_source('source','v1',rows)['changed']==3
    updated=[dict(r) for r in rows]; updated[0]['내용']='Excel 변경'
    assert repo.sync_source('source','v2',updated)['changed']==1
    db=repo.list_items()
    repo.save_item(dict(db[0],내용='앱 변경'), 'editor', db[0]['버전'])
    next_rows=[dict(r) for r in updated]
    next_rows[0]['내용']='다른 Excel 변경'; next_rows[1]['내용']='동반 수정'
    result=repo.sync_source('source','v3',next_rows)
    assert result['conflicts']
    assert repo.source_snapshot('source')['etag']=='v2'
    assert repo.list_items()[1]['내용']==db[1]['내용']
    next_rows[0]['내용']='앱 변경'
    assert repo.sync_source('source','v4',next_rows)['changed']==1
    assert repo.sync_source('source','v4',next_rows)['changed']==0
    assert repo.list_events()[0]['actor']=='local-excel-sync'


def test_app_only_changes_and_remote_deletions_preserved():
    repo=Repository(); rows=[payload(r) for r in sample_items()]
    repo.sync_source('source','v1',rows)
    repo.save_item(dict(rows[0],내용='앱만 변경'),'editor',1)
    repo.sync_source('source','v2',rows)
    assert repo.list_items()[0]['내용']=='앱만 변경'
    repo.sync_source('source','v3',[])
    assert len(repo.list_items())==3


def test_remote_page_without_credentials():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
    app.sidebar.radio[0].set_value('로컬 Excel 연동').run()
    assert not app.exception
    assert any('샘플 모드' in x.value for x in app.info)
