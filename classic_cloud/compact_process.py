"""Compact process view; uses existing, verified measurement associations."""
from html import escape
import streamlit as st
from classic_cloud.evaluation_compare import (comparison_navigation, comparison_panel,
    linked_measurement, display_grid, hardware_table, limits, uniformity, COMPARE)
from classic_cloud.visuals import numeric, number
from process_map import KINDS


def compact_panel(unit, data, hw):
    columns=st.columns([1,3,2])
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
        comparison_panel(unit,chamber,runs,run,data,hw,mode);return
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
    u=uniformity(run,unit)
    metrics=run.get('metrics',{}) if unit=='45' else {'Dep Time':run.get('dep_time'),'HCG':run.get('hcg')}
    metrics_html=''.join('<div><small>'+escape(k)+'</small><strong>'+escape(number(v))+'</strong></div>' for k,v in metrics.items() if k!='Unif.' and v is not None and v!='')
    meta=run['date']+' · PC '+run['chamber']+' · '+run['recipe']+' · Diffuser '+(run.get('diffuser_sn') or '—')+' · Susceptor '+(run.get('susceptor_sn') or '—')
    return '''<style>
    .block-container:has(.fit-board){padding-top:1rem;padding-bottom:1rem}
    .fit-board{color:#17324d;font-size:14px}
    .fit-meta{font-size:12px;margin:0 0 8px;overflow-wrap:anywhere}
    .fit-top{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
    .fit-board section{padding:8px 10px;border:1px solid #cbd5e1;border-radius:8px;min-width:0}
    .fit-board h3{font-size:16px!important;margin:0 0 3px;padding:0}
    .fit-board small{font-size:12px;color:#60758b;display:block}
    .fit-hw{margin:5px 0;height:clamp(130px,19vh,185px)}
    .fit-board table{border-collapse:collapse;table-layout:fixed;width:100%;margin:0;height:100%}
    .fit-board td{font-size:15px;font-weight:600;text-align:center;padding:2px!important;border:1px solid #cbd5e1}
    .fit-board .spacing td{background:#fff}.fit-board .spacing tr:nth-child(2) td:nth-child(2){background:#e0f2fe}
    .fit-bottom{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,2fr);gap:10px;margin-top:10px}
    .fit-map{display:grid;grid-template-columns:18px minmax(0,1fr) 18px;gap:5px;align-items:center;margin-top:6px}
    .fit-map>span{writing-mode:vertical-rl;font-size:12px}
    .fit-map-body{height:clamp(170px,24vh,240px)}
    .fit-map-body>div{height:100%!important;font-size:18px!important}
    .fit-empty{height:100%;display:flex;align-items:center;justify-content:center;border:1px solid #cbd5e1}
    .fit-unif{font-size:24px;font-weight:700;margin:6px 0 10px}
    .fit-metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
    .fit-metrics>div{background:#edf2f7;border-radius:5px;padding:4px 8px;overflow-wrap:anywhere}
    .fit-metrics strong{font-size:15px}
    @media(max-width:850px){.fit-top{grid-template-columns:1fr}.fit-bottom{grid-template-columns:1fr}}
    </style><div class="fit-board"><div class="fit-meta">'''+escape(meta)+'</div><div class="fit-top">'+''.join(cards)+'</div><div class="fit-bottom"><section><h3>'+escape('D/R 공정 Map' if unit=='15' else run['recipe']+' 공정 Map')+'</h3><div class="fit-map"><span>G/V</span><div class="fit-map-body">'+map_html(run['grid'])+'</div><span>WIN</span></div></section><section><h3>공정 결과</h3><div class="fit-unif">Unif. '+(f'{u:.2f}%' if u is not None else 'Data 없음')+'</div><div class="fit-metrics">'+metrics_html+'</div></section></div></div>'
