import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from io import BytesIO
import pytest
from openpyxl import load_workbook
from cloud_store import Repository, ConflictError
from domain import build_plan, access_role, ValidationError
from excel_sync import pending_excel, read_pending_excel
from sample_data import sample_items


def seeded():
    repo = Repository()
    for row in sample_items():
        repo.save_item(row, 'tester')
    return repo


def test_excel_roundtrip_and_literal_formula():
    rows = seeded().list_items()
    rows[0]['내용'] = '=1+1'
    assert read_pending_excel(pending_excel(rows)) == rows


def test_excel_formula_rejected():
    book = load_workbook(BytesIO(pending_excel(seeded().list_items())))
    book['PENDING']['E2'] = '=1+1'
    out = BytesIO(); book.save(out)
    with pytest.raises(ValidationError, match='수식'):
        read_pending_excel(out.getvalue())


def test_import_updates_audit_and_preserves_missing():
    repo = seeded(); rows = repo.list_items()
    changed = dict(rows[0], 내용='수정 내용')
    plan = build_plan(rows, [changed])
    assert len(plan['missing']) == 2
    assert repo.apply_plan(plan, 'editor@example.com') == 1
    assert len(repo.list_items()) == 3
    event = repo.list_events()[0]
    assert event['before_value']['내용'] == rows[0]['내용']
    assert event['after_value']['내용'] == '수정 내용'
    assert event['actor'] == 'editor@example.com'
    assert event['after_value']['버전'] == 2
    assert build_plan(repo.list_items(), [dict(changed, 내용='낡은 수정')])['conflicts']


def test_atomic_rollback_when_second_row_conflicts():
    repo = seeded(); before = repo.list_items()
    plan = build_plan(before, [dict(r, 내용='Excel 수정') for r in before])
    repo.save_item(dict(before[1], 내용='동시 수정'), 'other', 1)
    with pytest.raises(ConflictError):
        repo.apply_plan(plan, 'excel')
    after = repo.list_items()
    assert after[0] == before[0]
    assert after[1]['내용'] == '동시 수정'
    assert len(repo.list_events()) == 4


def test_duplicate_and_roles():
    rows = seeded().list_items()
    with pytest.raises(ValidationError, match='중복'):
        build_plan(rows, [rows[0], rows[0]])
    assert access_role('a@x', [], ['a@x']) is None
    assert access_role('A@X', ['a@x'], []) == 'viewer'
    assert access_role('a@x', ['a@x'], ['a@x']) == 'editor'


def test_streamlit_pages_and_session_isolation():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
    assert not app.exception
    assert app.metric[0].value == '3'
    app.session_state['demo_repository'].save_item(dict(sample_items()[0], ID='NEW-1'), 'test')
    app.run()
    assert app.metric[0].value == '4'
    other = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
    assert other.metric[0].value == '3'
    for page in ['Excel 동기화', '변경 이력']:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception


def test_production_fails_closed():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
    app.secrets['storage'] = {'mode': 'postgres'}
    app.run(timeout=30)
    assert not app.exception
    assert any('허용 계정' in e.value for e in app.error)
    assert not app.metric


def test_screen_registration_and_edit():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
    app.text_input[0].set_value('DEMO-NEW')
    app.text_area[0].set_value('화면에서 등록한 내용')
    next(b for b in app.button if b.label == '저장').click().run()
    assert not app.exception
    assert app.metric[0].value == '4'
    row = next(r for r in app.session_state['demo_repository'].list_items() if r['설비'] == 'DEMO-NEW')
    next(s for s in app.selectbox if s.label == '수정할 항목').set_value(row['ID']).run()
    app.text_area[1].set_value('화면에서 수정한 내용')
    [b for b in app.button if b.label == '저장'][1].click().run()
    assert not app.exception
    updated = next(r for r in app.session_state['demo_repository'].list_items() if r['ID'] == row['ID'])
    assert updated['내용'] == '화면에서 수정한 내용'
    assert updated['버전'] == 2
