"""Compact display of manual sync results; full worker text stays available."""
import re
from html import escape
import streamlit as st

SOURCES = (
    ('15HW', '15호기'), ('45HW', '45호기'),
    ('6G 통합 펜딩', 'PENDING'), ('8G 펜딩', '8G PENDING'),
    ('8.6G HW', '8.6G H/W'), ('15호기 공정 MAP', '15호기 공정 Map'),
)
LABELS = {
    'pending': 'PC 응답 대기 중', 'running': 'Excel 동기화 중',
    'done': '동기화 완료', 'failed': '동기화 실패',
    'blocked': '동기화 일시정지 또는 부재 기간', 'expired': '동기화 요청 만료',
}
PATTERN = re.compile(r'(?:^| / )(' + '|'.join(re.escape(key) for _, key in SOURCES) + r'): ')


def source_results(request):
    summary = request.get('summary') or ''
    matches = list(PATTERN.finditer(summary))
    messages = {
        match.group(1): summary[match.end():matches[i+1].start() if i+1 < len(matches) else len(summary)]
        for i, match in enumerate(matches)
    }
    results = []
    for label, key in SOURCES:
        message = messages.get(key, '')
        # Ignore filenames: an error keyword in a filename is not a sync failure.
        message = re.sub(r'^\[[^\]]*\]\s*', '', message)
        if any(word in message for word in ('실패', '충돌', '설정 필요', '오류')):
            state, tone = '실패', 'error'
        elif '변경 없음' in message:
            state, tone = '변경 없음', 'ok'
        elif '전송 완료' in message:
            state, tone = '업데이트 완료', 'ok'
        elif request.get('status') == 'pending':
            state, tone = '대기', 'muted'
        elif request.get('status') == 'running':
            state, tone = '진행 중', 'muted'
        else:
            # Worker summaries can be truncated at 500 characters; never infer success.
            state, tone = '결과 확인 필요', 'muted'
        results.append((label, state, tone))
    return results


def render_sync_status(request):
    results = source_results(request)
    good = sum(tone == 'ok' for _, _, tone in results)
    status = request.get('status')
    title = LABELS.get(status, '동기화 상태 확인 필요')
    if status in ('done', 'failed'):
        title += f' · {good}/6 정상'
    tiles = ''.join(
        '<div class="sync-result"><span>'+escape(label)+'</span>'
        '<span class="sync-result-'+tone+'">'+escape(state)+'</span></div>'
        for label, state, tone in results
    )
    st.markdown(
        '<style>.sync-summary{background:#eef5fc;border-radius:10px;padding:14px 16px;margin-bottom:8px}'
        '.sync-summary-title{font-weight:600;margin-bottom:10px}'
        '.sync-results{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px 20px}'
        '.sync-result{display:flex;justify-content:space-between;gap:8px;font-size:14px;flex-wrap:wrap}'
        '.sync-result-ok{color:#21633c}.sync-result-error{color:#b42318;font-weight:600}'
        '.sync-result-muted{color:#64748b}'
        '@media(max-width:640px){.sync-results{grid-template-columns:1fr}}</style>'
        '<div class="sync-summary"><div class="sync-summary-title">'+escape(title)+'</div>'
        '<div class="sync-results">'+tiles+'</div></div>',
        unsafe_allow_html=True,
    )
    with st.expander('상세 보기'):
        st.text(request.get('summary') or LABELS.get(status, '상세 결과 없음'))
