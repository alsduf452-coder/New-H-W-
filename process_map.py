"""15-unit process maps from the explicitly selected Unif 결과 데이터 sheet."""
from datetime import date,datetime
from io import BytesIO
from hashlib import sha256
from zipfile import ZipFile
import math,re
from openpyxl import load_workbook
from domain import ValidationError
from excel_sync import MAX_FILE,MAX_UNCOMPRESSED

SCHEMA_VERSION='process15-1'
SHEET='Unif 결과 데이터'
KINDS=('Spacing','Diffuser Flatness','Susceptor Flatness')
def text(v):return '' if v is None else str(v).strip()
def numeric(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def parse_date(v):
    if isinstance(v,datetime):return v.date().isoformat()
    if isinstance(v,date):return v.isoformat()
    m=re.fullmatch(r'(\d{2}|\d{4})[./-](\d{1,2})[./-](\d{1,2})',text(v))
    if not m:raise ValidationError('공정 평가 Date에 연·월·일이 필요합니다.')
    y,m,d=map(int,m.groups())
    try:return date(y+2000 if y<100 else y,m,d).isoformat()
    except ValueError:raise ValidationError('공정 평가 Date를 확인해주세요.') from None


def parse_process(content):
    if len(content)>MAX_FILE:raise ValidationError('Excel은 50MB 이하여야 합니다.')
    with ZipFile(BytesIO(content)) as z:
        if sum(i.file_size for i in z.infolist())>MAX_UNCOMPRESSED:raise ValidationError('압축 해제 크기가 너무 큽니다.')
    book=load_workbook(BytesIO(content),data_only=True,read_only=True)
    try:
        if SHEET not in book.sheetnames:raise ValidationError(SHEET+' 시트가 필요합니다.')
        s=book[SHEET]
        if s.max_row>5000 or s.max_column>200:raise ValidationError('공정 시트 크기를 확인해주세요.')
        rows=list(s.values)
        def val(r,c):return rows[r-1][c-1] if 0<r<=len(rows) and 0<c<=len(rows[r-1]) else None
        records=[]
        for r,row in enumerate(rows,1):
            for c,value in enumerate(row,1):
                if text(value)!='Date':continue
                when=parse_date(val(r,c+1));ch=text(val(r,c+3))
                if ch not in 'ABCDE' or len(ch)!=1:raise ValidationError('공정 PC는 A~E여야 합니다.')
                if text(val(r,c+2))!='PC' or text(val(r,c+4))!='Recipe':raise ValidationError('공정 블록 열 배치를 확인해주세요.')
                if text(val(r+10,c+5))!='Unif.':raise ValidationError('공정 Unif. 위치를 확인해주세요.')
                grid=[[float(val(r+5+i,c+2+j)) if numeric(val(r+5+i,c+2+j)) else None for j in range(5)] for i in range(5)]
                u=val(r+10,c+6)
                if u is not None and not numeric(u):raise ValidationError('Unif.은 Excel 숫자 값이어야 합니다.')
                records.append({'id':sha256(f'{SHEET}|{r}|{c}|{when}|{ch}'.encode()).hexdigest()[:24],
                    'date':when,'chamber':ch,'recipe':text(val(r,c+5)),'dep_time':text(val(r,c+7)),
                    'notes':text(val(r+1,c+1)),'diffuser_sn':text(val(r+2,c+2)),
                    'susceptor_sn':text(val(r+3,c+2)),'hcg':text(val(r+2,c+5)),
                    'grid':grid,'unif':float(u)*100 if numeric(u) else None,
                    'source_cell':s.cell(r,c).coordinate})
        if not records:raise ValidationError('공정 평가 블록이 없습니다.')
        return {'schema':SCHEMA_VERSION,'equipment':'15호기','sheet':SHEET,'records':records}
    finally:book.close()


def serial(v):return re.sub(r'[\s_-]','',text(v)).upper()

def link_measurement(run,measurements,kind):
    candidates=[r for r in measurements if r['kind']==kind and r['chamber']==run['chamber'] and r.get('date') and r['date']<=run['date']]
    if not candidates:return None,'평가일 이전 측정 Data 없음'
    latest=max(r['date'] for r in candidates);same=[r for r in candidates if r['date']==latest]
    fields=['diffuser_sn','susceptor_sn'] if kind=='Spacing' else ['diffuser_sn'] if kind=='Diffuser Flatness' else ['susceptor_sn']
    if any(not run.get(f) for f in fields):return None,'공정 기록 S/N 확인 필요'
    matching=[r for r in same if all(serial(r.get(f))==serial(run[f]) for f in fields)]
    if not matching:return None,f'{latest} 최근 측정 S/N 불일치 · 연결 확인 필요'
    # Operator confirmed on 2026-11-13: the 2025-08-16 A run used
    # the 2025-08-13 post-CSD measurements. Match full dates, workbook
    # block, recipe, both serials and measurement identity; never use row order.
    if (
        run.get('date')=='2025-08-16' and run.get('chamber')=='A'
        and run.get('source_cell')=='AD12' and run.get('recipe')=='PPPLS5K'
        and serial(run.get('diffuser_sn'))=='DIDDBB2002'
        and serial(run.get('susceptor_sn'))=='ASUBBBB2401'
        and latest=='2025-08-13'
    ):
        approved={'Spacing':('Spacing:B33',33),
                  'Diffuser Flatness':('Diff Flatness:C24',24)}.get(kind)
        if approved:
            selected=[r for r in matching if r.get('id')==approved[0]
                      and r.get('source_row')==approved[1]
                      and serial(r.get('diffuser_sn'))=='DIDDBB2002'
                      and serial(r.get('susceptor_sn'))=='ASUBBBB2401'
                      and 'CSD' in text(r.get('reason')).upper()
                      and '40' in text(r.get('reason'))]
            if len(selected)==1:return selected[0],'2025-08-13 CSD 조정 후 · 사용자 확인 연결'
            return None,'2025-08-13 CSD 조정 후 승인 기록 누락/중복 · 연결 확인 필요'
    if len(matching)!=1:return None,f'{latest} 동일 날짜 기록 {len(matching)}개 · 연결 확인 필요'
    return matching[0],''
