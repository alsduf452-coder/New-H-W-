from copy import deepcopy
from datetime import datetime
from io import BytesIO
import hashlib
import json
from openpyxl import Workbook
import pytest
from process45 import parse_process45, link_process45


def fixture(second=False):
    book=Workbook();book.remove(book.active)
    book.create_sheet('Summary')['A1']='DO NOT IMPORT'
    for ch in 'ABCDE':
        s=book.create_sheet('PC_'+ch)
        for c in ([2,11] if second and ch=='A' else [2]):
            s.cell(2,c+1,'MT 일자');s.cell(2,c+2,datetime(2026,5,14))
            for r,kind in [(10,'Diffuser Flatness'),(22,'Susceptor Flatness'),(34,'Spacing')]:
                for off,v in [(0,kind),(1,'Date'),(2,datetime(2026,5,10))]:s.cell(r,c+off,v)
                s.cell(r+1,c+1,'Diff. S/N');s.cell(r+1,c+2,'DIFF-'+ch)
                s.cell(r+1,c+3,'Susc. S/N');s.cell(r+1,c+4,'SUSC-'+ch)
                s.cell(r+2,c+1,'비고');s.cell(r+2,c+2,'confirmed')
                if kind=='Spacing':
                    for i in range(3):
                        for j in range(3):s.cell(r+5+2*i,c+2+2*j,800+i*10+j+c)
                else:
                    for i in range(7):
                        for j in range(5):s.cell(r+4+i,c+2+j,-i*5-j)
            for r,recipe in [(50,'YCNT'),(74,'YILD'),(98,'YILD2')]:
                s.cell(r,c,'공정 결과\n'+recipe);s.cell(r,c+1,'Date');s.cell(r,c+2,datetime(2026,5,15))
                for ri,ci in [(r+1,c+3),(r+1,c+5),(r+1,c+7),(r+2,c+3),(r+2,c+5),(r+3,c+3),(r+3,c+5),(r+3,c+7),(r+4,c+3),(r+4,c+5),(r+4,c+7),(r+5,c+3),(r+5,c+5)]:s.cell(ri,ci,'Data 없음')
            s.cell(51,c+3,0);s.cell(53,c+3,1800);s.cell(53,c+5,-300)
            for i in range(6):
                for j in range(5):s.cell(57+i,c+2+j,i*5+j)
    return book


def content(book):
    stream=BytesIO();book.save(stream);return stream.getvalue()


def test_five_sheets_actual_result_date_zero_signs_and_missing_fields():
    data=parse_process45(content(fixture()))
    assert len(data['records'])==5 and data['excluded_results']==10
    assert data['sheets']==['PC_'+ch for ch in 'ABCDE']
    assert 'DO NOT IMPORT' not in json.dumps(data) and 'Data 없음' not in json.dumps(data,ensure_ascii=False)
    run=data['records'][0]
    assert run['date']=='2026-05-15' and run['mt_date']=='2026-05-14'
    assert run['grid']==[[i*5+j for j in range(5)] for i in range(6)]
    assert run['metrics']=={'Unif.':0,'D/R':1800,'Stress Center':-300}
    flat=link_process45(run,data['measurements'],'Diffuser Flatness')[0]
    assert len(flat['grid'])==7 and len(flat['grid'][0])==5
    assert flat['grid'][0][0]==0 and flat['grid'][6][4]==-34
    spacing=link_process45(run,data['measurements'],'Spacing')[0]
    assert spacing['grid']==[[802+i*10+j for j in range(3)] for i in range(3)]


def test_same_date_different_snapshots_use_the_selected_evaluation_block():
    data=parse_process45(content(fixture(second=True)))
    runs=[r for r in data['records'] if r['chamber']=='A']
    assert len(runs)==2
    a,b=[link_process45(r,data['measurements'],'Spacing')[0] for r in runs]
    assert a['date']==b['date'] and a['grid']!=b['grid'] and a['id']!=b['id']


def test_future_year_wrong_serial_chamber_and_missing_are_not_linked():
    data=parse_process45(content(fixture()));run=data['records'][0]
    for kind in ['Spacing','Diffuser Flatness','Susceptor Flatness']:
        measured=link_process45(run,data['measurements'],kind)[0]
        assert link_process45({**run,'date':'2025-05-15'},data['measurements'],kind)[0] is None
        assert link_process45({**run,'chamber':'B'},data['measurements'],kind)[0] is None
        assert link_process45({**run,'hardware':{}},data['measurements'],kind)[0] is None
        field='susceptor_sn' if kind=='Susceptor Flatness' else 'diffuser_sn'
        assert link_process45({**run,field:'WRONG'},data['measurements'],kind)[0] is None
        assert link_process45(run,[{**measured,'date':'2027-05-10'}],kind)[0] is None


