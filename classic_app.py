"""Separate HW-25-style app. Existing app.py and ingestion server remain unchanged."""
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from classic_cloud.reader import SnapshotReader
from sync_control import SyncControl
from classic_cloud.sync_status import render_sync_status
from classic_cloud import model, views, hw86_views, process_views
from classic_cloud.visuals import STYLE, cards
from login_ui import require_local, guard_fragment

st.set_page_config(page_title='양산 설비 통합 관리 · Excel 연동', page_icon='🔷', layout='wide')
st.markdown(STYLE,unsafe_allow_html=True)
st.title('양산 설비 통합 관리')
st.caption('CLASSIC-CLOUD-04 · Soft Slate · Excel 자동 연동 · 조회 전용')
try:
    settings=dict(st.secrets)
except FileNotFoundError:
    settings={}
mode=settings.get('storage',{}).get('mode','demo')
with st.sidebar:
    generation=cards('설비 세대',['6G','8G'],'classic_generation',True)
    if generation=='6G':
        hw_unit=st.selectbox('H/W 설비',['45호기','15호기'],key='classic_hw_unit')
    else:
        hw_unit='A6 BP-04'
        st.caption('8.6G · A6 BP-04')
    st.caption('PENDING은 선택한 세대의 파일을 조회합니다. H/W 설비 선택은 H/W 조회에 적용됩니다.')

if st.session_state.get('classic_previous_generation')!=generation:
    for key in ['classic_equipment','classic_fields','classic_states','classic_search','classic_scope','classic_drill','classic_filter_signature','classic_rev_query']:
        st.session_state.pop(key,None)
    st.session_state['classic_previous_generation']=generation

@st.cache_resource
def reader(url):
    return SnapshotReader(url)

if mode=='demo':
    st.info('가상 샘플 미리보기입니다. 운영 데이터를 보려면 새 앱의 Secrets에 기존 DB·자체 로그인 설정을 등록해주세요.')
    from classic_cloud.sample import snapshots
    def read_sources():
        data=snapshots()
        if hw_unit!='45호기':data['hw']={'revision':0,'state':{},'previews':{}}
        if generation=='8G':data['pending']={'revision':0,'state':{},'previews':{}}
        return data
elif mode=='postgres':
    if settings.get('login',{}).get('method')!='password':
        st.error('새 앱은 자체 로그인을 사용합니다. Secrets의 [login] method를 password로 설정해주세요.');st.stop()
    actor,_=require_local(settings)
    st.sidebar.caption(actor+' · 조회 전용')
    try:
        database=reader(settings.get('database',{}).get('url',''))
    except Exception:
        st.error('운영 DB 설정을 확인해주세요. Render PostgreSQL의 External Database URL이 필요합니다.');st.stop()
    config=settings.get('local_excel',{})
    def read_sources():
        hw={'revision':0,'state':{},'previews':{}}
        if generation=='6G':
            source_id=config.get('source_id','local-excel') if hw_unit=='45호기' else config.get('hw15_source_id','hw-15')
            hw=database.read(source_id)
        else:
            source86=config.get('hw86_source_id','hw-86')
            if source86 in (config.get('source_id','local-excel'),config.get('hw15_source_id','hw-15'),config.get('pending_source_id','pending-excel'),config.get('pending8_source_id','pending-8g')):
                raise ValueError('8.6G H/W 소스 ID가 중복됩니다.')
            hw=database.read(source86)
        pending_source=config.get('pending_source_id','pending-excel') if generation=='6G' else config.get('pending8_source_id','pending-8g')
        if generation=='8G' and pending_source==config.get('pending_source_id','pending-excel'):
            raise ValueError('6G/8G PENDING 소스 ID가 중복됩니다.')
        process={'revision':0,'state':{},'previews':{}}
        if generation=='6G' and hw_unit=='15호기':
            process_source=config.get('process15_source_id','process-15')
            if process_source in (config.get('source_id','local-excel'),config.get('hw15_source_id','hw-15'),pending_source):raise ValueError('공정 소스 ID 중복')
            process=database.read(process_source)
        return {'hw':hw,'pending':database.read(pending_source),'process':process}
else:
    st.error('저장 모드 설정을 확인해주세요.');st.stop()

try:
    initial=read_sources()
except Exception:
    st.error('동기화 데이터를 읽지 못했습니다. DB 연결과 cloud_local_excel 테이블의 조회 권한을 확인해주세요.');st.stop()

