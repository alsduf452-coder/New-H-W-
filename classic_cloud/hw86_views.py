"""8.6G measurement history with source-position-preserving comparisons."""
from hashlib import sha256
from html import escape
import json
import pandas as pd
import streamlit as st
from hw86_excel import delta
from classic_cloud.visuals import cards
from classic_cloud.model import workbook_export


def grid_table(grid,title):
    st.markdown('**'+title+'**')
    # Keep sparse positions: blanks are not zero or assumed measurement points.
    rows=''.join('<tr>'+''.join('<td style="padding:10px;border:1px solid #cbd5e1;text-align:center">'+(f'{v:g}' if v is not None else '—')+'</td>' for v in row)+'</tr>' for row in grid)
    st.markdown('<table style="width:100%;background:#f1f5f9;color:#17324d">'+rows+'</table>',unsafe_allow_html=True)


def label(record):
    return (record['date'] or '날짜 확인 필요')+' · '+record['title'].splitlines()[0]+' · '+record['cell']


def hardware(snapshot):
    st.header('8.6G · A6 BP-04 H/W 이력관리')
    data=snapshot.get('previews',{}).get('__hw86_data__')
    if not data:
        st.info('8.6G H/W 파일 수신을 기다리고 있습니다.');return
    kind=cards('H/W 메뉴',['Diffuser Flatness','Susceptor Flatness','Spacing','Shim 변경이력'],'hw86_kind',True)
    search=st.text_input('측정 이력 검색',placeholder='날짜·평가 차수·온도 조건·부품 번호',key='hw86_search')
    records=[r for r in data['measurements'] if r['kind']==kind and all(t.casefold() in (r['title']+' '+r['notes']+' '+r['date']).casefold() for t in search.split())]
    records.sort(key=lambda r:(r['date'],r['row'],r['column']),reverse=True)
    st.caption('원본 위치 배열 유지 · Excel 편차 표 제외 · 날짜 없는 기록은 목록 하단에 표시합니다.')
    if data.get('warnings'):
        with st.expander('날짜 확인 필요'):
            for message in data['warnings']:st.write(message)
    if not records:st.info('검색 결과가 없습니다.');return
    frame=pd.DataFrame([{'일자':r['date'] or '확인 필요','기록':r['title'].splitlines()[0],
        '조건':r['condition'],'구분':r['representation'],'메모':r['notes'],'측정점':r['stats']['count'],
        '중앙':r['stats']['center'],'최소':r['stats']['min'],'최대':r['stats']['max'],'Max−Min':r['stats']['range'],'원본 위치':r['cell']} for r in records])
    signature=sha256(json.dumps(records,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16]
    selection=st.dataframe(frame,hide_index=True,use_container_width=True,on_select='rerun',selection_mode='single-row',key='hw86_rows_'+signature)
    st.caption('행을 클릭하면 하단에 측정값과 변경 이력이 표시됩니다. 빈칸·X·미측정은 계산에서 제외합니다.')
    st.download_button('이력 목록 다운로드',workbook_export({'측정 이력':frame}),'8.6G_HW_history.xlsx',key='hw86_download')
    positions=selection.selection.rows
    if not positions or not 0<=positions[0]<len(records):return
    current=records[positions[0]]
    st.subheader('측정 상세')
    st.write(current['title'])
    if current['notes']:st.write(current['notes'])
    st.caption('원본: '+current['sheet']+'!'+current['cell'])
    grid_table(current['grid'],'당시 Susceptor Flatness' if kind=='Shim 변경이력' else kind)
    for note in current['cell_notes']:st.caption(note)
    if kind=='Shim 변경이력':
        grid_table(current['shim'],'위치별 Shim 두께 · Excel 배치')
        for note in current['shim_notes']:st.write(note)
    st.caption('숫자는 Excel 원문 단위를 유지합니다. 배열 중앙값과 전체 범위(Max−Min)는 실측값으로 계산합니다.')
    candidates=[r for r in records if r['id']!=current['id'] and len(r['grid'])==len(current['grid'])]
    if not candidates:return
    if st.checkbox('기준 기록과 비교',key='hw86_compare_'+signature):
        by_id={r['id']:r for r in candidates}
        baseline=by_id[st.selectbox('기준 기록',list(by_id),format_func=lambda k:label(by_id[k]),key='hw86_baseline_'+signature)]
        st.caption('계산 방향: 선택한 상세 기록 − 기준 기록 · 같은 상대 위치에 양쪽 모두 측정값이 있는 경우만 계산합니다.')
        if baseline['condition']!=current['condition']:st.info('서로 다른 측정 조건의 기록입니다. 조건 차이를 함께 확인해주세요.')
        if baseline['representation']!=current['representation']:st.info('원본 측정과 변환표 비교입니다. 측정 위치 대응을 확인해주세요.')
        grid_table(delta(baseline,current),'Flatness 변화량' if kind=='Shim 변경이력' else '측정 변화량')
        if kind=='Shim 변경이력':grid_table(delta(baseline,current,'shim'),'Shim 두께 변화량')