def test_undated_or_fully_empty_result_not_imported_but_metrics_without_map_kept():
    book=fixture();s=book['PC_A'];s['D50']='##'
    s=book['PC_B']
    for row in s.iter_rows(min_row=57,max_row=62,min_col=4,max_col=8):
        for cell in row:cell.value='Data 없음'
    data=parse_process45(content(book))
    assert not any(r['chamber']=='A' for r in data['records'])
    run=next(r for r in data['records'] if r['chamber']=='B')
    assert run['metrics']['D/R']==1800 and all(v is None for row in run['grid'] for v in row)


def test_api_separate_source_only_stores_selected_normalized_data():
    from fastapi.testclient import TestClient
    from cloud_store import Repository
    from sync_api import create_app
    repo=Repository();client=TestClient(create_app(repo,'x'*43,mapping={'mode':'hw'}))
    raw=content(fixture())
    headers={'Authorization':'Bearer '+'x'*43,'X-Sync-Source':'process-45','If-Match':'0','X-Content-SHA256':hashlib.sha256(raw).hexdigest(),'Content-Type':'application/octet-stream'}
    response=client.post('/v1/source/workbook',headers=headers,content=raw)
    assert response.status_code==200,response.text
    assert response.json()['process_records']==5
    assert set(repo.local_previews('process-45'))=={'__process_data__'}
    assert repo.local_status('local-excel')['revision']==0 and repo.local_status('process-15')['revision']==0
    assert repo.list_items()==[]


def test_screen_only_actual_results_and_pc_switch():
    from streamlit.testing.v1 import AppTest
    data=parse_process45(content(fixture()))
    script='from classic_cloud.process45_views import process45_panel\nprocess45_panel('+repr({'previews':{'__process_data__':data}})+')'
    app=AppTest.from_string(script).run(timeout=20)
    assert not app.exception
    assert len([m for m in app.markdown if '<svg ' in m.value])==3
    assert any('<table ' in m.value for m in app.markdown)
    assert 'Data 없음' not in str(app)
    app.selectbox[0].select('E').run(timeout=20)
    assert not app.exception
    assert any('PC E' in c.value for c in app.caption)


def test_45_job_in_both_workers_and_source_id_validation(tmp_path, monkeypatch):
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'local_sync'))
    from test_manual_sync import setup
    import daily_sync, manual_sync
    from agent import load_config, SyncError
    session=setup(tmp_path,monkeypatch)
    path=tmp_path/'config.toml'
    path.write_text(path.read_text()+f"process45_excel_path='{tmp_path}/process45.xlsx'\n")
    assert load_config(path)['process45_source_id']=='process-45'
    calls=[]
    def sync(config,*args):calls.append(config.get('source_id','local-excel'));return '완료'
    assert daily_sync.run(tmp_path,datetime(2026,11,13,9),sync)==0
    assert calls[-1]=='process-45'
    calls.clear()
    assert manual_sync.run(tmp_path,datetime(2026,11,13,14),sync,lambda:session)==0
    assert calls[-1]=='process-45'
    path.write_text(path.read_text()+"process45_source_id='local-excel'\n")
    with pytest.raises(SyncError):load_config(path)


def test_45_renderer_keeps_original_grid_and_15_default_orientation():
    from classic_cloud.visuals import diagram_svg
    grid=[[-i*5-j for j in range(5)] for i in range(7)]
    html=diagram_svg(grid,orientation='rows')
    assert 'R7C5' in html and 'R5C7' not in html
    assert '▲ G/V 측' in html and '▼ Window 측' in html
    assert '>-34</text>' in html and '>0</text>' in html
    assert 'G/V · Col 1' in diagram_svg(grid)
    from classic_cloud.process45_views import measurement_chart
    from streamlit.testing.v1 import AppTest
    script='from classic_cloud.process45_views import measurement_chart\nmeasurement_chart([[0,None],[-2,3]],"Map",process=True)'
    app=AppTest.from_string(script).run(timeout=20)
    assert not app.exception
    assert 'Data 없음' not in app.markdown[0].value
    assert '>0</td>' in app.markdown[0].value and '>-2</td>' in app.markdown[0].value
