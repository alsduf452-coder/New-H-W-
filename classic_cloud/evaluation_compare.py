"""Date comparison using the same measurement links as the individual view."""
from html import escape
import streamlit as st
from classic_cloud.visuals import numeric, excel_color
from process_map import KINDS, link_measurement


INDIVIDUAL = '개별 평가 조회'
COMPARE = '공정 평가 비교'


def comparison_navigation(unit, chamber):
    key = f'evaluation_mode_{unit}_{chamber}'
    return st.segmented_control('조회 방식', [INDIVIDUAL, COMPARE],
                                default=INDIVIDUAL, key=key) or INDIVIDUAL


def open_comparison(unit, chamber):
    st.session_state[f'evaluation_mode_{unit}_{chamber}'] = COMPARE


def limits(grids):
    values = [v for grid in grids for row in grid for v in row if numeric(v)]
    return (min(values), max(values)) if values else (0, 0)


def difference(grid, baseline):
    if len(grid) != len(baseline) or any(len(a) != len(b) for a, b in zip(grid, baseline)):
        return None
    return [[a-b if numeric(a) and numeric(b) else None for a, b in zip(row, base)]
            for row, base in zip(grid, baseline)]


def uniformity(run, unit):
    value = run.get('unif') if unit == '15' else run.get('metrics', {}).get('Unif.')
    return value * (100 if unit == '45' else 1) if numeric(value) else None


def linked_measurement(unit, run, data, hw, kind):
    measurements = hw.get('previews', {}).get('__hw_data__', {}).get('measurements', [])
    if unit == '15':
        return link_measurement(run, measurements, kind)
    from process45 import link_spacing_history, link_process45
    if kind == 'Spacing':
        return link_spacing_history(run, data.get('measurements', []), measurements)
    return link_process45(run, data.get('measurements', []), kind)


def display_grid(unit, kind, grid):
    if unit == '45' and kind != 'Spacing':
        from classic_cloud.process45_views import flatness_history_grid
        return flatness_history_grid(grid)
    return grid


def placeholder(text='Data 없음'):
    return '<div class="eval-empty">'+escape(text)+'</div>'


def hardware_table(grid, spacing, scale):
    """Render native-size text, preserving the already oriented grid."""
    low, high = scale
    rows = []
    for row in grid:
        cells = []
        for value in row:
            valid = numeric(value)
            ratio = (value-low)/(high-low) if valid and high != low else .5
            ratio = min(1, max(0, ratio))
            color = excel_color(value,low,high)
            label = f'{value:g}' if valid else '—'
            style = '' if spacing else ' style="background:'+color+';color:'+('#172b4d' if valid else '#475569')+'"'
            cells.append('<td'+style+'>'+label+'</td>')
        rows.append('<tr>'+''.join(cells)+'</tr>')
    return '<table aria-label="'+('Spacing' if spacing else 'Flatness')+'" class="eval-hw-table'+(' spacing' if spacing else '')+'"><tbody>'+''.join(rows)+'</tbody></table>'


