"""실제 설비 데이터가 없는 가상 샘플."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def sample_items():
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    specs = [('DEMO-001', 'DEMO-01', 'H/W', '미완료', '샘플: 부품 점검 일정 확인', -2), ('DEMO-002', 'DEMO-02', 'S/W', '미완료', '샘플: 알람 메시지 표시 개선', 3), ('DEMO-003', 'DEMO-01', '공정', '완료', '샘플: 시험 조건 확인', 10)]
    return [{'ID': key, '설비': eq, '분야': cat, '상태': state, '내용': text, '담당자': '샘플 담당자', '목표일': (today + timedelta(days=offset)).isoformat()} for key, eq, cat, state, text, offset in specs]
