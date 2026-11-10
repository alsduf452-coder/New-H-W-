from html import escape
import pandas as pd
import streamlit as st
from process_map import link_measurement,KINDS
from classic_cloud.visuals import diagram_svg,detail


def map_html(grid):
    values=[v for row in grid for v in row if v is not None]
    if not values:return '<div style="height:300px;border:1px solid #cbd5e1;background:#f1f5f9;display:flex;align-items:center;justify-content:center;font-size:24px">Data 없음</div>'
    low,high=min(values),max(values);rows=[]
    for row in grid:
        cells=[]
        for v in row:
            ratio=(v-low)/(high-low) if v is not None and high!=low else .5
            color='#e2e8f0' if v is None else f'hsl({120*(1-ratio):.1f},65%,78%)'
            cells.append(f'<td style="background:{color};text-align:center;padding:20px;border:1px solid #cbd5e1">{v:g}</td>' if v is not None else '<td style="text-align:center;background:#e2e8f0">Data 없음</td>')
        rows.append('<tr>'+''.join(cells)+'</tr>')
    return '<table style="width:100%;table-layout:fixed;color:#17324d">'+''.join(rows)+'</table>'


def process_panel(process_snapshot,hw_snapshot):
    st.header('6G · 15호기 H/W 형상 · 공정 Map 비교')
    data=process_snapshot.get('previews',{}).get('__process_data__')
    if not data:st.info('15호기 공정 Map 파일 수신을 기다리고 있습니다.');return
    records=data['records']
    chamber=st.selectbox('공정 PC',list('ABCDE'),key='process15_pc')
    runs=sorted([r for r in records if r['chamber']==chamber],key=lambda r:(r['date'],r['source_cell']),reverse=True)
    if not runs:st.info('평가 기록이 없습니다.');return
    by_id={r['id']:r for r in runs}
    run=by_id[st.selectbox('공정 평가 기록',list(by_id),format_func=lambda k:by_id[k]['date']+' · '+by_id[k]['recipe']+' · '+by_id[k]['source_cell'],key='process15_run_'+chamber)]
    st.caption('평가일 '+run['date']+' · PC '+chamber+' · Recipe '+run['recipe']+' · Dep Time '+run['dep_time'])
    measurements=hw_snapshot.get('previews',{}).get('__hw_data__',{}).get('measurements',[])
    for col,kind in zip(st.columns(3),KINDS):
        with col:
            st.subheader(kind)
            linked,reason=link_measurement(run,measurements,kind)
            if linked:
                st.caption('H/W 측정일 '+linked['date']+' · '+linked['id'])
                st.markdown(diagram_svg(linked['grid'],kind=='Spacing'),unsafe_allow_html=True)
                st.caption(linked['reason'])
            else:
                st.markdown('<div style="height:250px;border:1px solid #cbd5e1;display:flex;align-items:center;justify-content:center">연결 확인 필요</div>',unsafe_allow_html=True)
                st.caption(reason)
    st.caption('평가일 당일/이전 최근 측정일 기준 · 미래 측정값 제외 · S/N 불일치/동일 날짜 중복은 자동 연결하지 않습니다.')
    left,right=st.columns([3,2])
    with left:
        st.subheader('D/R 공정 Map')
        st.markdown(map_html(run['grid']),unsafe_allow_html=True)
        st.markdown('**Unif. '+(f"{run['unif']:.2f}%" if run['unif'] is not None else 'Data 없음')+'**')
    with right:
        st.subheader('평가 조건 및 변경 메모')
        detail([('평가일',run['date']),('PC',run['chamber']),('Recipe',run['recipe']),('Dep Time',run['dep_time']),('Diffuser S/N',run['diffuser_sn']),('Susceptor S/N',run['susceptor_sn']),('HCG',run['hcg']),('평가 메모',run['notes'])])
    st.caption('출처: Unif 결과 데이터!'+run['source_cell']+' · 좌표 숫자는 표시하지 않습니다. Unif.는 Excel 원본값입니다.')
