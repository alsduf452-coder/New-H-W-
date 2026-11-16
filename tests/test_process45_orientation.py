"""Keep 45-unit Flatness in the H/W history coordinate system."""
from unittest.mock import patch
from classic_cloud import process45_views as view


def test_flatness_rotation_preserves_physical_positions_and_source():
    grid = [[10*r+c for c in range(5)] for r in range(7)]
    before = [row[:] for row in grid]
    displayed = view.flatness_history_grid(grid)
    assert displayed == [[10*r+c for r in range(7)] for c in range(4, -1, -1)]
    assert (displayed[0][0], displayed[0][-1], displayed[-1][0], displayed[-1][-1]) == (4, 64, 0, 60)
    assert grid == before


def test_rotation_does_not_change_spacing_or_process_maps():
    grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    for spacing, process in [(False, False), (True, False), (False, True)]:
        with patch.object(view, 'diagram_svg', return_value='<svg/>') as diagram, patch.object(view, 'map_html', return_value='<table/>') as mapping, patch.object(view.st, 'markdown'):
            view.measurement_chart(grid, 'test', spacing, process)
        actual = (mapping if process else diagram).call_args.args[0]
        assert actual == (grid if spacing or process else [[3, 6, 9], [2, 5, 8], [1, 4, 7]])
