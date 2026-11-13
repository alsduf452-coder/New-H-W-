"""45-unit PC_A..PC_E evaluation snapshots; never read other worksheets."""
from datetime import date, datetime
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile, BadZipFile
import json
import math
import re
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from domain import ValidationError
from excel_sync import MAX_FILE, MAX_UNCOMPRESSED
from process_map import serial

SCHEMA_VERSION = 'process45-1'
SHEETS = tuple('PC_'+ch for ch in 'ABCDE')
KINDS = ('Spacing', 'Diffuser Flatness', 'Susceptor Flatness')


def text(value):
    return '' if value is None else str(value).strip()


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def present(value):
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return numeric(value)
    clean = re.sub(r'\s+', '', text(value)).casefold()
    return bool(clean) and clean not in ('data없음', '미측정', '없음', '-', '—') and not clean.startswith('#')


def dated(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    match = re.fullmatch(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})(?: 00:00:00)?', text(value))
    if not match:
        return ''
    try:
        return date(*map(int, match.groups())).isoformat()
    except ValueError:
        return ''


def parse_process45(content):
    if len(content) > MAX_FILE:
        raise ValidationError('Excel은 50MB 이하여야 합니다.')
    try:
        with ZipFile(BytesIO(content)) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > MAX_UNCOMPRESSED:
                raise ValidationError('압축 해제 크기가 너무 큽니다.')
        book = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except (BadZipFile, OSError, KeyError):
        raise ValidationError('정상적인 45호기 Excel이 필요합니다.') from None
    try:
        if any(name not in book.sheetnames for name in SHEETS):
            raise ValidationError('PC_A~PC_E 시트가 모두 필요합니다.')
        records, measurements, warnings = [], {}, []
        blocks = excluded = 0
        for name in SHEETS:
            sheet = book[name]
            if (sheet.max_row or 0) > 2000 or (sheet.max_column or 0) > 300:
                raise ValidationError(name+': PC 시트 크기를 확인해주세요.')
            rows = list(sheet.iter_rows(max_row=122, max_col=sheet.max_column, values_only=True))
            def value(r, c):
                return rows[r-1][c-1] if 0 < r <= len(rows) and 0 < c <= len(rows[r-1]) else None
            for c in range(2, sheet.max_column+1, 9):
                if not any(value(2, c+i) is not None for i in range(8)):
                    continue
                if value(2, c+1) != 'MT 일자':
                    raise ValidationError(name+': 평가 블록 배치를 확인해주세요.')
                blocks += 1
                mt = dated(value(2, c+2))
                hardware = {}
                for r, title in [(10, 'Diffuser Flatness'), (22, 'Susceptor Flatness'), (34, 'Spacing')]:
                    if value(r, c) != title or value(r, c+1) != 'Date' or value(r+1, c+1) != 'Diff. S/N' or value(r+1, c+3) != 'Susc. S/N':
                        raise ValidationError(name+': H/W Date·S/N 배치를 확인해주세요.')
                    when = dated(value(r, c+2))
                    diffuser = text(value(r+1, c+2)) if present(value(r+1, c+2)) else ''
                    susceptor = text(value(r+1, c+4)) if present(value(r+1, c+4)) else ''
                    coords = [[(r+5+2*i, c+2+2*j) for j in range(3)] for i in range(3)] if title == 'Spacing' else [[(r+4+i, c+2+j) for j in range(5)] for i in range(7)]
                    grid = [[value(ri, ci) if numeric(value(ri, ci)) else None for ri, ci in line] for line in coords]
                    if not when or not any(numeric(v) for line in grid for v in line):
                        continue
                    relevant = [serial(diffuser), serial(susceptor)] if title == 'Spacing' else [serial(diffuser)] if title == 'Diffuser Flatness' else [serial(susceptor)]
                    # Evaluation cards repeat earlier H/W snapshots. Coalesce only
                    # identical date, kind, chamber, relevant serials and full grid.
                    identity = sha256(json.dumps([name, title, when, relevant, grid], ensure_ascii=False).encode()).hexdigest()[:24]
                    if identity not in measurements:
                        measurements[identity] = {'id': identity, 'kind': title, 'chamber': name[-1], 'date': when, 'diffuser_sn': diffuser, 'susceptor_sn': susceptor, 'grid': grid, 'reason': text(value(r+2, c+2)), 'source_row': r, 'source_sheet': name}
                    hardware[title] = identity
                diffuser = text(value(35, c+2)) if present(value(35, c+2)) else text(value(11, c+2))
                susceptor = text(value(35, c+4)) if present(value(35, c+4)) else text(value(23, c+4))
                for r, recipe in [(50, 'YCNT'), (74, 'YILD'), (98, 'YILD2')]:
                    if re.sub(r'\s+', '', text(value(r, c))) != '공정결과'+recipe or value(r, c+1) != 'Date':
                        raise ValidationError(name+': 공정 결과 블록 배치를 확인해주세요.')
                    grid = [[value(r+7+i, c+2+j) if numeric(value(r+7+i, c+2+j)) else None for j in range(5)] for i in range(6)]
                    positions = [('Unif.', r+1, c+3), ('Average', r+1, c+5), ('STD', r+1, c+7), ('Min', r+2, c+3), ('Max', r+2, c+5), ('D/R', r+3, c+3), ('Stress Center', r+3, c+5), ('Stress Edge', r+3, c+7), ('D/T', r+4, c+3), ('RI', r+4, c+5), ('막밀도', r+4, c+7), ('조성비', r+5, c+3), ('표면거칠기', r+5, c+5)]
                    metrics = {label: value(ri, ci) for label, ri, ci in positions if present(value(ri, ci))}
                    when = dated(value(r, c+2))
                    if not when or not metrics and not any(numeric(v) for line in grid for v in line):
                        excluded += 1
                        if not when and (metrics or any(numeric(v) for line in grid for v in line)):
                            warnings.append(name+' '+get_column_letter(c)+str(r)+': 공정 Date 미확정으로 제외')
                        continue
                    identity = sha256(f'{name}|{c}|{recipe}|{when}'.encode()).hexdigest()[:24]
                    records.append({'id': identity, 'chamber': name[-1], 'date': when, 'mt_date': mt, 'recipe': recipe, 'diffuser_sn': diffuser, 'susceptor_sn': susceptor, 'grid': grid, 'metrics': metrics, 'hardware': hardware, 'source_sheet': name, 'source_cell': get_column_letter(c)+str(r)})
        if not records:
            raise ValidationError('Date가 확인된 45호기 공정 결과가 없습니다.')
        return {'schema': SCHEMA_VERSION, 'equipment': '45호기', 'sheets': list(SHEETS), 'records': records, 'measurements': list(measurements.values()), 'blocks': blocks, 'excluded_results': excluded, 'warnings': warnings}
    finally:
        book.close()


def link_process45(run, measurements, kind):
    # The workbook already associates an H/W snapshot with each evaluation
    # card. Preserve that association; never choose a different card merely
    # because its measurement has the same calendar date.
    identifier = run.get('hardware', {}).get(kind)
    candidates = [m for m in measurements if m['id'] == identifier and m['kind'] == kind and m['chamber'] == run['chamber']]
    if len(candidates) != 1:
        return None, '측정 자료 미기재'
    measured = candidates[0]
    if measured['date'] > run['date']:
        return None, '공정 평가일 이후의 H/W 측정값은 제외했습니다.'
    fields = ['diffuser_sn', 'susceptor_sn'] if kind == 'Spacing' else ['diffuser_sn'] if kind == 'Diffuser Flatness' else ['susceptor_sn']
    if any(not run.get(field) or not measured.get(field) or serial(run[field]) != serial(measured[field]) for field in fields):
        return None, 'H/W 측정 S/N 확인 필요'
    return measured, ''
