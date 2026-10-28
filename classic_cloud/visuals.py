from html import escape
from datetime import date
import math
import pandas as pd
import streamlit as st

STYLE = '''<style>
[data-testid="stAppViewContainer"],.stApp{background:#e2e8f0;color:#172b4d}
[data-testid="stSidebar"]{background:#cbd5e1;border-right:1px solid #b6c4d5}
.block-container{max-width:1500px;padding-top:2rem}
h1{font-size:30px!important;letter-spacing:-.7px}
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button{background:#f1f5f9;color:#173c72;border:1px solid #94a3b8;border-radius:6px;min-height:38px}
[data-testid="stButton"] button[kind="primary"]{background:#bfdbfe!important;border:2px solid #2563eb!important;color:#123d80!important}
[data-testid="stMetric"]{background:#f1f5f9;border:1px solid #94a3b8;border-radius:8px;padding:12px;text-align:center}
[class*="st-key-classic_kpi"] button{height:76px;width:100%}
[class*="st-key-classic_kpi"] button p{font-size:26px;font-weight:700}
.classic-table-wrap{overflow:auto;border:1px solid #94a3b8;border-radius:7px;margin:10px 0}
.classic-table{width:100%;border-collapse:collapse;background:#f1f5f9;color:#172b4d;table-layout:fixed;font-size:13px}
.classic-table th{background:#cbd5e1;text-align:center;font-weight:600}
.classic-table td,.classic-table th{border:1px solid #94a3b8;padding:9px 8px;white-space:pre-wrap;overflow-wrap:anywhere;vertical-align:middle}
.classic-table tr:nth-child(even) td{background:#e8eef5}
.classic-parts{min-width:680px;font-size:11px}.classic-parts th:first-child{width:12%}.classic-parts td{vertical-align:top}
.part-sn{background:#dbe5f0;border:1px solid #b6c4d5;padding:5px;border-radius:3px;margin-bottom:5px}
.part-age{padding:4px;border-radius:3px;margin-top:4px}
.classic-detail th{width:18%}.classic-detail td{text-align:left}
.classic-measure th,.classic-measure td{text-align:center;padding:6px 3px}.classic-measure small{display:block;font-size:9px;color:#64748b}.classic-measure strong{display:block;background:#e2e8f0;padding:9px 0;border-radius:3px;margin:3px}
.classic-badges{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}.classic-badges span{border:1px solid #94a3b8;border-radius:4px;background:#dbeafe;padding:4px 8px;font-size:12px}
.classic-work{background:#f1f5f9;border:1px solid #94a3b8;border-radius:8px;padding:14px;margin-bottom:14px}.classic-work p{white-space:pre-wrap;overflow-wrap:anywhere;margin:10px 0;font-size:13px}.classic-work .reason{border-top:1px solid #b6c4d5;padding-top:10px}.classic-work .footer{border-top:1px solid #cbd5e1;padding:9px 0 4px;color:#64748b;font-size:12px}
</style>'''


