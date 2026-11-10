from io import BytesIO
from copy import deepcopy
from openpyxl import Workbook
import pytest
from process_map import parse_process,link_measurement
from classic_cloud.process_views import map_html
from domain import ValidationError

def fixture():
 b=Workbook();s=b.active;s.title='Unif 결과 데이터'
 for c,recipe in [(3,'R1'),(12,'R2')]:
  for off,v in enumerate(['Date','25.09.19','PC','A','Recipe',recipe,'Dep Time',54.9]):s.cell(12,c+off,v)
  s.cell(14,c+2,'DIFF-1');s.cell(15,c+2,'SUSC1');s.cell(14,c+5,'-172mils')
  s.cell(22,c+5,'Unif.');s.cell(22,c+6,.034)
  if c==3:
   for i in range(5):
    for j in range(5):s.cell(17+i,c+2+j,0 if i==j==0 else 4900+i+j)
  else:s.cell(17,c+2,'Raw Data 확인 필요')
 b.create_sheet('Unif.')['A1']='not imported'
 out=BytesIO();b.save(out);return out.getvalue()

def test_only_selected_sheet_coordinates_excluded_and_missing_map_retained():
 d=parse_process(fixture());a,b=d['records'];assert len(d['records'])==2
 assert a['date']=='2025-09-19' and a['grid'][0][0]==0 and a['unif']==pytest.approx(3.4)
 assert 'Data 없음' in map_html(b['grid']) and b['unif']==pytest.approx(3.4)
 assert a['recipe']!=b['recipe'] and a['id']!=b['id']
 assert 'not imported' not in str(d)

def test_asof_never_future_and_no_wrong_serial_or_ambiguous_same_day():
 run=parse_process(fixture())['records'][0]
 base={'id':'old','kind':'Spacing','chamber':'A','date':'2025-09-18','diffuser_sn':'DIFF1','susceptor_sn':'SUSC1'}
 future={**base,'id':'future','date':'2025-09-20'}
 assert link_measurement(run,[base,future],'Spacing')[0]['id']=='old'
 assert link_measurement(run,[future],'Spacing')[0] is None
 assert link_measurement(run,[base,{**base,'id':'other'}],'Spacing')[0] is None
 assert link_measurement(run,[base,{**base,'date':'2025-09-19','diffuser_sn':'WRONG'}],'Spacing')[0] is None
 assert link_measurement(run,[{**base,'chamber':'B'}],'Spacing')[0] is None

def test_process_api_snapshot_only():
 from fastapi.testclient import TestClient
 from cloud_store import Repository
 from sync_api import create_app
 import hashlib
 repo=Repository();client=TestClient(create_app(repo,'x'*43,mapping={'mode':'hw'},sources={'process-15':{'mode':'process15'}}))
 content=fixture();headers={'Authorization':'Bearer '+'x'*43,'X-Sync-Source':'process-15','If-Match':'0','X-Content-SHA256':hashlib.sha256(content).hexdigest(),'Content-Type':'application/octet-stream'}
 response=client.post('/v1/source/workbook',headers=headers,content=content)
 assert response.status_code==200 and response.json()['process_records']==2
 assert list(repo.local_previews('process-15'))==['__process_data__']
 assert repo.list_items()==[] and repo.local_status('hw-15')['revision']==0

def test_map_screen_missing_preserves_unif():
 from streamlit.testing.v1 import AppTest
 d=parse_process(fixture());d['records']=d['records'][1:]
 script='from classic_cloud.process_views import process_panel\nprocess_panel('+repr({'previews':{'__process_data__':d}})+',{})'
 app=AppTest.from_string(script).run();assert not app.exception
 assert any('Data 없음' in m.value for m in app.markdown)
 assert any('Unif. 3.40%' in m.value for m in app.markdown)


def test_process_job_in_both_workers(tmp_path,monkeypatch):
 import sys
 from pathlib import Path
 from datetime import datetime
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'local_sync'))
 from test_manual_sync import setup
 import daily_sync,manual_sync
 from agent import load_config
 session=setup(tmp_path,monkeypatch)
 p=tmp_path/'config.toml';p.write_text(p.read_text()+f"process15_excel_path='{tmp_path}/process.xlsx'\n")
 assert load_config(p)['process15_source_id']=='process-15'
 calls=[]
 def sync(c,*args):calls.append(c.get('source_id','local-excel'));return '완료'
 assert daily_sync.run(tmp_path,datetime(2026,11,10,9),sync)==0
 assert calls[-1]=='process-15'
 calls.clear();assert manual_sync.run(tmp_path,datetime(2026,11,10,14),sync,lambda:session)==0
 assert calls[-1]=='process-15'
