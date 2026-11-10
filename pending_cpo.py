"""8G CPO snapshot parser. Retains source categories and detailed progress states."""
from hashlib import sha256
from io import BytesIO
import re
from openpyxl import load_workbook
from domain import ValidationError
from pending_octa import original, target_date

SCHEMA_VERSION = 'pending-cpo-1'
HEADERS = ['분류','No.','개선 Item','상세 내용','추후 진행 계획','일정','완료일','완료 여부','비고','진척도']
STATES = {'완료','고객 전달 완료','미완료','추후 진행','SDC 검토중','준비 완료','Monitoring'}


def parse_cpo(content, source_id='pending-8g'):
    book=load_workbook(BytesIO(content),read_only=True,data_only=True)
    try:
        if 'CPO Pending Item' not in book.sheetnames:
            raise ValidationError('8G CPO Pending Item 시트가 필요합니다.')
        sheet=book['CPO Pending Item']
        if (sheet.max_row or 0)>5030 or (sheet.max_column or 0)>200:
            raise ValidationError('8G PENDING 허용 범위를 초과합니다.')
        rows=list(sheet.values)
        headers=[i for i,row in enumerate(rows[:30]) if all(original(v) in [original(c) for c in row] for v in HEADERS)]
        if len(headers)!=1:raise ValidationError('8G PENDING 머리글을 확인해주세요.')
        header=headers[0];names=[original(v) for v in rows[header]]
        if any(names.count(h)!=1 for h in HEADERS):raise ValidationError('8G PENDING 열이 중복됩니다.')
        equipment=''
        if 'Summary' in book:
            for row in book['Summary'].iter_rows(max_row=5,max_col=16,values_only=True):
                for value in row:
                    match=re.search(r'\bA\d+\s+BP[-_ ]\d+\b',original(value))
                    if match:equipment=match.group(0)
        if not equipment:raise ValidationError('Summary 상단의 설비명(A6 BP-04 형식)을 확인해주세요.')
        details=[];warnings=[];seen=set();notes={}
        for line,row in enumerate(rows[header+1:],header+2):
            values={h:row[names.index(h)] for h in HEADERS}
            if all(v is None or original(v)=='' for v in values.values()):continue
            number=values['No.']
            if isinstance(number,bool) or not isinstance(number,(int,float)) or number<1 or int(number)!=number:
                raise ValidationError(f'8G {line}행: 정수 No.가 필요합니다.')
            number=int(number)
            if original(values['분류'])=='비고':
                notes.setdefault(number,[]).append(original(values['개선 Item']))
                continue
            if number in seen:raise ValidationError(f'8G {line}행: No.가 중복됩니다.')
            seen.add(number)
            status=original(values['완료 여부'])
            if status not in STATES:raise ValidationError(f'8G {line}행: 완료 여부를 확인해주세요.')
            if not original(values['분류']) or not original(values['개선 Item']):
                raise ValidationError(f'8G {line}행: 분류와 개선 Item은 필수입니다.')
            progress=values['진척도']
            if progress is not None and (isinstance(progress,bool) or not isinstance(progress,(int,float)) or not 0<=progress<=1):
                raise ValidationError(f'8G {line}행: 진척도는 0~100%여야 합니다.')
            _,warning=target_date(values['일정'])
            if warning:warnings.append({'시트':sheet.title,'행':line,'목표일 원문':original(values['일정']),'안내':warning})
            detail={h:original(v) for h,v in values.items()}
            detail.update({'ID':'P8-'+sha256(f'{source_id}|{equipment}|{number}'.encode()).hexdigest()[:32],
                '시트':sheet.title,'No.':number,'호기':equipment,'분야':original(values['분류']),
                '범위':'주요 항목','완료여부':'완료' if status in ('완료','고객 전달 완료') else '미완료',
                '불합리 및 이슈 내용':original(values['개선 Item'])+'\n'+original(values['상세 내용']),
                '진행 사항':original(values['추후 진행 계획']),'목표일 원문':original(values['일정']),
                '원본 상태':status,'진척도':f'{progress*100:g}%' if progress is not None else ''})
            details.append(detail)
        if not details or len(details)>5000:raise ValidationError('8G PENDING은 1~5,000건이어야 합니다.')
        if set(notes)-seen:raise ValidationError('8G 비고의 No.와 일치하는 PENDING 항목이 없습니다.')
        for detail in details:detail['관련 메모']='\n\n'.join(notes.get(detail['No.'],[]))
        return {'details':details,'warnings':warnings,'count':len(details),
            'done':sum(d['완료여부']=='완료' for d in details),'schema':SCHEMA_VERSION}
    finally:book.close()
