import pytest
from classic_cloud.evaluation_compare import difference, uniformity, display_grid, comparison_html
from streamlit.testing.v1 import AppTest


def test_difference_missing_and_shape():
    assert difference([[4,None]], [[1,2]]) == [[3,None]]
    assert difference([[1]], [[1,2]]) is None


def test_units_rotation():
    assert uniformity({'unif':3.4},'15') == pytest.approx(3.4)
    assert uniformity({'metrics':{'Unif.':.034}},'45') == pytest.approx(3.4)
    assert display_grid('45','Diffuser Flatness',[[1,2],[3,4],[5,6]]) == [[2,4,6],[1,3,5]]
    assert display_grid('45','Spacing',[[1,2],[3,4]]) == [[1,2],[3,4]]


def app(unit):
    import streamlit as st
    from classic_cloud.process_views import process_panel
    from classic_cloud.process45_views import process45_panel
    runs=[]
    for i in range(3):
        runs.append(dict(id=str(i),date='2026-07-'+str(10+i),chamber='A',recipe='YILD' if unit=='45' else 'Barrier',source_cell='A'+str(i),grid=[[None]*5 for _ in range(6 if unit=='45' else 5)],unif=3+i,metrics={'Unif.':.03+i*.01},mt_date='',hardware={},dep_time='50',notes='',hcg='',diffuser_sn='',susceptor_sn=''))
    snap={'previews':{'__process_data__':{'equipment':unit+'호기','records':runs,'measurements':[]}}}
    (process45_panel if unit=='45' else process_panel)(snap, {})


def test_navigation_and_comparison():
    for unit in ['15','45']:
        at=AppTest.from_function(app,args=(unit,)).run()
        assert not at.exception
        at.button[0].click().run()
        assert not at.exception
        assert len(at.multiselect)==1
        at.multiselect[0].set_value(['0','1']).run()
        assert not at.exception
        html=''.join(m.value for m in at.markdown)
        assert '기준 평가' in html and '비교 평가 2' in html
        assert 'Data 없음' in html and 'Unif.' in html


def test_shared_map_scale_delta_and_html_escaping():
    base=dict(id='a',date='2026-07-10',chamber='A',recipe='<test>',source_cell='A1',grid=[[0,10]],unif=3.4)
    other={**base,'id':'b','grid':[[10,None]],'unif':3.1}
    html=comparison_html('15',[base,other],{}, {})
    assert '<test>' not in html and '&lt;test&gt;' in html
    assert html.count('hsl(0.0,65%,78%)') == 2
    assert '기준 대비 -0.30%p' in html
    delta=comparison_html('15',[base,other],{}, {},True)
    assert '>+10<' in delta and '>—<' in delta
    assert other['grid'] == [[10,None]]
