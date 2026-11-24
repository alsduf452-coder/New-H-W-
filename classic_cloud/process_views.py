from html import escape
import pandas as pd
import streamlit as st
from classic_cloud.evaluation_compare import comparison_navigation, comparison_panel
from process_map import link_measurement,KINDS
from classic_cloud.visuals import diagram_svg,detail,excel_color


def map_html(grid, limits=None):
    values=[v for row in grid for v in row if v is not None]
    if not values:return '<div style="height:300px;border:1px solid #cbd5e1;background:#f1f5f9;display:flex;align-items:center;justify-content:center;font-size:24px">Data 없음</div>'
    low,high=limits or (min(values),max(values));rows=[]
    for row in grid:
        cells=[]
        for v in row:
            ratio=(v-low)/(high-low) if v is not None and high!=low else .5
            color=excel_color(v,low,high)
            cells.append(f'<td style="background:{color};text-align:center;padding:20px;border:1px solid #cbd5e1">{v:g}</td>' if v is not None else '<td style="text-align:center;background:#e2e8f0">Data 없음</td>')
        rows.append('<tr>'+''.join(cells)+'</tr>')
    return '<table style="width:100%;table-layout:fixed;color:#17324d">'+''.join(rows)+'</table>'


def process_panel(process_snapshot,hw_snapshot):
    st.header('6G · 15호기 H/W 형상 · 공정 Map 비교')
    data=process_snapshot.get('previews',{}).get('__process_data__')
    if not data:st.info('15호기 공정 Map 파일 수신을 기다리고 있습니다.');return
    from classic_cloud.compact_process import compact_panel
    compact_panel('15',data,hw_snapshot)


def process_comparison_html(run):
    items=[('평가일',run['date']),('PC',run['chamber']),('Recipe',run['recipe']),('Dep Time',run['dep_time']),('Diffuser S/N',run['diffuser_sn']),('Susceptor S/N',run['susceptor_sn']),('HCG',run['hcg']),('평가 메모',run['notes'])]
    rows=''.join('<tr><th>'+escape(str(k))+'</th><td>'+escape(str('—' if v is None or v=='' else v))+'</td></tr>' for k,v in items)
    unif=f"{run['unif']:.2f}%" if run['unif'] is not None else 'Data 없음'
    return ('<style>'
        '.process-comparison{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,2fr);gap:12px 16px;align-items:stretch}'
        '.process-comparison h3{margin:0;padding:0}'
        '.process-map-body{min-height:300px;display:flex;min-width:0}'
        '.process-map-body>div,.process-map-body>table{height:100%!important;min-height:300px;width:100%;margin:0;box-sizing:border-box}'
        '.process-map-body>table{border-collapse:collapse}'
        '.process-condition-body{margin:0;min-width:0;border:1px solid #cfdae5;border-radius:12px;overflow:hidden}'
        '.process-condition-body table{height:100%;margin:0}'
        '.process-condition-body th{width:24%}'
        '.process-unif{text-align:right;font-weight:600}'
        '@media(max-width:640px){.process-comparison{grid-template-columns:minmax(0,1fr)}'
        '.process-map-title{grid-row:1}.process-map-body{grid-row:2}.process-unif{grid-row:3}'
        '.process-condition-title{grid-row:4}.process-condition-body{grid-row:5}}'
        '</style><div class="process-comparison">'
        '<h3 class="process-map-title">D/R 공정 Map</h3>'
        '<h3 class="process-condition-title">평가 조건 및 변경 메모</h3>'
        '<div class="process-map-body">'+map_html(run['grid'])+'</div>'
        '<div class="process-condition-body"><table class="classic-table classic-detail">'+rows+'</table></div>'
        '<div class="process-unif">Unif. '+unif+'</div></div>')
