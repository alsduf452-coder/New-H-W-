"""Date comparison using the same measurement links as the individual view."""
from html import escape
import streamlit as st
from classic_cloud.visuals import diagram_svg, numeric
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
        cells.append('<section><h3>'+title+' · '+escape(run['date'])+'</h3><div class="eval-conditions">'+
                     ' · '.join(conditions)+'</div><small>평가 기록 '+escape(run.get('source_cell', ''))+'</small></section>')
    hardware_cards = [[] for _ in selected]
    hardware_details = [[] for _ in selected]
    for kind in KINDS:
        linked = [linked_measurement(unit, run, data, hw, kind) for run in selected]
        grids = [display_grid(unit, kind, m['grid']) if m else [] for m, _ in linked]
        scale = limits(grids)
        for index, ((measured, reason), grid) in enumerate(zip(linked, grids)):
            chart = diagram_svg(grid, kind == 'Spacing', limits=scale,
                                show_position_labels=False, match_spacing_size=True) if measured and grid else placeholder('연결 확인 필요')
            caption = 'H/W 측정일 '+measured['date'] if measured else reason
            card = ('<div class="eval-hw-card"><h4>'+kind+'</h4><div class="eval-caption">'+escape(caption)+'</div>'+chart+'</div>')
            hardware_cards[index].append(card)
            hardware_details[index].append(card)
    for cards, details in zip(hardware_cards, hardware_details):
        cells.append('<section class="eval-hardware"><div class="eval-hw-row">'+''.join(cards)+
                     '</div><details class="eval-hw-detail"><summary>H/W 수치 크게 보기</summary>'+
                     ''.join(details)+'</details></section>')
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
        cells.append('<section><h3>'+escape(title)+'</h3><div class="eval-map"><span class="eval-side">G/V 측</span><div>'+chart+
                     '</div><span class="eval-side">Window 측</span></div><div class="eval-unif">'+footer+'</div></section>')
    if unit == '45':
        for run in selected:
            rows = []
            for key, value in run.get('metrics', {}).items():
                text = f'{value*100:.2f}%' if key == 'Unif.' and numeric(value) else str(value)
                rows.append('<tr><th>'+escape(key)+'</th><td>'+escape(text)+'</td></tr>')
            cells.append('<section><h3>공정 결과</h3><table class="classic-table">'+''.join(rows)+'</table></section>')
    return '''<style>
    .eval-scroll{overflow-x:auto}.eval-grid{display:grid;gap:12px;align-items:stretch}
    .eval-grid section{min-width:0;border:1px solid #cbd5e1;border-radius:10px;padding:12px;background:#f8fafc}
    .eval-grid h3{margin:0 0 8px}.eval-caption{color:#60758b;min-height:32px;font-size:11px;overflow-wrap:anywhere}
    .eval-hw-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;align-items:start}
    .eval-hw-card{min-width:0}.eval-hw-card h4{font-size:12px!important;line-height:1.3;min-height:32px;margin:0 0 4px;padding:0}
    .eval-hw-card svg{width:100%;height:auto;display:block}
    .eval-hw-card .eval-empty{font-size:11px;text-align:center}
    .eval-hw-detail{margin-top:8px}.eval-hw-detail summary{cursor:pointer;color:#365f88;font-size:12px}
    .eval-hw-detail .eval-hw-card{margin:12px auto 0;max-width:560px}
    .eval-hw-detail h4{font-size:16px!important;min-height:0}.eval-hw-detail .eval-caption{font-size:12px;min-height:24px}
    .eval-empty{aspect-ratio:700/510;border:1px solid #cbd5e1;display:flex;align-items:center;justify-content:center}
    .eval-map{display:grid;grid-template-columns:20px minmax(0,1fr) 20px;align-items:center;gap:5px}
    .eval-map table{border-collapse:collapse;margin:0;width:100%;table-layout:fixed;height:300px}
    .eval-map td{padding:10px 2px!important;font-size:14px;text-align:center}
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
            color = '#e2e8f0' if not numeric(v) else f'hsl({0 if v > 0 else 215},65%,{98-35*abs(v)/magnitude:.1f}%)'
            label = f'{v:+g}' if numeric(v) else '—'
            cells.append('<td style="background:'+color+'">'+label+'</td>')
        rows.append('<tr>'+''.join(cells)+'</tr>')
    return '<table>'+''.join(rows)+'</table>'


def comparison_panel(unit, chamber, runs, run, data, hw, mode):
    if mode != COMPARE:
        st.button('이 평가 기준으로 비교', key=f'compare_open_{unit}_{chamber}',
                  on_click=open_comparison, args=(unit, chamber))
        return False
    st.caption(('Barrier 단일막' if unit == '15' else run['recipe'])+' · 위에서 선택한 공정 평가 기록을 기준으로 비교합니다.')
    prefix = f'compare_{unit}_{chamber}_{run["id"]}'
    same_recipe = True if unit == '45' else st.checkbox('동일 레시피만 비교', value=True, key=prefix+'_same')
    candidates = {r['id']: r for r in runs if r['id'] != run['id'] and r['chamber'] == chamber
                  and (not same_recipe or r['recipe'] == run['recipe'])}
    if not candidates:
        st.info('같은 조건의 비교 가능한 평가 기록이 없습니다.')
        return True
    key = prefix+('_same_runs' if same_recipe else '_all_runs')
    if key in st.session_state:
        st.session_state[key] = [k for k in st.session_state[key] if k in candidates][:2]
    ids = st.multiselect('비교 평가 기록 (최대 2개)', list(candidates), default=list(candidates)[:1], max_selections=2,
                         format_func=lambda k: candidates[k]['date']+' · '+candidates[k]['recipe']+' · '+candidates[k]['source_cell'], key=key)
    if not ids:
        st.info('비교할 평가 기록을 선택해주세요.')
        return True
    delta = st.segmented_control('공정 Map 표시', ['원본 값', '기준 대비 차이'], default='원본 값', key=prefix+'_display') == '기준 대비 차이'
    st.caption('같은 항목은 색상 범위를 통일합니다. 차이는 비교값 − 기준값이며, 측정값이 없는 위치는 계산하지 않습니다.' if not delta
               else '기준 Map은 원본 값입니다. 비교 Map은 증가 빨강·감소 파랑으로 표시하며, 색은 양호/불량 판정이 아닙니다.')
    st.markdown(comparison_html(unit, [run]+[candidates[k] for k in ids], data, hw, delta), unsafe_allow_html=True)
    return True
