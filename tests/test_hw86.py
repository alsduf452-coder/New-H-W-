from io import BytesIO
from pathlib import Path
from datetime import datetime
import hashlib
import json
import pytest
from openpyxl import Workbook
from fastapi.testclient import TestClient
from hw86_excel import parse_hw86,delta,SHEETS
from cloud_store import Repository
from sync_api import create_app
from local_sync.agent import sync_once,load_config


def fixture():
    b=Workbook();b.remove(b.active)
    for name in SHEETS:
        s=b.create_sheet(name)
        for col,title in [(2,'(26/01/02) Test (Temp. Up 전)'),(10,'편차'),(18,'(26/01/03) Test (Temp. Down 후)')]:
            s.merge_cells(start_row=2,start_column=col,end_row=3,end_column=col+6);s.cell(2,col,title)
            for i in range(5):
                for j in range(7):s.cell(5+i,col+j,999 if col==10 else i*7+j+(10 if col==18 else 0))
        s.cell(5,2,0);s.cell(6,3,'X')
        if name=='Shim 변경이력':
            s.cell(11,2,6.5);s.cell(13,5,4.5);s.cell(13,21,3.5);s.cell(12,2,'↘ 7.5')
        if name=='Susceptor Flat.':
            for r in (10,11):
                for c in range(18,25):s.cell(r,c,1)
        s.merge_cells('Z2:AF3');s['Z2']='(26/01/04) Backing Plate 재생';s['Z5']=123
    b.create_sheet('Excluded secret sheet')['A1']='must not enter snapshot'
    out=BytesIO();b.save(out);return out.getvalue()


def test_import_excludes_deviation_backing_other_sheets_and_retains_missing():
    d=parse_hw86(fixture());assert len(d['measurements'])==8
    assert all(r['column'] in (2,18) for r in d['measurements'])
    a=d['measurements'][0];assert a['grid'][0][0]==0 and a['grid'][1][1] is None
    assert a['stats']['count']==34 and 'X' in str(a['cell_notes'])
    s=next(r for r in d['measurements'] if r['kind']=='Susceptor Flatness' and r['column']==18)
    assert len(s['grid'])==7 and s['stats']['count']==49
    shim=next(r for r in d['measurements'] if r['kind']=='Shim 변경이력' and r['column']==2)
    assert shim['shim'][2][3]==4.5 and any('↘ 7.5' in n for n in shim['shim_notes'])
    assert 'must not enter snapshot' not in json.dumps(d)


def test_delta_uses_points_not_excel_deviation_and_shapes():
    d=parse_hw86(fixture())['measurements'];a,b=d[:2]
    diff=delta(a,b);assert diff[0][0]==10 and diff[1][1] is None
    with pytest.raises(ValueError):delta(d[2],d[3])
    shim=[r for r in d if r['kind']=='Shim 변경이력']
    assert delta(*shim,'shim')[2][3]==-1


def test_ingestion_and_agent_isolation(tmp_path):
    repo=Repository();token='x'*43
    client=TestClient(create_app(repo,token,mapping={'mode':'hw'},sources={'hw-86':{'mode':'hw86'}}))
    class Transport:
        def get(self,url,headers,**kwargs):return client.get('/v1/source/status',headers=headers)
        def post(self,url,headers,data,**kwargs):return client.post('/v1/source/workbook',headers=headers,content=data)
    p=tmp_path/'hw86.xlsx';p.write_bytes(fixture());cfg={'excel_path':p,'server_url':'https://example.test','source_id':'hw-86'}
    assert '8건' in sync_once(cfg,token,Transport(),0)
    assert sync_once(cfg,token,Transport(),0)=='H/W 변경 없음'
    assert repo.local_status('local-excel')['revision']==0 and repo.list_items()==[]
    preview=repo.local_previews('hw-86');assert list(preview)==['__hw86_data__']
    p.write_bytes(b'bad file')
    with pytest.raises(ValueError):sync_once(cfg,token,Transport(),0)
    assert repo.local_status('hw-86')['revision']==1


def test_workers_include_fifth_source(tmp_path,monkeypatch):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'local_sync'))
    import daily_sync,manual_sync
    from test_manual_sync import setup
    session=setup(tmp_path,monkeypatch)
    p=tmp_path/'config.toml';p.write_text(p.read_text()+f"pending8_excel_path='{tmp_path}/pending8.xlsx'\nhw86_excel_path='{tmp_path}/hw86*.xlsx'\n")
    assert load_config(p)['hw86_source_id']=='hw-86'
    calls=[]
    def sync(c,*args):calls.append(c.get('source_id','local-excel'));return '완료'
    assert daily_sync.run(tmp_path,datetime(2026,11,10,9),sync)==0
    assert calls==['local-excel','pending-excel','hw-15','pending-8g','hw-86']
    calls.clear();assert manual_sync.run(tmp_path,datetime(2026,11,10,14),sync,lambda:session)==0
    assert calls[-1]=='hw-86'
    p.write_text(p.read_text()+"hw86_source_id='pending-8g'\n")
    with pytest.raises(ValueError):load_config(p)


def test_views_selection_and_comparison():
    from streamlit.testing.v1 import AppTest
    data=parse_hw86(fixture())
    script='''import streamlit as st
from types import SimpleNamespace
from classic_cloud.hw86_views import hardware
original=st.dataframe
def selected(*args,**kwargs):
    original(*args,**kwargs)
    return SimpleNamespace(selection=SimpleNamespace(rows=[0]))
st.dataframe=selected
hardware(SNAPSHOT)
'''.replace('SNAPSHOT',repr({'revision':1,'previews':{'__hw86_data__':data}}))
    app=AppTest.from_string(script).run();assert not app.exception
    assert any(s.value=='측정 상세' for s in app.subheader)
    app.checkbox[0].check().run();assert not app.exception
    assert any('측정 변화량' in m.value for m in app.markdown)
    next(b for b in app.button if b.label=='Shim 변경이력').click().run();assert not app.exception
    app.checkbox[0].check().run();assert not app.exception
    assert any('Shim 두께 변화량' in m.value for m in app.markdown)


def test_standard_spacing_positions_and_nonstandard_points():
    from classic_cloud.hw86_views import spacing_grid
    g=[[None]*7 for _ in range(5)]
    for r in (0,2,4):
        for c in (0,3,6):g[r][c]=r*7+c
    assert spacing_grid(g)==[[0,3,6],[14,17,20],[28,31,34]]
    g[1][2]=873.9
    assert spacing_grid(g) is None


def test_measurement_detail_two_panels():
    from streamlit.testing.v1 import AppTest
    data=parse_hw86(fixture())['measurements'][0]
    script='from classic_cloud.hw86_views import measurement_detail\nmeasurement_detail('+repr(data)+')'
    app=AppTest.from_string(script).run()
    assert not app.exception
    assert [s.value for s in app.subheader]==['Diffuser Flatness 실측 데이터','Diffuser Flatness 측정 위치도']
    assert any('<svg' in m.value for m in app.markdown)
