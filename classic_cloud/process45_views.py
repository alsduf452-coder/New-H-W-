"""45-unit comparison from the five PC sheets, without placeholder results."""
import pandas as pd
import streamlit as st
from process45 import KINDS, link_process45, numeric
from classic_cloud.visuals import diagram_svg
from classic_cloud.process_views import map_html


def measurement_chart(grid, title, spacing=False, process=False):
    if not any(numeric(value) for line in grid for value in line):
        return
    # Reuse the 15-unit renderers. The 45-unit sheets place G/V at
    # the top of their 7x5 flatness grid, so retain that orientation.
    html = map_html(grid).replace('Data 없음', '—') if process else diagram_svg(grid, spacing, orientation='rows')
    st.markdown(html, unsafe_allow_html=True)


def process45_panel(snapshot):
    st.header('6G · 45호기 H/W 형상 · 공정 Map 비교')
    data = snapshot.get('previews', {}).get('__process_data__')
    if not data or data.get('equipment') != '45호기':
        st.info('45호기 공정 파일 수신을 기다리고 있습니다.')
        return
    chamber = st.selectbox('공정 PC', list('ABCDE'), key='process45_pc')
    runs = sorted([r for r in data['records'] if r['chamber'] == chamber],
                  key=lambda r: (r['date'], r['mt_date'], r['recipe'], r['source_cell']), reverse=True)
    if not runs:
        st.info('조회할 공정 결과가 없습니다.')
        return
    by_id = {r['id']: r for r in runs}
    def label(identifier):
        run = by_id[identifier]
        suffix = ' · MT '+run['mt_date'] if run['mt_date'] and run['mt_date'] != run['date'] else ''
        return run['date']+' · '+run['recipe']+suffix
    selected = st.selectbox('공정 평가 기록', list(by_id), format_func=label, key='process45_run_'+chamber)
    run = by_id[selected]
    st.caption('평가일 '+run['date']+' · PC '+chamber+' · '+run['recipe'])
    st.caption('Diffuser S/N: '+(run['diffuser_sn'] or '미기재')+' · Susceptor S/N: '+(run['susceptor_sn'] or '미기재'))
    for col, kind in zip(st.columns(3), KINDS):
        with col:
            st.subheader(kind)
            measured, reason = link_process45(run, data['measurements'], kind)
            if measured:
                st.caption('H/W 측정일 '+measured['date'])
                st.caption('Diffuser S/N: '+measured['diffuser_sn']+' · Susceptor S/N: '+measured['susceptor_sn'])
                st.caption('▲ G/V 측 · ▼ Window 측')
                measurement_chart(measured['grid'], kind, kind == 'Spacing')
            else:
                st.caption(reason)
    st.caption('선택한 평가 블록의 측정일·S/N 기준 · 공정 평가일 이후 측정값 제외')
    has_map = any(numeric(v) for row in run['grid'] for v in row)
    metrics = []
    for key, value in run['metrics'].items():
        formatted = f'{value*100:.2f}%' if key == 'Unif.' and numeric(value) else f'{value:g}' if numeric(value) else str(value)
        metrics.append({'항목': key, '값': formatted})
    if has_map:
        left, right = st.columns([3, 2])
        with left:
            st.subheader(run['recipe']+' 공정 Map')
            st.caption('▲ G/V 측 · ▼ Window 측')
            measurement_chart(run['grid'], run['recipe']+' 공정 Map', process=True)
        with right:
            st.subheader('공정 결과')
            if metrics:
                st.table(pd.DataFrame(metrics).set_index('항목'), alt='실제 값이 있는 공정 결과 항목')
    elif metrics:
        st.subheader('공정 결과')
        st.table(pd.DataFrame(metrics).set_index('항목'), alt='실제 값이 있는 공정 결과 항목')
