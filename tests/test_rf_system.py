from rf_system import parse_rf_system, rf_system_card


def test_block_isolation_and_missing_values():
    rows = [
        [None, 'RF System', 'RFG', 'Maker', 'NPP', 'S/N', 'A-SERIAL', None, None, None,
         'RF System', 'RFG', 'Maker', 'OTHER', 'S/N', 'B-SERIAL', None, None, None],
        [None, None, 'Matcher', 'Maker', 'NPP', 'S/N', 'MATCH-A', None, None, None],
        [None, None, 'RF Cable', 'Type', 'Rigid', 'Length', '5.15m', 'Bellows 수', '1ea', None],
    ]
    first = parse_rf_system(rows, 2, 10)
    second = parse_rf_system(rows, 11, 19)
    assert first['rfg']['serial'] == 'A-SERIAL'
    assert first['cable']['type'] == 'Rigid'
    assert first['cable']['length'] == '5.15m'
    assert first['cable']['bellows'] == '1ea'
    assert second['rfg']['serial'] == 'B-SERIAL'
    assert 'cable' not in second
    assert parse_rf_system([], 2, 10) == {}


def test_ambiguous_rows_are_not_silently_selected():
    row = [None, 'RFG', 'Maker', 'NPP', 'S/N', 'SERIAL']
    assert parse_rf_system([row, row], 2, 10) == {}


def test_render_escapes_values_and_does_not_use_sample_defaults():
    html = rf_system_card({'chamber': 'A', 'rf_system': {'cable': {'type': '<Rigid>'}}})
    assert '&lt;Rigid&gt;' in html and '<Rigid>' not in html
    assert 'NPG2K260039' not in html
    assert 'RF 정보 없음' in rf_system_card({'chamber': 'B'})