def comparison_html(unit, selected, data, hw, delta=False):
    from classic_cloud.process_views import map_html
    n = len(selected)
    cells = []
    base = selected[0]
    for i, run in enumerate(selected):
        title = '기준 평가' if i == 0 else f'비교 평가 {i}'
        conditions = []
        for label, field in [('Recipe', 'recipe'), ('Dep Time', 'dep_time'), ('HCG', 'hcg')]:
            value = run.get(field)
            if value is None or value == '':
                continue
            changed = i > 0 and value != base.get(field)
            conditions.append('<span'+(' class="eval-changed"' if changed else '')+'>'+escape(label+': '+str(value))+'</span>')
        cells.append('<section><h3>'+title+' · CH '+escape(run['chamber'])+' · '+escape(run['date'])+'</h3><div class="eval-conditions">'+
                     ' · '.join(conditions)+'</div><small>평가 기록 '+escape(run.get('source_cell', ''))+'</small></section>')
    for kind in KINDS:
        linked = [linked_measurement(unit, run, data, hw, kind) for run in selected]
        grids = [display_grid(unit, kind, m['grid']) if m else [] for m, _ in linked]
        scale = limits(grids)
        for (measured, reason), grid in zip(linked, grids):
            chart = hardware_table(grid, kind == 'Spacing', scale) if measured and grid else placeholder('연결 확인 필요')
            caption = ('H/W 측정일<br><span class="eval-measured-date">'+escape(measured['date'].replace('-','.'))+'</span>') if measured else escape(reason)
            if kind=='Spacing':
                chart='<div class="eval-direction-horizontal">G/V</div>'+chart+'<div class="eval-direction-horizontal">WIN</div>'
            else:
                chart='<div class="eval-direction-wrap"><span>G/V</span><div>'+chart+'</div><span>WIN</span></div>'
            cells.append('<section class="eval-hardware"><div class="eval-hw-label"><h4>'+kind+
                         '</h4><div class="eval-caption">'+caption+'</div></div><div class="eval-hw-values">'+chart+'</div></section>')
    grids = [run['grid'] for run in selected]
    shared = limits(grids)
    deltas = [difference(g, grids[0]) for g in grids]
    delta_limit = max(abs(v) for v in limits([g for g in deltas if g is not None])) or 1
    for i, run in enumerate(selected):
        grid = deltas[i] if delta and i else grids[i]
        use_delta = delta and i > 0
        if grid is None:
            chart = placeholder('측정 칸수가 달라 차이 계산 불가')
        elif use_delta:
            chart = delta_map(grid, delta_limit)
        else:
            chart = map_html(grid, limits=shared)
        u, bu = uniformity(run, unit), uniformity(base, unit)
        footer = 'Unif. '+(f'{u:.2f}%' if u is not None else 'Data 없음')
        if i and u is not None and bu is not None:
            footer += f' · 기준 대비 {u-bu:+.2f}%p'
        title = 'D/R 공정 Map' if unit == '15' else run['recipe']+' 공정 Map'
        if use_delta:
            title += ' · 기준 대비 차이'
        cells.append('<section><h3>'+escape(title)+'</h3><div class="eval-map"><span class="eval-side">G/V</span><div>'+chart+
                     '</div><span class="eval-side">WIN</span></div><div class="eval-unif">'+footer+'</div></section>')
    if unit == '45':
        for run in selected:
            rows = []
            for key, value in run.get('metrics', {}).items():
                text = f'{value*100:.2f}%' if key == 'Unif.' and numeric(value) else str(value)
                rows.append('<tr><th>'+escape(key)+'</th><td>'+escape(text)+'</td></tr>')
            cells.append('<section><h3>공정 결과</h3><table class="classic-table">'+''.join(rows)+'</table></section>')
    return '''<style>
    .eval-scroll{overflow-x:auto;transform:rotateX(180deg);padding-bottom:8px}.eval-scroll>.eval-grid{transform:rotateX(180deg)}.eval-grid{display:grid;gap:4px 8px;align-items:stretch}
    .eval-grid section{min-width:0;border:1px solid #cbd5e1;border-radius:10px;padding:12px;background:#f8fafc}
    .eval-grid h3{margin:0 0 8px}.eval-caption{color:#60758b;min-height:32px;font-size:11px;overflow-wrap:anywhere}
    .eval-grid .eval-hardware{display:grid;grid-template-columns:86px minmax(0,1fr);gap:6px;align-items:center;padding:4px 8px;border-radius:3px;border-width:0 0 1px}
    .eval-hw-label h4{font-size:14px!important;line-height:1.3;margin:0 0 6px;padding:0}
    .eval-hw-values{min-width:0}
    .eval-measured-date{white-space:nowrap;display:inline-block}
    .eval-direction-horizontal{text-align:center;font-size:10px;line-height:12px;color:#075985}
    .eval-direction-wrap{display:grid;grid-template-columns:13px minmax(0,1fr) 13px;gap:3px;align-items:center}
    .eval-direction-wrap>div{min-width:0}
    .eval-direction-wrap>span{writing-mode:vertical-rl;font-size:10px;color:#075985;justify-self:center}
    .eval-direction-wrap>span:first-child{transform:rotate(180deg)}
    .eval-hw-label .eval-caption{min-height:0;font-size:11px;line-height:1.35}
    .eval-hardware p{margin:0}
    .eval-hw-table{width:100%;height:105px;table-layout:fixed;border-collapse:collapse;margin:0;font-variant-numeric:tabular-nums}
    .eval-hw-table td{padding:2px 0;border:1px solid #cbd5e1;text-align:center;font-size:14px;font-weight:700;line-height:1.15}
    .eval-hw-table.spacing{height:78px}.eval-hw-table.spacing td{font-size:17px;background:#fff;color:#17324d}
    .eval-hw-table.spacing tr:nth-child(2) td:nth-child(2){background:#e0f2fe;border:2px solid #0891b2}
    .eval-hw-values .eval-empty{aspect-ratio:auto;height:105px;font-size:13px;text-align:center}
    .eval-empty{aspect-ratio:700/510;border:1px solid #cbd5e1;display:flex;align-items:center;justify-content:center}
    .eval-map{display:grid;grid-template-columns:20px minmax(0,1fr) 20px;align-items:center;gap:5px}
    .eval-map table{border-collapse:collapse;margin:0;width:100%;table-layout:fixed;height:240px}
    .eval-map td{padding:5px 2px!important;font-size:14px;text-align:center}
    .eval-side{writing-mode:vertical-rl;color:#075985;font-size:12px}.eval-side:first-child{transform:rotate(180deg)}
    .eval-unif{text-align:right;font-weight:600;margin-top:8px}.eval-changed{background:#fef3c7;padding:3px}
    .eval-conditions{min-height:44px}.eval-grid small{color:#60758b}
    </style><div class="eval-scroll"><div class="eval-grid" style="grid-template-columns:repeat('''+str(n)+',minmax(360px,1fr));min-width:'+str(n*380)+'px">'+''.join(cells)+'</div></div>'


