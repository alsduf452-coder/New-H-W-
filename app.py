"""Cloud-01: separate Pending cloud starter, with reviewed Excel imports."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from uuid import uuid4
from hashlib import sha256
import pandas as pd
import streamlit as st
from cloud_store import Repository, ConflictError
from domain import CATEGORIES, STATES, FIELDS, ValidationError, access_role, build_plan
from excel_sync import pending_excel, read_pending_excel
from sample_data import sample_items

st.set_page_config(page_title='양산 설비 통합 관리 · Cloud', layout='wide')
st.title('양산 설비 통합 관리 · Cloud')
st.caption('CLOUD-02 · PENDING 및 로컬 Excel 연동')
try:
    settings = dict(st.secrets)
except FileNotFoundError:
    settings = {}
mode = settings.get('storage', {}).get('mode', 'demo')

@st.cache_resource
def persistent_repository(url):
    return Repository(url)

if mode == 'demo':
    st.info('샘플 체험 모드입니다. 데이터는 현재 세션에만 저장되며 세션 종료 시 사라집니다. 실제 업무 데이터는 입력하지 마세요.')
    if 'demo_repository' not in st.session_state:
        st.session_state.demo_repository = Repository()
        for item in sample_items():
            st.session_state.demo_repository.save_item(item, 'sample')
    repo = st.session_state.demo_repository
    actor, role = 'demo-session', 'editor'
elif mode == 'postgres':
    auth = settings.get('auth', {})
    access = settings.get('access', {})
    url = settings.get('database', {}).get('url', '')
    required = ('client_id', 'client_secret', 'cookie_secret', 'redirect_uri', 'server_metadata_url')
    if not all(auth.get(k) for k in required) or not isinstance(access.get('allowed_emails'), list) or not access['allowed_emails'] or not url.startswith(('postgres://', 'postgresql://', 'postgresql+psycopg://')):
        st.error('운영 모드는 PostgreSQL, OIDC 로그인, 허용 계정 설정이 필요합니다. README를 확인해주세요.')
        st.stop()
    if not st.user.is_logged_in:
        if st.button('계정으로 로그인'):
            st.login()
        st.stop()
    actor = st.user.get('email', '')
    role = access_role(actor, access['allowed_emails'], access.get('editor_emails', []))
    if st.sidebar.button('로그아웃'):
        st.session_state.clear()
        st.logout()
    if role is None:
        st.error('이 앱에 허용된 계정이 아닙니다. 관리자에게 문의해주세요.')
        st.stop()
    try:
        repo = persistent_repository(url)
    except Exception:
        st.error('DB 연결에 실패했습니다. 관리자에게 연결 설정을 확인해주세요.')
        st.stop()
    st.sidebar.caption(f'{actor} · {role}')
else:
    st.error('지원하지 않는 저장 모드입니다.')
    st.stop()

page = st.sidebar.radio('화면 선택', ['PENDING 현황', 'Excel 동기화', '로컬 Excel 연동', '변경 이력'])
if st.sidebar.button('최신 데이터 새로고침'):
    for key in list(st.session_state):
        if key.startswith('snapshot_') or key == 'import_plan':
            del st.session_state[key]
    st.rerun()
if message := st.session_state.pop('flash', None):
    st.success(message)
from local_ui import render_local
if page in ('PENDING 현황', '로컬 Excel 연동'):
    render_local(repo, settings, mode, show_sheets=page == '로컬 Excel 연동')
try:
    rows = repo.list_items()
except Exception:
    st.error('데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.')
    st.stop()


def save_form(old=None):
    old = old or {}
    key = old.get('ID', 'new')
    # Keep the version associated with the displayed form until submission.
    snapshot_key = 'snapshot_' + key
    if snapshot_key not in st.session_state:
        st.session_state[snapshot_key] = dict(old)
    snapshot = st.session_state[snapshot_key]
    with st.form('edit_' + key):
        a, b = st.columns(2)
        equipment = a.text_input('설비', value=old.get('설비', ''))
        category = b.selectbox('분야', CATEGORIES, index=CATEGORIES.index(old.get('분야', CATEGORIES[0])))
        state = a.selectbox('상태', STATES, index=STATES.index(old.get('상태', STATES[0])))
        owner = b.text_input('담당자', value=old.get('담당자', ''))
        description = st.text_area('내용', value=old.get('내용', ''))
        target = st.date_input('목표일', value=date.fromisoformat(old['목표일']) if old.get('목표일') else None)
        submitted = st.form_submit_button('저장')
    if submitted:
        values = {'ID': old.get('ID', 'CLD-' + uuid4().hex[:16]), '설비': equipment, '분야': category, '상태': state, '담당자': owner, '내용': description, '목표일': target}
        try:
            repo.save_item(values, actor, snapshot.get('버전', 0))
        except (ValidationError, ConflictError) as exc:
            st.error(str(exc))
            if isinstance(exc, ConflictError):
                st.caption('사이드바의 최신 데이터 새로고침을 눌러 최신 값을 확인해주세요.')
        else:
            st.session_state.pop(snapshot_key, None)
            st.session_state.flash = '저장했습니다.'
            st.rerun()

if page == 'PENDING 현황':
    @st.fragment(run_every=15)
    def pending_dashboard():
        st.subheader('PENDING 현황')
        rows = repo.list_items()
        equipment = st.selectbox('설비 필터', ['전체'] + sorted({r['설비'] for r in rows}))
        filtered = [r for r in rows if equipment == '전체' or r['설비'] == equipment]
        total = len(filtered); done = sum(r['상태'] == '완료' for r in filtered)
        for col, label, value in zip(st.columns(4), ['전체 건수', '완료', '미완료', '완료율'], [total, done, total-done, f'{done/total*100:.1f}%' if total else '0.0%']):
            col.metric(label, value)
        st.dataframe(pd.DataFrame(filtered), hide_index=True, use_container_width=True)
        today = datetime.now(ZoneInfo('Asia/Seoul')).date()
        counts = {'기한초과': 0, '임박': 0, '여유': 0}; missing = 0
        for row in filtered:
            if row['상태'] != '미완료':
                continue
            if not row['목표일']:
                missing += 1; continue
            days = (date.fromisoformat(row['목표일']) - today).days
            counts['기한초과' if days < 0 else '임박' if days <= 7 else '여유'] += 1
        import plotly.graph_objects as go
        with st.columns(2)[0]:
            st.subheader('미완료 목표일 현황')
            fig = go.Figure(go.Bar(x=list(counts), y=list(counts.values()), marker_color=['#dc2626', '#f59e0b', '#2563eb']))
            fig.update_layout(height=280, margin=dict(l=20, r=20, t=20, b=20), yaxis=dict(dtick=1))
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f'한국 날짜 기준 · 임박: 오늘~7일 후 · 목표일 미입력 {missing}건')
    pending_dashboard()
    if role == 'editor':
        with st.expander('새 PENDING 등록'):
            save_form()
        if rows:
            selected = st.selectbox('수정할 항목', [r['ID'] for r in rows])
            if st.session_state.get('selected_id') != selected:
                for k in list(st.session_state):
                    if k.startswith('snapshot_'):
                        del st.session_state[k]
                st.session_state.selected_id = selected
            with st.expander('선택 항목 수정'):
                save_form(next(r for r in rows if r['ID'] == selected))
elif page == 'Excel 동기화':
    st.subheader('Excel 동기화')
    st.write('최신 Excel 다운로드 → Excel 값 수정 → 파일 업로드 → 변경 비교 → 확인 후 반영 순서입니다.')
    st.caption('수동 업로드 화면입니다. PC Excel 자동 연결은 로컬 Excel 연동 화면에서 확인할 수 있습니다.')
    st.download_button('전체 PENDING 연동 Excel 다운로드', pending_excel(rows), 'Cloud_PENDING.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    if role != 'editor':
        st.info('조회 권한입니다. 변경 반영은 편집 계정으로 로그인해주세요.')
        st.stop()
    upload = st.file_uploader('수정한 연동 Excel', type=['xlsx'])
    if upload:
        content = upload.getvalue(); digest = sha256(content).hexdigest()
        if st.button('변경사항 비교'):
            st.session_state.pop('import_plan', None)
            try:
                plan = build_plan(repo.list_items(), read_pending_excel(content))
                st.session_state.import_plan = (digest, plan)
            except ValidationError as exc:
                st.error(str(exc))
            except Exception:
                st.error('파일을 읽지 못했습니다. 앱에서 받은 정상적인 Excel 파일인지 확인해주세요.')
        saved = st.session_state.get('import_plan')
        if saved and saved[0] == digest:
            plan = saved[1]
            st.write(f"반영 대상 {len(plan['changes'])}건 · 충돌 {len(plan['conflicts'])}건 · 동일 {len(plan['unchanged'])}건 · 파일에서 빠진 항목 {len(plan['missing'])}건")
            diff = []
            for change in plan['changes']:
                before = change.get('before') or {}
                for field in FIELDS:
                    if before.get(field) != change['after'][field]:
                        diff.append({'ID': change['id'], '항목': field, '기존': before.get(field, ''), '변경': change['after'][field]})
            if diff:
                st.dataframe(pd.DataFrame(diff), hide_index=True, use_container_width=True)
            if plan['conflicts']:
                st.error('충돌이 있습니다. 최신 Excel로 변경사항을 다시 대조해주세요.')
                st.dataframe(plan['conflicts'], hide_index=True)
            if plan['missing']:
                st.info('파일에서 빠진 항목은 기존 DB에 유지됩니다.')
            reviewed = st.checkbox('위 변경사항을 확인했습니다.', key='review_' + digest)
            if st.button('변경사항 반영', disabled=not reviewed or bool(plan['conflicts']) or not plan['changes']):
                try:
                    count = repo.apply_plan(plan, actor)
                except (ValidationError, ConflictError) as exc:
                    st.error(str(exc))
                else:
                    st.session_state.pop('import_plan', None)
                    for k in list(st.session_state):
                        if k.startswith('snapshot_'):
                            del st.session_state[k]
                    st.session_state.flash = f'{count}건을 반영했습니다.'
                    st.rerun()
elif page == '로컬 Excel 연동':
    st.caption('PENDING 열 연결은 수신 서버의 SYNC_MAPPING_JSON에서 설정합니다.')
else:
    st.subheader('변경 이력')
    events = repo.list_events()
    display = [{'시간(KST)': datetime.fromisoformat(e['created_at']).astimezone(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S'), 'ID': e['item_id'], '변경자': e['actor'], '작업': e['action'], '버전': e['after_value']['버전']} for e in events]
    st.caption('최근 500건 · 저장 전후 값과 변경자를 기록합니다.')
    st.dataframe(pd.DataFrame(display), hide_index=True, use_container_width=True)
    if events:
        selected = st.selectbox('변경 상세', range(len(events)), format_func=lambda i: f"{events[i]['seq']} · {events[i]['item_id']}")
        a, b = st.columns(2)
        a.write('변경 전'); a.json(events[selected]['before_value'])
        b.write('변경 후'); b.json(events[selected]['after_value'])
