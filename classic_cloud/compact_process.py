"""Compact process view; uses existing, verified measurement associations."""
from html import escape
import streamlit as st
from classic_cloud.evaluation_compare import (comparison_navigation, comparison_panel,
    linked_measurement, display_grid, hardware_table, limits, uniformity, COMPARE)
from classic_cloud.visuals import numeric, number
from process_map import KINDS
from rf_system import rf_system_card


def compact_panel(unit, data, hw):
    columns=st.columns([1,3.1,1.8,0.8])
    with columns[0]:
        chamber=st.selectbox('공정 PC',list('ABCDE'),key='fit_pc_'+unit)
    runs=sorted([r for r in data['records'] if r['chamber']==chamber],key=lambda r:(r['date'],r.get('source_cell','')),reverse=True)
    if not runs:
        st.info('평가 기록이 없습니다.');return
    by_id={r['id']:r for r in runs}
    with columns[1]:
        selected=st.selectbox('공정 평가 기록',list(by_id),format_func=lambda k:by_id[k]['date']+' · '+by_id[k]['recipe']+' · '+by_id[k]['source_cell'],key='fit_run_'+unit+'_'+chamber)
    run=by_id[selected]
    with columns[2]:mode=comparison_navigation(unit,chamber)
    if mode==COMPARE:
        with columns[3]:
            count=st.selectbox('비교 대상 수',[1,2,3,4],format_func=lambda n:str(n)+'개',
                               key=f'compare_{unit}_{chamber}_{run["id"]}_count_select')
        comparison_panel(unit,chamber,runs,run,data,hw,mode,count=count);return
    st.markdown(compact_html(unit,run,data,hw),unsafe_allow_html=True)
    with st.expander('평가 상세 · S/N · 메모'):
        st.write({k:run.get(k,'') for k in ['date','recipe','dep_time','hcg','diffuser_sn','susceptor_sn','notes','source_cell']})


def compact_html(unit,run,data,hw):
    from classic_cloud.process_views import map_html
    cards=[]
    for kind in KINDS:
        measured,reason=linked_measurement(unit,run,data,hw,kind)
        grid=display_grid(unit,kind,measured['grid']) if measured else []
        chart=hardware_table(grid,kind=='Spacing',limits([grid])) if grid else '<div class="fit-empty">연결 확인 필요</div>'
        caption='H/W 측정일 '+measured['date'] if measured else reason
        direction='G/V ↑ · WIN ↓' if kind=='Spacing' else '← G/V · WIN →'
        cards.append('<section><h3>'+kind+'</h3><small>'+escape(caption)+'</small><div class="fit-hw">'+chart+'</div><small>'+direction+'</small></section>')
    rf_card=rf_system_card(run) if unit=='45' else ''
    u=uniformity(run,unit)
    metrics=run.get('metrics',{}) if unit=='45' else {'Dep Time':run.get('dep_time'),'HCG':run.get('hcg')}
    metrics_html=''.join('<div><small>'+escape(k)+'</small><strong>'+escape(number(v))+'</strong></div>' for k,v in metrics.items() if k!='Unif.' and v is not None and v!='')
    meta=run['date']+' · PC '+run['chamber']+' · '+run['recipe']+' · Diffuser '+(run.get('diffuser_sn') or '—')+' · Susceptor '+(run.get('susceptor_sn') or '—')
    return '''<style>
    .block-container:has(.fit-board){padding-top:1rem;padding-bottom:1rem}
    .fit-board{--fit-chart-height:clamp(130px,19vh,185px);color:#17324d;font-size:14px}
    .fit-meta{font-size:12px;margin:0 0 8px;overflow-wrap:anywhere}
    .fit-top{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
    .fit-board section{padding:8px 10px;border:1px solid #cbd5e1;border-radius:8px;min-width:0}
    .fit-board h3{font-size:16px!important;margin:0 0 3px;padding:0}
    .fit-board small{font-size:12px;color:#60758b;display:block}
    .fit-hw{margin:5px 0;height:var(--fit-chart-height)}
    .fit-board table{border-collapse:collapse;table-layout:fixed;width:100%;margin:0;height:100%}
    .fit-board td{font-size:15px;font-weight:600;text-align:center;padding:2px!important;border:1px solid #cbd5e1}
    .fit-board .spacing td{background:#fff}.fit-board .spacing tr:nth-child(2) td:nth-child(2){background:#e0f2fe}
    .fit-bottom{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(0,1fr);gap:10px;margin-top:10px;align-items:start}
    .fit-bottom>section:last-child{grid-column:3}
    .fit-bottom>section.fit-process-map{grid-column:2;box-sizing:border-box}
    .fit-bottom>section.fit-rf-card{grid-column:1}
    .fit-board .fit-rf-table{height:auto;margin-top:10px;font-size:12px}
    .fit-board .fit-rf-table th,.fit-board .fit-rf-table td{padding:8px 3px!important;text-align:center;vertical-align:middle;font-size:12px;font-weight:400;line-height:1.35;overflow-wrap:anywhere;border:1px solid #cbd5e1}
    .fit-board .fit-rf-table th{background:#e8edf3;font-weight:600}
    .fit-board .fit-rf-table td{background:#f8fafc}
    .fit-rf-missing{margin-top:8px}
    .fit-map{position:relative;margin:6px 0 18px}
    .fit-map>span{position:absolute;bottom:-18px;font-size:12px;line-height:16px}
    .fit-map>span:first-child{left:0}.fit-map>span:last-child{right:0}
    .fit-map-body{height:var(--fit-chart-height);min-width:0}
    .fit-board .fit-map-body>table{height:100%;width:100%;margin:0;table-layout:fixed}
    .fit-board .fit-map-body td{padding:0 2px!important;line-height:1.1;font-size:14px;vertical-align:middle;overflow-wrap:anywhere}
    .fit-map-body>div{height:100%!important;font-size:18px!important}
    .fit-empty{height:100%;display:flex;align-items:center;justify-content:center;border:1px solid #cbd5e1}
    .fit-unif{font-size:24px;font-weight:700;margin:6px 0 10px}
    .fit-metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
    .fit-metrics>div{background:#edf2f7;border-radius:5px;padding:4px 8px;overflow-wrap:anywhere}
    .fit-metrics strong{font-size:15px}
    @media(max-width:850px){.fit-top{grid-template-columns:1fr}.fit-bottom{grid-template-columns:1fr}.fit-bottom>section.fit-rf-card,.fit-bottom>section.fit-process-map,.fit-bottom>section:last-child{grid-column:auto}}
    </style><div class="fit-board"><div class="fit-meta">'''+escape(meta)+'</div><div class="fit-top">'+''.join(cards)+'</div><div class="fit-bottom">'+rf_card+'<section class="fit-process-map"><h3>'+escape('D/R 공정 Map' if unit=='15' else run['recipe']+' 공정 Map')+'</h3><div class="fit-map"><span>G/V</span><div class="fit-map-body">'+map_html(run['grid'])+'</div><span>WIN</span></div></section><section><h3>공정 결과</h3><div class="fit-unif">Unif. '+(f'{u:.2f}%' if u is not None else 'Data 없음')+'</div><div class="fit-metrics">'+metrics_html+'</div></section></div></div>'
