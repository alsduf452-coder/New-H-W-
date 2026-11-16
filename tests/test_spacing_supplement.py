from io import BytesIO
from openpyxl import load_workbook
from hw_excel import parse_hw
from process45 import link_spacing_history
from test_hw import hw_fixture


def test_supplement_is_additive_by_chamber_date_and_preserves_positions():
    original = hw_fixture()
    before = parse_hw(original)
    book = load_workbook(BytesIO(original))
    extra = book.copy_worksheet(book['Spacing'])
    extra.title = 'Spacing_1'
    extra['C7'] = '2000-01-02'
    extra['C11'] = -1
    extra['E13'] = 0
    # B is a duplicate date: ignore it even when its value differs.
    extra['L11'] = 999
    extra['U7'] = '2000-01-03'
    for row in (11, 13, 15):
        for col in (21, 23, 25):
            extra.cell(row, col).value = None
    # A second recognized spelling must not reintroduce duplicate dates.
    alias = book.copy_worksheet(extra)
    alias.title = 'Spacing1'
    out = BytesIO(); book.save(out)
    after = parse_hw(out.getvalue())
    assert after['measurements'][:len(before['measurements'])] == before['measurements']
    added = after['measurements'][len(before['measurements']):]
    assert len(added) == 1
    assert added[0]['id'] == 'Spacing_1:B7'
    assert added[0]['grid'] == [[-1, 1, 2], [10, 0, 12], [20, 21, 22]]
    assert added[0]['center'] == 0
    assert added[0]['source_sheet'] == 'Spacing_1'


def sample(identifier, date, **fields):
    return dict(id=identifier, date=date, kind='Spacing', chamber='A',
                diffuser_sn='D1', susceptor_sn='S1', grid=[[1]*3 for _ in range(3)], **fields)


def test_comparison_uses_latest_eligible_spacing_and_retains_card_on_ties():
    run = dict(date='2000-02-01', chamber='A', diffuser_sn='D1', susceptor_sn='S1', hardware={'Spacing':'card'})
    card = sample('card', '2000-01-01')
    added = sample('Spacing_1:B7', '2000-01-02')
    future = sample('future', '2000-02-02')
    wrong = {**sample('wrong', '2000-01-31'), 'diffuser_sn':'D2'}
    assert link_spacing_history(run, [card], [added, future, wrong])[0] == added
    same_day = {**added, 'date':run['date']}
    assert link_spacing_history(run, [card], [same_day])[0] == same_day
    assert link_spacing_history(run, [card], [{**added, 'date':card['date']}])[0] == card
    assert link_spacing_history(run, [card], [future, wrong])[0] == card


def test_comparison_rejects_ambiguous_same_date_and_can_fill_missing_card():
    run = dict(date='2000-02-01', chamber='A', diffuser_sn='D1', susceptor_sn='S1', hardware={})
    added = sample('Spacing_1:B7', '2000-01-02')
    assert link_spacing_history(run, [], [added])[0] == added
    result, reason = link_spacing_history(run, [], [added, {**added, 'id':'another'}])
    assert result is None and '여러 개' in reason
