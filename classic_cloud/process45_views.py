"""45-unit comparison from the five PC sheets, without placeholder results."""
import pandas as pd
import streamlit as st
from classic_cloud.evaluation_compare import comparison_navigation, comparison_panel
from process45 import KINDS, link_process45, link_spacing_history, numeric
from classic_cloud.visuals import diagram_svg
from classic_cloud.process_views import map_html


def flatness_history_grid(grid):
    """PC rows run G/V to Window; PC columns run opposite to H/W rows.

    A 90-degree counterclockwise rotation matches the H/W history's 5x7
    coordinates. A transpose alone mirrors the top and bottom rows.
    """
    return [list(column) for column in zip(*grid)][::-1]


def measurement_chart(grid, title, spacing=False, process=False):
    if not any(numeric(value) for line in grid for value in line):
        return
    # Keep Spacing point positions and process maps in their source order.
    # Only Flatness needs rotation to the H/W history coordinate system.
    display_grid = grid if spacing or process else flatness_history_grid(grid)
    html = map_html(display_grid).replace('Data 없음', '—') if process else diagram_svg(display_grid, spacing, show_position_labels=False,match_spacing_size=True)
    if process:
        html = ('<div style="display:grid;grid-template-columns:28px minmax(0,1fr) 28px;align-items:center;gap:8px">'
                '<div style="justify-self:center;writing-mode:vertical-rl;transform:rotate(180deg);white-space:nowrap;color:#075985;font-size:13px">G/V 측</div>'
                '<div style="min-width:0">'+html+'</div>'
                '<div style="justify-self:center;writing-mode:vertical-rl;white-space:nowrap;color:#075985;font-size:13px">Window 측</div></div>')
    st.markdown(html, unsafe_allow_html=True)


def process45_panel(snapshot, hw_snapshot=None):
    st.header('6G · 45호기 H/W 형상 · 공정 Map 비교')
    data = snapshot.get('previews', {}).get('__process_data__')
    if not data or data.get('equipment') != '45호기':
        st.info('45호기 공정 파일 수신을 기다리고 있습니다.')
        return
    layout=st.segmented_control('화면 배치',['기본 보기','한 화면 보기'],default='한 화면 보기',key='process_layout_45')
    if layout=='한 화면 보기':
        from classic_cloud.compact_process import compact_panel
        compact_panel('45',data,hw_snapshot or {})
        return
    chamber = st.selectbox('공정 PC', list('ABCDE'), key='process45_pc')
    runs = sorted([r for r in data['records'] if r['chamber'] == chamber],
                  key=lambda r: (r['date'], r['mt_date'], r['recipe'], r['source_cell']), reverse=True)
    if not runs:
        st.info('조회할 공정 결과가 없습니다.')
        return
    comparison_mode = comparison_navigation('45', chamber)
    by_id = {r['id']: r for r in runs}
    def label(identifier):
        run = by_id[identifier]
        suffix = ' · MT '+run['mt_date'] if run['mt_date'] and run['mt_date'] != run['date'] else ''
        return run['date']+' · '+run['recipe']+suffix+' · '+run['source_cell']
    selected = st.selectbox('공정 평가 기록', list(by_id), format_func=label, key='process45_run_'+chamber)
    run = by_id[selected]
    if comparison_panel('45', chamber, runs, run, data, hw_snapshot or {}, comparison_mode):
        return
    hw_measurements = (hw_snapshot or {}).get('previews', {}).get('__hw_data__', {}).get('measurements', [])
    st.caption('평가일 '+run['date']+' · PC '+chamber+' · '+run['recipe'])
    st.caption('Diffuser S/N: '+(run['diffuser_sn'] or '미기재')+' · Susceptor S/N: '+(run['susceptor_sn'] or '미기재'))
    for col, kind in zip(st.columns(3), KINDS):
        with col:
            st.subheader(kind)
            measured, reason = (link_spacing_history(run, data['measurements'], hw_measurements)
                                if kind == 'Spacing' else link_process45(run, data['measurements'], kind))
            if measured:
                st.caption('H/W 측정일 '+measured['date'])
                measurement_chart(measured['grid'], kind, kind == 'Spacing')
            else:
                st.caption(reason)
    has_map = any(numeric(v) for row in run['grid'] for v in row)
    metrics = []
    for key, value in run['metrics'].items():
        formatted = f'{value*100:.2f}%' if key == 'Unif.' and numeric(value) else f'{value:g}' if numeric(value) else str(value)
        metrics.append({'항목': key, '값': formatted})
    if has_map:
        left, right = st.columns([3, 2])
        with left:
            st.subheader(run['recipe']+' 공정 Map')
            measurement_chart(run['grid'], run['recipe']+' 공정 Map', process=True)
        with right:
            st.subheader('공정 결과')
            if metrics:
                st.table(pd.DataFrame(metrics).set_index('항목'), alt='실제 값이 있는 공정 결과 항목')
    elif metrics:
        left, _ = st.columns([1, 1])
        with left:
            st.subheader('공정 결과')
            st.table(pd.DataFrame(metrics).set_index('항목'), alt='실제 값이 있는 공정 결과 항목')

