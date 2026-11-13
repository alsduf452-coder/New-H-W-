"""45-unit display uses 15-unit cell geometry without reassigning measurements."""
from copy import deepcopy
from xml.etree import ElementTree as ET
from classic_cloud.visuals import diagram_svg


def test_transposed_flatness_matches_15_geometry_and_preserves_source_coordinates():
    grid=[[r*5+c for c in range(5)] for r in range(7)]
    original=deepcopy(grid)
    rendered=ET.fromstring(diagram_svg(grid,transpose=True))
    reference=ET.fromstring(diagram_svg([[0]*7 for _ in range(5)]))
    cells=rendered.findall('{*}rect')[1:]
    expected=reference.findall('{*}rect')[1:]
    assert len(cells)==len(expected)==35
    for actual,wanted in zip(cells,expected):
        for key in ('x','y','width','height'):
            assert actual.attrib[key]==wanted.attrib[key]
    texts=rendered.findall('{*}text')[2:]
    for row in range(5):
        for col in range(7):
            label,value=texts[(row*7+col)*2:(row*7+col)*2+2]
            assert label.text==f'R{col+1}C{row+1}'
            assert value.text==str(grid[col][row])
    assert grid==original
    assert 'G/V · 원본 Row 1' in diagram_svg(grid,transpose=True)
    spacing=[[885]*3 for _ in range(3)]
    assert diagram_svg(spacing,True,transpose=True)==diagram_svg(spacing,True)