def numeric(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def number(v):return '—' if v is None or v=='' else f'{v:g}' if numeric(v) else str(v)


def cards(label, options, key, horizontal=False):
    st.caption(label)
    if st.session_state.get(key) not in options:st.session_state[key]=options[0]
    selected=st.session_state[key]
    columns=st.columns(len(options)) if horizontal else [st]*len(options)
    for column,option in zip(columns,options):
        if column.button(option,key=key+'_'+option,type='primary' if selected==option else 'secondary',use_container_width=True):
            st.session_state[key]=option
            st.rerun()
    return selected


def detail(items):
    rows=''.join('<tr><th>'+escape(str(k))+'</th><td>'+escape(str('—' if v is None or v=='' else v))+'</td></tr>' for k,v in items)
    st.markdown('<div class="classic-table-wrap"><table class="classic-table classic-detail">'+rows+'</table></div>',unsafe_allow_html=True)


def installed_html(hw, chambers, today):
    rows=[]
    excluded={'RFG','Matcher','RPSC Reactor','Generator'}
    for part in hw.get('parts',[]):
        cells=['<th>'+escape(part)+'</th>']
        for chamber in chambers:
            item=hw.get('installed',{}).get(chamber,{}).get(part)
            if not item:cells.append('<td>—</td>');continue
            try:days=(today-date.fromisoformat(item['date'])).days
            except (ValueError,KeyError):days=None
            age='색상 제외' if part in excluded else '—' if days is None else f'{days}일 경과' if days>=0 else '예정일'
            color='#e2e8f0' if part in excluded or days is None else '#fee2e2' if days>=365 else '#fef3c7' if days>=180 else '#dcfce7'
            cells.append('<td><div class="part-sn">S/N: <b>'+escape(item['sn'])+'</b></div><div>최근 기록일: '+escape(item['date'] or '미기재')+'</div><div class="part-age" style="background:'+color+'">'+escape(age)+'</div></td>')
        rows.append('<tr>'+''.join(cells)+'</tr>')
    return '<div class="classic-table-wrap"><table class="classic-table classic-parts"><thead><tr><th>부품</th>'+''.join('<th>Chamber '+c+'</th>' for c in chambers)+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


def measurement_table(grid, spacing=False):
    labels=[[1,6,2],[9,5,7],[4,8,3]]
    cols=len(grid[0]);rows=[]
    for i,line in enumerate(grid):
        cells=['<th>'+('G/V 측' if i==0 else 'Window 측' if i==2 else '중앙' if spacing else f'Row {i+1}')+'</th>'] if spacing else ['<th>Row '+str(i+1)+'</th>']
        for j,v in enumerate(line):
            label='P'+str(labels[i][j]) if spacing else f'R{i+1}C{j+1}'
            cells.append('<td><small>'+label+'</small><strong>'+escape(number(v))+'</strong></td>')
        rows.append('<tr>'+''.join(cells)+'</tr>')
    return '<div class="classic-table-wrap"><table class="classic-table classic-measure"><thead><tr><th>구분</th>'+''.join('<th>Col '+str(c+1)+'</th>' for c in range(cols))+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


def diagram_svg(grid, spacing=False, limits=None):
    values=[v for row in grid for v in row if numeric(v)]
    low,high=limits or ((min(values),max(values)) if values else (0,0))
    nr,nc=len(grid),len(grid[0]);width=560/nc;height=310/nr
    out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 440" role="img" aria-label="측정 위치도">','<rect x="40" y="40" width="600" height="360" rx="20" fill="#d9e2ef" stroke="#64748b" stroke-width="3"/>']
    if spacing:out+=['<text x="340" y="25" text-anchor="middle" fill="#075985">G/V 측</text>','<text x="340" y="425" text-anchor="middle" fill="#92400e">Window 측</text>']
    else:out+=['<text x="20" y="220" transform="rotate(-90 20 220)" text-anchor="middle" fill="#075985">G/V · Col 1</text>','<text x="663" y="220" transform="rotate(90 663 220)" text-anchor="middle" fill="#92400e">Window · Col 7</text>']
    points=[[1,6,2],[9,5,7],[4,8,3]]
    for i,row in enumerate(grid):
        for j,v in enumerate(row):
            ratio=0.5 if high==low else (v-low)/(high-low) if numeric(v) else 0
            ratio=min(1,max(0,ratio))
            color='#e2e8f0' if not numeric(v) else '#'+''.join(f'{round(a+(b-a)*ratio):02x}' for a,b in zip((37,99,235),(239,68,68)))
            x,y=60+j*width,65+i*height
            label=f'P{points[i][j]}' if spacing else f'R{i+1}C{j+1}'
            ink='#475569' if not numeric(v) else '#ffffff'
            out.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{color}" stroke="#cbd5e1"/><text x="{x+4}" y="{y+13}" font-size="10" fill="{ink}">{label}</text><text x="{x+width/2}" y="{y+height/2+7}" text-anchor="middle" font-size="19" font-weight="700" fill="{ink}">{escape(number(v))}</text>')
    return ''.join(out)+'</svg>'