def delta_map(grid, magnitude):
    if not any(numeric(v) for row in grid for v in row):
        return placeholder()
    rows = []
    for row in grid:
        cells = []
        for v in row:
            color = excel_color(v,-magnitude,magnitude)
            label = f'{v:+g}' if numeric(v) else '—'
            cells.append('<td style="background:'+color+'">'+label+'</td>')
        rows.append('<tr>'+''.join(cells)+'</tr>')
    return '<table>'+''.join(rows)+'</table>'


def comparison_panel(unit, chamber, runs, run, data, hw, mode, count=None):
    if mode != COMPARE:
        st.button('이 평가 기준으로 비교', key=f'compare_open_{unit}_{chamber}',
                  on_click=open_comparison, args=(unit, chamber))
        return False
    prefix = f'compare_{unit}_{chamber}_{run["id"]}'
    same_recipe = True if unit == '45' else st.checkbox('동일 레시피만 비교', value=True, key=prefix+'_same')
    available = [r for r in data.get('records', runs) if r['id'] != run['id']
                 and (not same_recipe or r['recipe'] == run['recipe'])]
    if not available:
        st.info('같은 공정의 비교 가능한 평가 기록이 없습니다.')
        return True
    if count is None:
        count=st.selectbox('비교 대상 수',options=[1,2,3,4],
                           format_func=lambda value:str(value)+'개',key=prefix+'_count_select')
    if count>=3:
        st.caption('비교 표를 좌우로 끌어 모든 평가를 확인할 수 있습니다.')
    selected=[]
    for index, panel in enumerate(st.columns(count)):
        with panel:
            slot=prefix+f'_slot{index}_'+str(same_recipe)
            st.markdown(f'**비교 평가 {index+1}**')
            remaining=[r for r in available if r['id'] not in {x['id'] for x in selected}]
            chambers=sorted({r['chamber'] for r in remaining})
            if not chambers:
                st.info('추가로 비교할 평가 기록이 없습니다.')
                continue
            chamber_key=slot+'_chamber'
            if st.session_state.get(chamber_key) not in chambers:
                used={chamber}|{r['chamber'] for r in selected}
                unused=[c for c in chambers if c not in used]
                st.session_state[chamber_key]=unused[0] if unused else chamber if chamber in chambers else chambers[0]
            chamber_column, record_column = st.columns([1, 3])
            other_chamber=chamber_column.selectbox('비교 챔버',chambers,key=chamber_key)
            candidates=sorted([r for r in remaining if r['chamber']==other_chamber],
                              key=lambda r:(r['date'],r.get('source_cell','')),reverse=True)
            # Prefer the same evaluation date; retain a stable source-cell ordering on ties.
            candidates.sort(key=lambda r:r['date']!=run['date'])
            by_id={r['id']:r for r in candidates}
            record_key=slot+'_'+other_chamber+'_record'
            if st.session_state.get(record_key) not in by_id:
                st.session_state[record_key]=candidates[0]['id']
            identifier=record_column.selectbox('비교 평가 기록',list(by_id),
                format_func=lambda k, records=by_id:records[k]['date']+' · '+records[k]['recipe']+' · '+records[k]['source_cell'],
                key=record_key)
            selected.append(by_id[identifier])
    if not selected:
        return True
    from pathlib import Path
    from streamlit.components.v1 import declare_component
    drag_view=declare_component('process_comparison_drag',path=str(Path(__file__).parent/'drag_compare'))
    drag_view(html=comparison_html(unit, [run]+selected, data, hw, delta=False),font_css=comparison_font_css(),key=prefix+'_drag_view',default=None)
    return True


@st.cache_data
def comparison_font_css():
    """Use the font shipped with this deployed Streamlit version."""
    import base64
    from pathlib import Path
    import streamlit
    fonts=sorted((Path(streamlit.__file__).parent/'static').rglob('*SourceSans*.woff2'))
    regular=next((p for p in fonts if 'Upright' in p.name),None)
    if regular is not None:
        encoded=base64.b64encode(regular.read_bytes()).decode('ascii')
        return '@font-face{font-family:"Source Sans";src:url(data:font/woff2;base64,'+encoded+') format("woff2");font-weight:100 900;font-style:normal;font-display:swap;}'
    # Older Streamlit releases ship separate regular/semibold/bold assets.
    rules=[]
    for weight,word in [(400,'Regular'),(600,'SemiBold'),(700,'Bold')]:
        asset=next((p for p in fonts if word.lower() in p.name.lower() and 'italic' not in p.name.lower()),None)
        if asset is not None:
            encoded=base64.b64encode(asset.read_bytes()).decode('ascii')
            rules.append('@font-face{font-family:"Source Sans";src:url(data:font/woff2;base64,'+encoded+') format("woff2");font-weight:'+str(weight)+';font-style:normal;font-display:swap;}')
    return ''.join(rules)
