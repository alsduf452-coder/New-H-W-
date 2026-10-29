from collections import Counter
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from classic_cloud import model
from classic_cloud.visuals import detail, installed_html, measurement_table, diagram_svg, number, numeric, spacing_table_html


def downloads(frame,name,extra=None):
    st.download_button('조회 결과 Excel 다운로드',model.workbook_export({name:frame,**(extra or {})}),name+'.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key='classic_download_'+name)


def pending(snapshot, filters):
    st.header('PENDING 현황')
    if not snapshot.get('revision'):
        st.info('PENDING 파일 수신을 기다리고 있습니다. 기존 동기화 프로그램에서 PENDING 전송 결과를 확인해주세요.');return
    frame=model.pending_frame(snapshot)
    base=model.filter_pending(frame,**filters)
    done=int((base['상태']=='완료').sum());total=len(base)
    values=[('전체 건수',str(total),None),('완료',str(done),'완료'),('미완료',str(total-done),'미완료'),('완료율',f'{done/total*100:.1f}%' if total else '0.0%',None)]
    for col,(label,value,state) in zip(st.columns(4),values):
        with col:
            st.caption(label)
            if st.button(value,key='classic_kpi_'+label,use_container_width=True):st.session_state.classic_drill=state
    st.caption('현재 필터 기준 · 완료/미완료 카드를 누르면 해당 목록을 조회합니다.')
    left,right=st.columns(2)
    for panel,group in [(left,'분야'),(right,'설비')]:
        grouped=model.summary(base,group)
        panel.subheader(group+'별 현황')
        if not grouped.empty:
            fig=px.bar(grouped,x=group,y=['완료','미완료'],color_discrete_map={'완료':'#2563eb','미완료':'#ef4444'},barmode='stack')
            fig.update_layout(height=280,margin=dict(l=15,r=15,t=20,b=20),legend_title_text='상태',yaxis_title='건수')
            panel.plotly_chart(fig,use_container_width=True,key='classic_chart_'+group)
            panel.dataframe(grouped,hide_index=True,use_container_width=True)
    counts,unresolved=model.deadlines(base,datetime.now(ZoneInfo('Asia/Seoul')).date())
    with st.columns(2)[0]:
        st.subheader('미완료 목표일 현황')
        fig=go.Figure(go.Bar(x=list(counts),y=list(counts.values()),marker_color=['#dc2626','#f59e0b','#2563eb'],text=list(counts.values()),textposition='auto'))
        fig.update_layout(height=280,margin=dict(l=20,r=15,t=20,b=25),yaxis=dict(dtick=1,title='건수'))
        st.plotly_chart(fig,use_container_width=True,key='classic_deadlines')
        st.caption(f'한국 날짜 기준 · 기한초과: 어제까지 / 임박: 오늘~7일 후 / 여유: 8일 이후 · 목표일 미기재/확인 필요 {unresolved}건')
    selected=st.session_state.get('classic_drill')
    shown=base[base['상태']==selected] if selected else base
    st.subheader('Pending List'+(' · '+selected if selected else ''))
    if selected and st.button('카드 선택 해제',key='classic_clear_drill'):
        st.session_state.classic_drill=None;st.rerun(scope='app')
    columns=['ID','설비','분야','상태','Unit','내용','담당자','목표일','시트']
    st.dataframe(shown[columns],hide_index=True,use_container_width=True,height=380)
    if not shown.empty:
        identifier=st.selectbox('상세 항목 선택',shown['ID'].tolist(),format_func=lambda key:next(f"{r['설비']} · {r['분야']} · {r['내용'][:65]}" for r in shown.to_dict('records') if r['ID']==key),key='classic_pending_detail')
        row=shown[shown['ID']==identifier].iloc[0]
        detail([(field,row[field]) for field in ['설비','분야','상태','Unit','내용','발생일','담당자','원인','진행 사항','목표일','조치내용','완료일','조치자','45호기 적용 여부']])
    downloads(shown,'Pending List',{'분야별 집계':model.summary(shown,'분야'),'설비별 집계':model.summary(shown,'설비')})
    warnings=snapshot.get('previews',{}).get('__pending_data__',{}).get('warnings',[])
    if warnings:
        with st.expander(f'목표일 확인 필요 · {len(warnings)}건'):
            st.dataframe(warnings,hide_index=True,use_container_width=True)
    if filters['scope']!='주요 5개 분야':st.caption('보조 시트는 주요 분야와 중복될 수 있습니다. 일부 원본 시트가 잘린 경우 수신된 미리보기 범위만 조회됩니다.')


def revisions(snapshot):
    st.header('PENDING List REV관리')
    rev=model.revision(snapshot)
    if not rev['history'] and not rev['summary']:
        st.info('수신한 PENDING 파일에 REV 관리 정보가 없습니다.');return
    st.subheader(rev['title'] or 'REV 변경 이력')
    st.caption(f"라인: {rev['line'] or '—'} · 공정: {rev['process'] or '—'}")
    st.subheader('분야별 요약 · Excel 저장값')
    if rev['summary']:st.dataframe(pd.DataFrame(rev['summary']).set_index('구분').T,use_container_width=True)
    st.caption('Excel에 저장된 요약값입니다. PENDING 현황은 항목별로 다시 집계하므로 저장된 수식 결과와 다를 수 있습니다. 앱이 Excel 수식을 재계산하지 않습니다.')
    records=pd.DataFrame(rev['history'])
    if records.empty:return
    last=records.iloc[-1];st.success(f"목록 마지막 REV: {last['REV']} · 변경일: {last['변경일자']} · 이력 {len(records)}건")
    query=st.text_input('REV 이력 검색',key='classic_rev_query')
    for term in query.split():
        if records.empty:break
        records=records[records.astype(str).agg(' '.join,axis=1).str.contains(term,case=False,regex=False)]
    st.dataframe(records,hide_index=True,use_container_width=True,height=380)
    if not records.empty:
        index=st.selectbox('REV 상세 선택',records.index.tolist(),format_func=lambda i:f"REV {records.loc[i,'REV']} · {records.loc[i,'변경일자']}",key='classic_rev_selection')
        detail(list(records.loc[index].items()))
    downloads(records,'REV 이력')


def work_history(hw,chamber,query=''):
    chronological=sorted(hw.get('history',[]),key=lambda r:(r['date'],r['source_row']))
    state={};events=[]
    for record in chronological:
        changes=[]
        for part,sn in record['parts'].items():
            before=state.get((record['chamber'],part),'미기재')
            changes.append((part,before,sn))
            state[(record['chamber'],part)]=sn
        events.append({**record,'changes':changes})
    for record in reversed(events):
        if chamber!='전체' and record['chamber']!=chamber:continue
        if query and query.casefold() not in str(record).casefold():continue
        body='<div class="classic-work"><div class="classic-badges"><span>'+escape(record['date'] or '일자 미기재')+'</span><span>Chamber '+escape(record['chamber'])+'</span><span>Excel 기록</span></div>'
        body+='<table class="classic-change-table" aria-label="부품 교체 전후"><thead><tr><th>부품</th><th>교체 전</th><th>교체 후</th></tr></thead><tbody>'
        for part,before,after in record['changes']:
            body+='<tr>'+''.join('<td>'+escape(str(value))+'</td>' for value in (part,before,after))+'</tr>'
        body+='</tbody></table><p class="reason">사유: '+escape(record['reason'] or '—')+'</p><div class="footer">작업자: 원본에 기재 없음</div></div>'
        st.markdown(body,unsafe_allow_html=True)
    if not events:st.info('작업 이력이 없습니다.')


def measurement(hw,chamber,kind):
    rows=[r for r in hw.get('measurements',[]) if r['kind']==kind and (chamber=='전체' or r['chamber']==chamber)]
    spacing=kind=='Spacing'
    if not rows:st.info('측정 기록이 없습니다.');return
    if chamber=='전체':
        st.subheader('챔버별 최신 측정 요약')
        latest=[]
        for ch in 'ABCDE':
            matches=[r for r in rows if r['chamber']==ch]
            if not matches:continue
            r=max(matches,key=lambda v:(v['date'],v['source_row']))
            latest.append({'챔버':'Chamber '+ch,'최신 측정일':r['date'],'Center (⑤)' if spacing else 'Center (R3C4)':number(r['center']),'최소값':number(r['min']),'최대값':number(r['max']),'Max−Min':number(r['range']),'측정 개수':f"{r['count']}/{r['total']}"})
        st.dataframe(latest,hide_index=True,use_container_width=True)
        st.caption('같은 날짜의 여러 기록은 아래쪽 Excel 블록을 최신으로 선택합니다. 빈칸은 미측정이며 0은 실측값입니다.')
        years=sorted({r['date'][:4] for r in rows},reverse=True)
        year=st.selectbox('측정 집계 연도',years,key='classic_year_'+kind)
        counts=Counter(r['date'][5:7] for r in rows if r['date'].startswith(year))
        st.subheader('월별 측정 횟수')
        fig=go.Figure(go.Bar(x=[f'{i:02d}월' for i in range(1,13)],y=[counts[f'{i:02d}'] for i in range(1,13)],marker_color='#2563eb'))
        fig.update_layout(height=280,margin=dict(l=20,r=20,t=20,b=20),yaxis=dict(dtick=1,title='건수'))
        st.plotly_chart(fig,use_container_width=True,key='classic_monthly_'+kind)
        measurement_download(rows,kind)
        return
    rows=sorted(rows,key=lambda r:(r['date'],r['source_row']),reverse=True)
    by_id={r['id']:r for r in rows}
    selected=st.selectbox('측정 기록',[r['id'] for r in rows],format_func=lambda identifier:f"{by_id[identifier]['date']} · {by_id[identifier]['reason']} · {identifier}",key='classic_measure_'+kind)
    record=by_id[selected]
    st.caption(f"Diffuser S/N: {record.get('diffuser_sn') or '—'} · Susceptor S/N: {record.get('susceptor_sn') or '—'}")
    mode=st.segmented_control('측정 보기',['단일 상세','측정 전후 비교'],default='단일 상세',key='classic_compare_mode_'+kind)
    if mode=='측정 전후 비교':
        others=[r for r in rows if r['id']!=selected]
        if not others:st.info('비교할 다른 측정 기록이 없습니다.');return
        compare=st.selectbox('비교 대상',[r['id'] for r in others],format_func=lambda identifier:f"{by_id[identifier]['date']} · {by_id[identifier]['reason']} · {identifier}",key='classic_compare_record_'+kind)
        other=by_id[compare]
        values=[v for r in [record,other] for line in r['grid'] for v in line if numeric(v)]
        limits=(min(values),max(values)) if values else (0,0)
        for panel,item in zip(st.columns(2),[other,record]):
            panel.subheader(item['date']);panel.caption(item['reason'])
            panel.markdown(diagram_svg(item['grid'],spacing,limits),unsafe_allow_html=True)
        delta=[[b-a if numeric(a) and numeric(b) else None for a,b in zip(left,right)] for left,right in zip(other['grid'],record['grid'])]
        st.caption('차이 = 선택 기록 − 비교 대상' + ('' if spacing else ' · 두 위치도는 같은 색상 범위를 사용합니다.'))
        st.markdown(measurement_table(delta,spacing),unsafe_allow_html=True)
    else:
        left,right=st.columns(2)
        left.subheader(kind+' 실측 데이터');right.subheader(kind+' 측정 위치도')
        if spacing:
            for panel in (left,right):panel.caption('▲ G/V 측: ①⑥② / 중앙: ⑨⑤⑦ / ▼ Window 측: ④⑧③')
        left.markdown(spacing_table_html(record['grid']) if spacing else measurement_table(record['grid']),unsafe_allow_html=True)
        right.markdown(diagram_svg(record['grid'],spacing),unsafe_allow_html=True)
        st.dataframe([{'최소값':number(record['min']),'최대값':number(record['max']),'Max−Min':number(record['range']),'Center (⑤)' if spacing else 'Center (R3C4)':number(record['center']),'측정 개수':f"{record['count']}/{record['total']}"}],hide_index=True,use_container_width=True)
        st.caption('원본 Excel의 행·열과 부호를 그대로 표시합니다. 수정은 Excel에서 저장하세요. 비수치 값은 통계에서 제외합니다.')
    history=pd.DataFrame([{'측정일':r['date'],'사유':r['reason'],'Diffuser S/N':r['diffuser_sn'],'Susceptor S/N':r['susceptor_sn'],'Center':number(r['center']),'Max−Min':number(r['range'])} for r in rows])
    with st.expander('측정 이력'):st.dataframe(history,hide_index=True,use_container_width=True)
    measurement_download(rows,kind)


def measurement_download(records,kind):
    out=[]
    for r in records:
        row={'챔버':r['chamber'],'측정일':r['date'],'구분':r['kind'],'사유':r['reason'],'Diffuser S/N':r.get('diffuser_sn'),'Susceptor S/N':r.get('susceptor_sn')}
        row.update({f'R{i}C{j}':v for i,line in enumerate(r['grid'],1) for j,v in enumerate(line,1)})
        out.append(row)
    downloads(pd.DataFrame(out),kind)


def hardware(snapshot,chamber,section,flatness,query,equipment_name):
    st.header('설비 H/W 이력관리')
    st.caption(equipment_name)
    hw=snapshot.get('previews',{}).get('__hw_data__')
    if not hw:st.info('H/W 파일 수신을 기다리고 있습니다.');return
    if hw.get('warnings'):
        with st.expander('원본 데이터 확인 사항'):
            for warning in hw['warnings']:st.write(warning)
    chambers=list('ABCDE') if chamber=='전체' else [chamber]
    if section=='설비 현황':
        st.subheader('챔버별 장착 부품 통합 현황')
        st.markdown(installed_html(hw,chambers,datetime.now(ZoneInfo('Asia/Seoul')).date()),unsafe_allow_html=True)
        st.caption('부품별 최신 기록 기준 · 180일 이상 주황, 365일 이상 빨강 · RFG/Matcher/Reactor/Generator는 색상 제외. 교체일 이외의 작업자·점검 정보는 원본에 있는 범위만 표시합니다.')
        rows=[{'부품':part,**{'Chamber '+ch:hw['installed'].get(ch,{}).get(part,{}).get('sn','') for ch in chambers}} for part in hw['parts']]
        downloads(pd.DataFrame(rows),'장착 부품 통합')
    elif section=='작업 이력':
        work_history(hw,chamber,query)
    elif section=='부품 추적':
        st.subheader('S/N 이력 추적')
        serial=st.text_input('추적할 S/N',key='classic_sn_search')
        if serial:
            rows=[{'일자':r['date'],'챔버':r['chamber'],'부품':p,'S/N':sn,'변경이력':r['reason']} for r in hw['history'] for p,sn in r['parts'].items() if serial.casefold() in sn.casefold() and r['chamber'] in chambers]
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
        st.caption('Excel에 기록된 장착/변경 위치를 조회합니다. 기록되지 않은 이동·분리 작업은 추정하지 않습니다.')
    elif section in ('Spacing','Flatness'):
        measurement(hw,chamber,'Spacing' if section=='Spacing' else flatness+' Flatness')
    else:
        st.subheader('동기화된 데이터 다운로드')
        rows=[{'일자':r['date'],'챔버':r['chamber'],'변경이력':r['reason'],**r['parts']} for r in hw['history']]
        tables={'작업 교체 이력':pd.DataFrame(rows)}
        tables['장착 부품']=pd.DataFrame([{'부품':p,**{ch:hw['installed'].get(ch,{}).get(p,{}).get('sn','') for ch in 'ABCDE'}} for p in hw['parts']])
        for kind in ('Spacing','Diffuser Flatness','Susceptor Flatness'):
            records=[]
            for r in hw['measurements']:
                if r['kind']!=kind:continue
                records.append({'챔버':r['chamber'],'측정일':r['date'],'사유':r['reason'],'Diffuser S/N':r.get('diffuser_sn'),'Susceptor S/N':r.get('susceptor_sn'),**{f'R{i}C{j}':v for i,line in enumerate(r['grid'],1) for j,v in enumerate(line,1)}})
            tables[kind]=pd.DataFrame(records)
        st.download_button('H/W 전체 Excel 다운로드',model.workbook_export(tables),'HW_History.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.caption('읽기 전용 앱입니다. 데이터 변경·백업 파일 복원·삭제는 제공하지 않습니다. Excel 원본과 서버 백업에서 관리해주세요.')
