"""Read the latest received workbook; never open a path on the visitor's PC."""
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st


def render_one(repo, settings, mode, source_id, show_sheets=False):
    if mode != 'postgres':
        if show_sheets:
            st.info('샘플 모드입니다. 실제 자동 동기화를 사용하려면 운영 DB·로그인·수신 서버 설정이 필요합니다.')
            st.markdown('[로컬 Excel 연결 순서 보기](https://github.com/alsduf452-coder/New-H-W-/blob/main/docs/LOCAL_EXCEL.md)')
            st.write('PC의 install.bat 실행 → config.toml에 파일·서버 주소 설정 → start.bat 실행 순서로 연결합니다.')
        return

    @st.fragment(run_every=15)
    def view():
        from login_ui import guard_fragment
        guard_fragment()
        try:
            state = repo.local_status(source_id)
            if not state['revision']:
                if show_sheets:
                    st.info('아직 PC에서 받은 Excel이 없습니다. 동기화 프로그램을 실행해주세요.')
                return
            received = datetime.fromisoformat(state['received_at']).astimezone(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
            st.caption(f'[{source_id}] 마지막 수신: {received} KST · 화면은 15초마다 확인 · PC 연결 상태를 뜻하지 않습니다.')
            if state.get('warning'):
                st.warning(state['warning'])
            if state.get('conflicts'):
                st.error('Excel과 앱의 변경이 충돌하여 PENDING 반영을 보류했습니다. 양쪽 항목을 확인하여 같은 값으로 맞춰주세요.')
                st.dataframe(state['conflicts'], hide_index=True, use_container_width=True)
            elif state.get('mode') == 'hw':
                st.caption(f"H/W 반영 완료 · 측정 기록 {state.get('hw_records', 0)}건")
            elif state.get('pending_status') == 'applied':
                st.caption(f"PENDING 반영 완료 · 원본 {state.get('pending_records', '—')}건 · Excel에서 빠진 항목은 DB에 유지합니다.")
            if state.get('pending_warnings'):
                st.warning(f"날짜 확인이 필요한 목표일 {state['pending_warnings']}건입니다. 로컬 Excel 연동에서 원문을 확인해주세요.")
            if not show_sheets:
                return
            cache_key = (source_id, state['revision'])
            if st.session_state.get('local_preview_key') != cache_key:
                st.session_state.local_preview_data = repo.local_previews(source_id)
                st.session_state.local_preview_key = cache_key
            previews = dict(st.session_state.local_preview_data)
            hw = previews.pop('__hw_data__', None)
            pending = previews.pop('__pending_data__', None)
            if pending:
                st.subheader('PENDING 원본 항목')
                st.caption('HW(설계)·공정·전장·SW·기타 5개 시트 합계입니다. 고객사 요청 등 보조 시트는 별도 미리보기로 제공합니다.')
                st.dataframe(pd.DataFrame(pending['details']), hide_index=True, use_container_width=True)
                if pending['warnings']:
                    with st.expander('목표일 확인 필요', expanded=True):
                        st.dataframe(pending['warnings'], hide_index=True, use_container_width=True)
            if hw:
                from hw_ui import render_hw
                render_hw(hw)
                st.subheader('원본 시트 미리보기')
            st.caption('시트별 값 미리보기 · 최대 시트당 500행·50열 / 전체 100,000셀 · Excel 서식·병합·차트는 복제하지 않습니다. 긴 셀은 2,000자까지만 표시합니다.')
            if not previews:
                st.info('표시할 시트가 없습니다.'); return
            for tab, (name, preview) in zip(st.tabs(list(previews)), previews.items()):
                with tab:
                    data = preview['rows']
                    if not data:
                        st.info('빈 시트입니다.'); continue
                    header = st.number_input('머리글 행 (0: 원본 행 그대로 표시)', min_value=0, max_value=min(100, len(data)), value=0, step=1, key='local_header_' + source_id + '_' + name)
                    frame = pd.DataFrame(data[header:] if header else data)
                    if header:
                        names = [str(v).strip() for v in data[header-1]]
                        names = [name or f'열 {i+1}' for i, name in enumerate(names)]
                        names = [name + f' ({i+1})' if names.count(name) > 1 else name for i, name in enumerate(names)]
                        frame = frame.reindex(columns=range(len(names)))
                        frame.columns = names
                    else:
                        frame.columns = [f'열 {i+1}' for i in range(len(frame.columns))]
                    st.dataframe(frame, hide_index=True, use_container_width=True, height=min(600, max(150, 36*(len(frame)+1))))
                    if preview['truncated']:
                        st.caption('큰 시트의 일부만 표시합니다. PENDING 반영은 별도로 최대 5,000행까지 처리합니다.')
        except Exception:
            st.error('수신 상태를 읽지 못했습니다. 잠시 후 다시 확인해주세요.')
    view()



def render_local(repo, settings, mode, show_sheets=False):
    options = settings.get('local_excel', {})
    sources = [options.get('source_id', 'local-excel'), options.get('pending_source_id', 'pending-excel')]
    sources = list(dict.fromkeys(sources))
    if mode != 'postgres':
        render_one(repo, settings, mode, sources[0], show_sheets)
    elif show_sheets:
        selected = st.selectbox('연동 파일', sources, format_func=lambda value: 'H/W · '+value if value==sources[0] else 'PENDING · '+value)
        render_one(repo, settings, mode, selected, True)
    else:
        for source in sources:
            render_one(repo, settings, mode, source, False)
