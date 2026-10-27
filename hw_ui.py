"""Read-only H/W views backed by the most recently received workbook."""
from collections import Counter
import pandas as pd
import streamlit as st
from hw_excel import numeric, CHAMBERS


def display(value):
    return '—' if value is None or value == '' else str(value)


def render_hw(hw):
    st.subheader('설비 H/W 이력·측정 데이터')
    st.caption('Excel 원본 기준 · 이 화면은 조회 전용이며 수정은 PC의 Excel에서 저장합니다. 빈칸은 미측정, 0은 실측값입니다.')
    tabs = st.tabs(['장착 부품', '작업·교체 이력', 'Spacing', 'Diffuser Flatness', 'Susceptor Flatness'])
    with tabs[0]:
        rows = []
        for part in hw['parts']:
            row = {'부품': part}
            for chamber in CHAMBERS:
                item = hw['installed'][chamber].get(part)
                row['Chamber '+chamber] = f"{item['sn']}\n기록일: {item['date']}" if item else '—'
            rows.append(row)
        st.dataframe(pd.DataFrame(rows).style.set_properties(subset=['부품'], **{'text-align':'center'}), hide_index=True, use_container_width=True, row_height=65)
        st.caption('이력 시트의 최신 비어 있지 않은 S/N을 부품별로 표시합니다. 측정 시트의 S/N으로 장착 이력을 덮어쓰지 않습니다.')
    with tabs[1]:
        for event in sorted(hw['history'],key=lambda e:(e['date'],e['source_row']),reverse=True):
            with st.container(border=True):
                st.write(f"**Chamber {event['chamber']} · {event['date']}**")
                st.write(event['reason'])
                st.dataframe([{'부품':p,'S/N':sn} for p,sn in event['parts'].items()],hide_index=True,use_container_width=True)
                st.caption(event['source'])
    for tab,kind in zip(tabs[2:],('Spacing','Diffuser Flatness','Susceptor Flatness')):
        with tab:
            records = [r for r in hw['measurements'] if r['kind']==kind]
            summary = []
            for chamber in CHAMBERS:
                matches = [r for r in records if r['chamber']==chamber]
                if not matches:
                    summary.append({'챔버':chamber,'최신 측정일':'—'});continue
                r = max(matches,key=lambda r:(r['date'],r['source_row']))
                summary.append({'챔버':chamber,'최신 측정일':r['date'],'Center (⑤)' if kind=='Spacing' else 'Center (R3C4)':display(r['center']),'최소값':display(r['min']),'최대값':display(r['max']),'Max-Min':display(r['range']),'측정 개수':f"{r['count']}/{r['total']}"})
            st.write('**챔버별 최신 측정 요약**')
            st.dataframe(summary,hide_index=True,use_container_width=True)
            st.caption('같은 날짜에 여러 기록이 있으면 Excel의 아래쪽 기록을 최신으로 표시합니다. 측정값의 단위·정확성은 원본 기준입니다.')
            months = Counter(r['date'][:7] for r in records)
            with st.columns(2)[0]:
                st.write('**월별 측정 횟수**')
                st.bar_chart(pd.DataFrame({'월':sorted(months),'측정 횟수':[months[m] for m in sorted(months)]}).set_index('월'),height=240)
            chamber = st.selectbox('챔버',CHAMBERS,key='hw_chamber_'+kind)
            choices = sorted([r for r in records if r['chamber']==chamber],key=lambda r:(r['date'],r['source_row']),reverse=True)
            if not choices:
                st.info('측정 기록이 없습니다.');continue
            identifier = st.selectbox('측정 기록',[r['id'] for r in choices],format_func=lambda identifier:next(f"{r['date']} · {r['reason']} · {r['id']}" for r in choices if r['id']==identifier),key='hw_record_'+kind)
            record = next(r for r in choices if r['id']==identifier)
            st.caption(f"Diffuser S/N: {display(record['diffuser_sn'])} · Susceptor S/N: {display(record['susceptor_sn'])}")
            if kind == 'Spacing':
                labels = [['①','⑥','②'],['⑨','⑤','⑦'],['④','⑧','③']]
                matrix = [[f'{labels[i][j]}: {display(value)}' for j,value in enumerate(line)] for i,line in enumerate(record['grid'])]
                st.dataframe(pd.DataFrame(matrix,index=['G/V 측','중앙','Window 측'],columns=['좌','중앙','우']),use_container_width=True)
            else:
                matrix = [[display(value) for value in row] for row in record['grid']]
                st.dataframe(pd.DataFrame(matrix,index=[f'Row {i+1}' for i in range(5)],columns=[f'Col {i+1}' for i in range(7)]),use_container_width=True)
                st.write('**Center(R3C4): ' + display(record['center']) + '**')
            st.caption(f"원본 위치: {record['source_sheet']}!{record['cells'][0][0]} ~ {record['cells'][-1][-1]} · 행·열 방향을 변환하지 않았습니다.")
    if hw['warnings']:
        with st.expander('원본 측정값 안내'):
            for warning in hw['warnings']:
                st.write(warning)
