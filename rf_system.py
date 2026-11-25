"""RF configuration from the same PC worksheet evaluation block."""
import re
from html import escape


def clean(value):
    return '' if value is None else str(value).strip()


def normalized(value):
    return re.sub(r'\s+', '', clean(value)).casefold()


def parse_rf_system(rows, start_column, end_column):
    """Read labelled RF rows only; never borrow values from another block."""
    names = {'rfg': 'rfg', 'matcher': 'matcher', 'rfcable': 'cable'}
    fields = {'maker': 'maker', '제조사': 'maker', 's/n': 'serial',
              'type': 'type', 'length': 'length', 'bellows수': 'bellows',
              'bellows': 'bellows'}
    matches = {}
    for row_number, row in enumerate(rows[:49], 1):
        cells = list(row[start_column-1:end_column])
        for index, value in enumerate(cells):
            kind = names.get(normalized(value))
            if kind is None:
                continue
            labels = [(i, fields[normalized(v)]) for i, v in enumerate(cells)
                      if i > index and normalized(v) in fields]
            values = {}
            for position, (column, field) in enumerate(labels):
                stop = labels[position+1][0] if position+1 < len(labels) else len(cells)
                candidates = [clean(v) for v in cells[column+1:stop] if clean(v)]
                if len(candidates) == 1:
                    values[field] = candidates[0]
            allowed = ('type', 'length', 'bellows') if kind == 'cable' else ('maker', 'serial')
            entry = {key: values[key] for key in allowed if key in values}
            if entry:
                entry['source_row'] = row_number
                matches.setdefault(kind, []).append(entry)
    return {kind: entries[0] for kind, entries in matches.items() if len(entries) == 1}


def rf_system_card(run):
    rf = run.get('rf_system') or {}
    def value(kind, field):
        raw = clean(rf.get(kind, {}).get(field))
        return escape(raw or '—')
    rows = []
    for kind, label in [('rfg', 'RFG'), ('matcher', 'Matcher')]:
        rows.append('<tr><th scope="row">'+label+'</th><th>제조사</th><td>'+
                    value(kind, 'maker')+'</td><th>S/N</th><td colspan="3">'+
                    value(kind, 'serial')+'</td></tr>')
    rows.append('<tr><th scope="row">RF Cable</th><th>Type</th><td>'+
                value('cable', 'type')+'</td><th>Length</th><td>'+
                value('cable', 'length')+'</td><th>Bellows</th><td>'+
                value('cable', 'bellows')+'</td></tr>')
    notice = '<small class="fit-rf-missing">RF 정보 없음 · Excel 동기화 확인 필요</small>' if not rf else ''
    return ('<section class="fit-rf-card"><h3>RF System</h3><small>CH '+
            escape(clean(run.get('chamber')))+
            '</small><table class="fit-rf-table"><colgroup><col style="width:20%"><col style="width:14%">'+
            '<col style="width:15%"><col style="width:12%"><col style="width:14%">'+
            '<col style="width:15%"><col style="width:10%"></colgroup><tbody>'+
            ''.join(rows)+'</tbody></table>'+notice+'</section>')
