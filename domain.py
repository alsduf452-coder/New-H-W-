"""클라우드 Pending의 고유 ID·버전·변경 비교 규칙."""
from datetime import date, datetime
import re

FIELDS = ('ID', '설비', '분야', '상태', '내용', '담당자', '목표일')
FIELDS_WITH_VERSION = (*FIELDS, '버전')
CATEGORIES = ('H/W', 'S/W', '공정', '전장', '기타')
STATES = ('미완료', '완료')


class ValidationError(ValueError):
    pass


def normalize_item(row):
    result = {}
    for field in FIELDS:
        value = row.get(field)
        if field == '목표일' and isinstance(value, (date, datetime)):
            value = value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
        result[field] = '' if value is None else str(value).strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9:_-]{0,79}', result['ID']):
        raise ValidationError('ID는 영문·숫자로 시작하는 80자 이내 고유값이어야 합니다.')
    if not result['설비'] or len(result['설비']) > 100:
        raise ValidationError('설비를 100자 이내로 입력해주세요.')
    if result['분야'] not in CATEGORIES or result['상태'] not in STATES:
        raise ValidationError('분야 또는 상태가 지정된 값과 다릅니다.')
    if not result['내용'] or len(result['내용']) > 20000 or len(result['담당자']) > 200:
        raise ValidationError('내용은 필수이며 20,000자, 담당자는 200자 이하여야 합니다.')
    if result['목표일']:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', result['목표일']):
            raise ValidationError('목표일은 YYYY-MM-DD 또는 빈칸이어야 합니다.')
        try:
            date.fromisoformat(result['목표일'])
        except ValueError as exc:
            raise ValidationError('목표일이 올바른 날짜가 아닙니다.') from exc
    raw = row.get('버전')
    if raw in (None, ''):
        result['버전'] = None
    elif isinstance(raw, bool) or not re.fullmatch(r'\d+', str(raw)):
        raise ValidationError('버전은 0 이상의 정수여야 합니다.')
    else:
        result['버전'] = int(raw)
    return result


def payload(row):
    return {field: row[field] for field in FIELDS}


def build_plan(current, incoming):
    """삭제는 후보로만 표시하고, 오래된 Excel 버전은 덮어쓰지 않습니다."""
    active = {r['ID']: r for r in current}
    incoming = [normalize_item(r) for r in incoming]
    ids = [r['ID'] for r in incoming]
    if len(ids) != len(set(ids)):
        raise ValidationError('Excel 안에 중복 ID가 있습니다.')
    plan = {'changes': [], 'conflicts': [], 'unchanged': [], 'missing': []}
    for row in incoming:
        old = active.get(row['ID'])
        if old is None:
            if row['버전'] not in (None, 0):
                plan['conflicts'].append({'ID': row['ID'], '사유': '서버에 없는 항목에 기존 버전이 있습니다. 대상 앱을 확인해주세요.'})
            else:
                plan['changes'].append({'id': row['ID'], 'after': payload(row), 'expected_version': 0, 'before': None})
        elif payload(row) == payload(old):
            plan['unchanged'].append(row['ID'])
        elif row['버전'] != old['버전']:
            plan['conflicts'].append({'ID': row['ID'], '사유': 'Excel 버전이 현재 DB와 다릅니다. 최신 Excel을 내려받아 변경사항을 대조해주세요.'})
        else:
            plan['changes'].append({'id': row['ID'], 'after': payload(row), 'expected_version': old['버전'], 'before': old})
    plan['missing'] = [r for r in current if r['ID'] not in set(ids)]
    return plan


def access_role(email, allowed_emails, editor_emails):
    email = str(email or '').strip().casefold()
    allowed = {str(v).strip().casefold() for v in allowed_emails}
    editors = {str(v).strip().casefold() for v in editor_emails}
    if not email or email not in allowed:
        return None
    return 'editor' if email in editors else 'viewer'
