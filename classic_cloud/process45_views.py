"""45-unit comparison from the five PC sheets, without placeholder results."""
import pandas as pd
import streamlit as st
from classic_cloud.evaluation_compare import comparison_navigation, comparison_panel
from process45 import KINDS, link_process45, link_spacing_history, numeric
from classic_cloud.visuals import diagram_svg
from classic_cloud.process_views import map_html


def flatness_history_grid(grid):
    """PC rows run G/V to Window; PC columns run opposite to H/W rows.

    A 90-degree counterclockwise rotation matches the H/W history's 5x7
    coordinates. A transpose alone mirrors the top and bottom rows.
    """
    return [list(column) for column in zip(*grid)][::-1]


def measurement_chart(grid, title, spacing=False, process=False):
    if not any(numeric(value) for line in grid for value in line):
        return
    # Keep Spacing point positions and process maps in their source order.
    # Only Flatness needs rotation to the H/W history coordinate system.
    display_grid = grid if spacing or process else flatness_history_grid(grid)
    html = map_html(display_grid).replace('Data 없음', '—') if process else diagram_svg(display_grid, spacing, show_position_labels=False,match_spacing_size=True)
    if process:
        html = ('<div style="display:grid;grid-template-columns:28px minmax(0,1fr) 28px;align-items:center;gap:8px">'
                '<div style="justify-self:center;writing-mode:vertical-rl;transform:rotate(180deg);white-space:nowrap;color:#075985;font-size:13px">G/V</div>'
                '<div style="min-width:0">'+html+'</div>'
                '<div style="justify-self:center;writing-mode:vertical-rl;white-space:nowrap;color:#075985;font-size:13px">WIN</div></div>')
    st.markdown(html, unsafe_allow_html=True)


def process45_panel(snapshot, hw_snapshot=None):
    st.header('6G · 45호기 H/W 형상 · 공정 Map 비교')
    data = snapshot.get('previews', {}).get('__process_data__')
    if not data or data.get('equipment') != '45호기':
        st.info('45호기 공정 파일 수신을 기다리고 있습니다.')
        return
    from classic_cloud.compact_process import compact_panel
    compact_panel('45',data,hw_snapshot or {})