with st.sidebar:
    st.markdown('**🔷 양산 설비 통합 관리**')
    st.caption('PECVD 설비 · Excel 연동 조회')
    pages=['PENDING 현황','PENDING List REV관리','설비 H/W 이력관리']
    if generation=='6G' and hw_unit=='15호기':pages.append('H/W · 공정 Map')
    page=cards('화면 선택',pages,'classic_page')
    if st.button('Excel 동기화 요청',use_container_width=True):
        if mode=='postgres':
            try:
                SyncControl(database.engine).request(actor)
                st.session_state['manual_requested']=True
            except Exception:
                st.error('수동 동기화 요청을 등록하지 못했습니다. 새 수신 서버 배포와 DB 연결을 확인해주세요.')
        else:st.info('샘플 화면에서는 PC 동기화를 요청하지 않습니다.')
    st.caption('버튼을 누르면 PC에 Excel 동기화를 요청합니다. PC가 켜져 있고 예약 수신 기능이 등록되어 있어야 합니다.')
    st.caption('화면은 15초마다 수신 데이터를 확인합니다. 수정은 PC Excel에서 저장해주세요.')

filters={};chamber='전체';section='설비 현황';flatness='Diffuser';query=''
if page=='PENDING 현황':
    all_rows=model.pending_frame(initial['pending'])
    with st.sidebar:
        st.subheader('PENDING 현황 필터')
        scope=cards('조회 범위',['주요 5개 분야','보조 시트','전체 시트'],'classic_scope') if generation=='6G' else '주요 항목'
        frame=all_rows if scope=='전체 시트' else all_rows[all_rows['범위']==scope]
        equipment=st.multiselect('설비',sorted(frame['설비'].unique()),key='classic_equipment')
        categories=st.multiselect('분야',sorted(frame['분야'].unique()),key='classic_fields')
        states=st.multiselect('상태',['완료','미완료'],key='classic_states')
        search=st.text_input('검색',placeholder='내용·Unit·담당자·조치내용',key='classic_search')
    filters={'scope':scope,'equipment':equipment,'categories':categories,'states':states,'query':search}
    signature=str(filters)
    if st.session_state.get('classic_filter_signature')!=signature:
        st.session_state.classic_drill=None
        st.session_state.classic_filter_signature=signature
elif page=='설비 H/W 이력관리' and generation=='6G':
    with st.sidebar:
        st.subheader('H/W 조회 필터')
        chamber=st.selectbox('H/W 챔버',['전체','A','B','C','D','E'],key='classic_chamber')
        query=st.text_input('작업 이력 검색',key='classic_work_search')
    section=cards('H/W 메뉴',['설비 현황','작업 이력','부품 추적','Spacing','Flatness','데이터 관리'],'classic_hw_section',True)
    if section=='Flatness':flatness=cards('Flatness 항목',['Diffuser','Susceptor'],'classic_flat_part',True)

@st.fragment(run_every=15)
def content():
    guard_fragment()
    try:
        current=read_sources()
    except Exception:
        st.error('데이터 갱신에 실패했습니다. 잠시 후 다시 확인해주세요.');return
    if mode=='postgres':
        try:
            request=SyncControl(database.engine).status()
            if request:
                render_sync_status(request)
        except Exception:
            if st.session_state.get('manual_requested'):st.warning('수동 동기화 상태를 확인하지 못했습니다.')
    received=[(generation+' PENDING',current['pending'])]
    received.append(((generation if generation=='6G' else '8.6G')+' · '+hw_unit+' H/W',current['hw']))
    if generation=='6G' and hw_unit=='15호기':received.append(('15호기 공정 Map',current.get('process',{})))
    for label,snapshot in received:
        state=snapshot.get('state',{})
        stamp=state.get('received_at')
        if stamp:
            try:stamp=datetime.fromisoformat(stamp).astimezone(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')
            except ValueError:pass
            st.caption(f'{label} 마지막 수신: {stamp} · 수신 버전 {snapshot["revision"]}')
        else:st.caption(label+' · 수신 대기')
        if state.get('warning'):st.warning(label+': '+state['warning'])
        if state.get('pending_status')=='conflict':
            st.warning('기존 앱 DB 반영에 충돌이 있습니다. 새 앱은 가장 최근 수신한 Excel 스냅샷을 표시합니다. 기존 앱의 충돌 내역을 별도로 확인해주세요.')
    if page=='H/W · 공정 Map':process_views.process_panel(current.get('process',{}),current['hw'])
    elif page=='PENDING 현황':views.pending(current['pending'],filters,generation)
    elif page=='PENDING List REV관리':views.revisions(current['pending'],generation)
    elif generation=='8G':hw86_views.hardware(current['hw'])
    else:views.hardware(current['hw'],chamber,section,flatness,query,generation+' · '+hw_unit)

content()

