"""Read both customer-request tables from the existing workbook snapshot."""
import re
from hashlib import sha256


def customer_rows(previews, columns):
    result=[]
    for name, sheet in previews.items():
        if ''.join(name.split())!='고객사요청':
            continue
        section=None
        for line,row in enumerate(sheet.get('rows',[]),1):
            def val(c):
                return str(row[c-1]).strip() if c<=len(row) and row[c-1] is not None else ''
            if val(2)=='No.':
                section='설비별 조치' if val(7)=='호기' else '검토 요청' if val(5)=='수정 할 사항' else None
                continue
            if not section or not re.fullmatch(r'\d+(?:\.0)?',val(2)) or not val(5):
                continue
            item={key:'' for key in columns}
            identity='|'.join([name,section,val(2),str(line)])
            item.update(ID='customer-'+sha256(identity.encode()).hexdigest()[:24],범위='고객사 요청',시트=name,
                        분야=val(3) or '미기재',Unit=val(4),내용=val(5),설비='미기재',상태='확인 필요')
            item['요청 구분']=section
            item['진행 사항']=val(11)
            item['45호기 적용 여부']=val(13)
            item['기존 펜딩 중복 여부']=val(12)
            if section=='설비별 조치':
                raw=val(10)
                item.update(설비=val(7) or '미기재',발생일=val(6),목표일=val(8),완료일=val(9))
            else:
                raw=val(8) or val(7)
                item['검토 결과']=val(6)
                item['목표일']=val(9)
            item['완료 여부 원문']=' / '.join(filter(None,[val(7),val(8)])) if section=='검토 요청' else raw
            item['상태']='완료' if raw.upper() in ('O','○','완료') else '미완료' if raw.upper() in ('X','미완료') else '확인 필요'
            result.append(item)
    return result
