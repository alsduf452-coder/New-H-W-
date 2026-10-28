from html import escape
from datetime import date
import math
import pandas as pd
import streamlit as st

STYLE = '''<style>
[data-testid="stAppViewContainer"],.stApp{background:#f3f6fa;color:#24364b}
[data-testid="stHeader"]{background:rgba(243,246,250,.96)}
[data-testid="stSidebar"]{background:#4b6279;border-right:1px solid #40576e}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] label{color:#f0f5fb!important}
[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#fff!important}
[data-testid="stSidebar"] [data-testid="stButton"] button{background:#536d85;color:#f5f8fc;border-color:#71869b;box-shadow:none}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover{background:#617e98;border-color:#a4bfd7}
[data-testid="stSidebar"] [data-testid="stButton"] button p{color:inherit!important}
.block-container{max-width:1500px;padding-top:2.2rem;padding-bottom:3rem}
h1{font-size:30px!important;letter-spacing:-.7px;color:#24364b}
h2{font-size:25px!important;letter-spacing:-.5px}h3{font-size:20px!important}
[data-testid="stCaptionContainer"]{color:#60758b}
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button{background:#fff;color:#365f88;border:1px solid #cfdae5;border-radius:9px;min-height:40px;transition:background .15s,border-color .15s}
[data-testid="stButton"] button:hover,[data-testid="stDownloadButton"] button:hover{background:#edf4fc;border-color:#739ac2}
[data-testid="stButton"] button[kind="primary"]{background:#3979bb!important;border:1px solid #3979bb!important;color:#fff!important;box-shadow:0 3px 8px #294a6d18}
button:focus-visible{outline:3px solid #81b4e5!important;outline-offset:2px}
[data-testid="stMetric"]{background:#fff;border:1px solid #dce5ee;border-radius:12px;padding:16px;text-align:center}
[class*="st-key-classic_kpi"] button{height:84px;width:100%;background:#fff;border:1px solid #dce5ee;box-shadow:0 3px 12px #294a6d08;border-radius:12px}
[class*="st-key-classic_kpi"] button p{font-size:28px;font-weight:700;color:#315d88}
[data-testid="stDataFrame"],[data-testid="stPlotlyChart"]{border:1px solid #dce5ee;border-radius:12px;overflow:hidden;background:#fff}
[data-testid="stPlotlyChart"]{padding:6px}
[data-testid="stExpander"]{background:#fff;border-radius:10px}
.classic-table-wrap{overflow:auto;border:1px solid #cfdae5;border-radius:12px;margin:10px 0}
.classic-table{width:100%;border-collapse:collapse;background:#ffffff;color:#24364b;table-layout:fixed;font-size:13px}
.classic-table th{background:#e7eef6;text-align:center;font-weight:600}
.classic-table td,.classic-table th{border:1px solid #d5e0eb;padding:10px 9px;white-space:pre-wrap;overflow-wrap:anywhere;vertical-align:middle}
.classic-table tr:nth-child(even) td{background:#f5f8fc}
.classic-parts{min-width:680px;font-size:11px}.classic-parts th:first-child{width:12%}.classic-parts td{vertical-align:top}
.part-sn{background:#dbe5f0;border:1px solid #b6c4d5;padding:5px;border-radius:3px;margin-bottom:5px}
.part-age{padding:4px;border-radius:3px;margin-top:4px}
.classic-detail th{width:18%}.classic-detail td{text-align:left}
.classic-measure th,.classic-measure td{text-align:center;padding:6px 3px}.classic-measure small{display:block;font-size:9px;color:#64748b}.classic-measure strong{display:block;background:#e2e8f0;padding:9px 0;border-radius:3px;margin:3px}
.classic-badges{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}.classic-badges span{border:1px solid #94a3b8;border-radius:4px;background:#dbeafe;padding:4px 8px;font-size:12px}
.classic-work{background:#fff;border:1px solid #d5e0eb;border-radius:12px;padding:18px;margin-bottom:14px}.classic-work p{white-space:pre-wrap;overflow-wrap:anywhere;margin:10px 0;font-size:13px}.classic-work .reason{border-top:1px solid #b6c4d5;padding-top:10px}.classic-work .footer{border-top:1px solid #cbd5e1;padding:9px 0 4px;color:#64748b;font-size:12px}
.spacing-values {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border:1px solid #94a3b8;border-radius:9px;overflow:hidden;background:#f1f5f9}
.spacing-cell {min-height:135px;padding:12px;border:1px solid #cbd5e1;display:flex;flex-direction:column;gap:7px;color:#172b4d}
.spacing-cell strong {font-size:27px;line-height:1.25;overflow-wrap:anywhere}.spacing-cell small {font-size:12px}.spacing-cell span {font-size:11px;color:#475569}
.spacing-center {background:#e0f2fe;border:2px solid #0891b2}.measurement-svg {width:100%;height:auto;display:block;background:#f1f5f9;border:1px solid #94a3b8;border-radius:10px}
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
    if spacing:return spacing_diagram_svg(grid)
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

SPACING_LAYOUT=[[1,6,2],[9,5,7],[4,8,3]]
SPACING_LABELS={1:'G/V 좌',6:'G/V 중앙',2:'G/V 우',9:'중앙 좌',5:'Center 기준',7:'중앙 우',4:'Window 좌',8:'Window 중앙',3:'Window 우'}

def measurement_number(value):
    return "미측정" if value is None or value=="" else number(value)

def spacing_values(grid):
    values=[None]*9
    for row,points in zip(grid,SPACING_LAYOUT):
        for value,point in zip(row,points):values[point-1]=value
    return values

def spacing_table_html(grid):
    values=spacing_values(grid)
    from html import escape
    cells=[]
    for row in SPACING_LAYOUT:
        for point in row:
            v=values[point-1];delta=None if not numeric(v) else round(v-885,3)
            color='#64748b' if not numeric(v) else '#1d4ed8' if delta<0 else '#b91c1c' if delta>0 else '#047857'
            cells.append(f'<div class="spacing-cell {"spacing-center" if point==5 else ""}"><small>P{point} · {SPACING_LABELS[point]}</small><strong>{escape(measurement_number(v))}</strong><span>mils</span><small style="color:{color}">885 대비 {"—" if delta is None else f"{delta:+g}"}</small></div>')
    return '<div class="spacing-values">'+''.join(cells)+'</div>'


def spacing_diagram_svg(grid,table_mode=False):
    values=spacing_values(grid)
    from html import escape
    svg=['<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Spacing 9포인트 위치도" viewBox="0 0 700 510" class="measurement-svg">',
         '<rect x="35" y="40" width="630" height="420" rx="24" fill="#e5ecf5" stroke="#64748b" stroke-width="3"/>',
         '<rect x="62" y="67" width="576" height="366" rx="14" fill="#f1f5f9" stroke="#94a3b8" stroke-width="2"/>',
         '<path d="M350 68V432M64 250H636" stroke="#94a3b8" stroke-dasharray="4 5"/>',
         '<text x="350" y="24" text-anchor="middle" fill="#075985" font-size="18" font-weight="700">▲ GATE VALVE · G/V 측</text>',
         '<text x="350" y="490" text-anchor="middle" fill="#92400e" font-size="18" font-weight="700">▼ WINDOW 측</text>']
    if table_mode:
        svg=svg[:1]+['<rect x="62" y="67" width="576" height="366" rx="12" fill="#f1f5f9" stroke="#94a3b8"/>','<text x="350" y="24" text-anchor="middle" fill="#075985" font-size="18" font-weight="700">▲ GATE VALVE · G/V 측</text>','<text x="350" y="490" text-anchor="middle" fill="#92400e" font-size="18" font-weight="700">▼ WINDOW 측</text>']
    for y,row in enumerate(SPACING_LAYOUT):
        for x,point in enumerate(row):
            left=82+x*185;top=90+y*112;v=values[point-1]
            stroke='#0891b2' if point==5 else '#94a3b8'
            svg.append(f'<rect x="{left}" y="{top}" width="166" height="86" rx="9" fill="{"#e0f2fe" if point==5 else "#ffffff"}" stroke="{stroke}" stroke-width="{3 if point==5 else 1.5}"/>')
            svg.append(f'<text x="{left+83}" y="{top+21}" text-anchor="middle" font-size="13" fill="#334155">P{point} · {SPACING_LABELS[point]}</text>')
            svg.append(f'<text x="{left+83}" y="{top+49}" text-anchor="middle" font-size="25" font-weight="700" fill="#172b4d">{escape(measurement_number(v))}</text>')
            delta='—' if not numeric(v) else f'{v-885:+.1f} mils'
            color='#64748b' if not numeric(v) else '#1d4ed8' if v<885 else '#b91c1c' if v>885 else '#047857'
            svg.append(f'<text x="{left+83}" y="{top+71}" text-anchor="middle" font-size="13" fill="{color}">{delta}</text>')
    return ''.join(svg)+'</svg>'


