from datetime import date
from io import BytesIO
from unittest.mock import MagicMock
import pandas as pd
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest
from classic_cloud import model
from classic_cloud.sample import snapshots
from classic_cloud.reader import SnapshotReader
from classic_cloud.visuals import measurement_table, diagram_svg


def test_pending_filters_summary_and_dates():
    frame=model.pending_frame(snapshots()['pending'])
    assert len(frame)==3
    assert model.summary(frame,'분야')['완료'].sum()==1
    assert len(model.filter_pending(frame,states=['미완료'],query='점검'))==2
    frame.loc[0,'목표일']='2026-10-27'
    frame.loc[2,'목표일']='2612.01.01'
    assert model.deadlines(frame,date(2026,10,28))==({'기한초과':1,'임박':0,'여유':0},1)
    assert model.filter_pending(frame,query='no match').empty
    assert model.pending_frame({}).empty


def test_revision_and_literal_export():
    rev=model.revision(snapshots()['pending'])
    assert len(rev['history'])==1
    assert rev['summary'][0]['총 건수']=='3'
    book=load_workbook(BytesIO(model.workbook_export({'test':pd.DataFrame({'값':['=1+1',0,-39,None]})})))
    assert book.active['A2'].data_type=='s'
    assert book.active['A3'].value==0
    assert book.active['A4'].value==-39


def test_reader_uses_read_only_transaction_and_bound_source():
    reader=SnapshotReader.__new__(SnapshotReader)
    reader.engine=MagicMock()
    conn=reader.engine.begin.return_value.__enter__.return_value
    conn.execute.return_value.mappings.return_value.first.return_value={'revision':4,'state':{},'previews':{}}
    assert reader.read("source'; DROP TABLE x")['revision']==4
    calls=conn.execute.call_args_list
    assert str(calls[0].args[0])=='SET TRANSACTION READ ONLY'
    assert str(calls[1].args[0]).startswith('SELECT ')
    assert calls[1].args[1]=={'source':"source'; DROP TABLE x"}
    assert len(calls)==2


def test_measurement_preserves_zero_sign_and_escapes_text():
    grid=[[None,0,-39,'<script>',1,2,3] for _ in range(5)]
    html=measurement_table(grid)+diagram_svg(grid)
    assert '-39' in html and '>0<' in html and 'R3C4' in html
    assert '<script>' not in html


def click(app,label):
    next(button for button in app.button if button.label==label).click().run()
    assert not app.exception


def test_demo_navigation_and_measurements():
    app=AppTest.from_file('../classic_app.py',default_timeout=15).run()
    assert not app.exception
    click(app,'PENDING List REV관리')
    assert any('REV' in header.value for header in app.header)
    click(app,'설비 H/W 이력관리')
    for label in ['작업 이력','부품 추적','데이터 관리','Spacing','Flatness']:
        click(app,label)
    assert 'Center (R3C4)' in app.dataframe[0].value.columns
    next(s for s in app.selectbox if s.label=='H/W 챔버').select('A').run()
    assert not app.exception
    click(app,'Susceptor')
    assert not app.exception
    click(app,'PENDING 현황')
    app.button(key='classic_kpi_미완료').click().run()
    assert not app.exception
    assert any('미완료' in s.value for s in app.subheader)


def test_production_requires_login_before_database_read(monkeypatch):
    from password_auth import hash_password
    reads=[]
    monkeypatch.setattr(SnapshotReader,'__init__',lambda self,url:reads.append(url))
    app=AppTest.from_file('../classic_app.py',default_timeout=15)
    app.secrets['storage']={'mode':'postgres'}
    app.secrets['database']={'url':'postgresql://unused'}
    app.secrets['login']={'method':'password'}
    app.secrets['local_auth']={'users':{'demo':{'password_hash':hash_password('test-password'),'role':'viewer'}}}
    app.run()
    assert not app.exception
    assert any(s.value=='아이디·비밀번호 로그인' for s in app.subheader)
    assert reads==[]
