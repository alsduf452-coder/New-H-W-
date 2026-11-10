"""Selected 8.6G measurement blocks; never import workbook deviation tables."""
from datetime import date
from hashlib import sha256
from io import BytesIO
import math
import re
from zipfile import ZipFile, BadZipFile
from openpyxl import load_workbook
from domain import ValidationError
from excel_sync import MAX_FILE, MAX_UNCOMPRESSED

SCHEMA_VERSION='hw86-1'
SHEETS={'Diffuser Flat.':'Diffuser Flatness','Susceptor Flat.':'Susceptor Flatness','Spacing':'Spacing','Shim 변경이력':'Shim 변경이력'}


def number(v):
    return float(v) if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) else None


def text(v):return '' if v is None else str(v).strip()


def measured_date(title):
    m=re.search(r'\((\d{2,4})/(\d{1,2})/(\d{1,2})\)',title)
    if not m:return ''
    y,m,d=map(int,m.groups())
    try:return date(y+2000 if y<100 else y,m,d).isoformat()
    except ValueError:return ''


def stats(grid):
    values=[v for row in grid for v in row if v is not None]
    return {'count':len(values),'min':min(values) if values else None,'max':max(values) if values else None,
            'range':max(values)-min(values) if values else None,
            'center':grid[len(grid)//2][len(grid[0])//2] if grid else None}


def delta(base,other,key='grid'):
    a,b=base[key],other[key]
    if len(a)!=len(b) or any(len(x)!=len(y) for x,y in zip(a,b)):
        raise ValueError('배열 크기가 달라 비교할 수 없습니다.')
    if base['kind']!=other['kind']:raise ValueError('같은 측정 항목끼리 비교해주세요.')
    return [[None if x is None or y is None else round(y-x,6) for x,y in zip(ar,br)] for ar,br in zip(a,b)]


def parse_hw86(content):
    if len(content)>MAX_FILE:raise ValidationError('Excel은 50MB 이하여야 합니다.')
    try:
        with ZipFile(BytesIO(content)) as z:
            if sum(i.file_size for i in z.infolist())>MAX_UNCOMPRESSED:raise ValidationError('압축 해제 크기가 100MB를 초과합니다.')
        book=load_workbook(BytesIO(content),data_only=True)
    except (BadZipFile,OSError,KeyError):raise ValidationError('정상적인 xlsx 파일이 아닙니다.') from None
    records=[];warnings=[]
    try:
        if not set(SHEETS)<=set(book.sheetnames):raise ValidationError('8.6G H/W의 네 필수 시트를 확인해주세요.')
        for name,kind in SHEETS.items():
            sheet=book[name]
            if sheet.max_row>5000 or sheet.max_column>200:raise ValidationError(name+': 시트 크기 제한을 초과했습니다.')
            blocks=sorted((m for m in sheet.merged_cells.ranges if m.max_col-m.min_col==6 and m.max_row-m.min_row==1),key=lambda m:(m.min_row,m.min_col))
            sheet_records=[]
            for block in blocks:
                r,c=block.min_row,block.min_col;title=text(sheet.cell(r,c).value)
                if not title or title=='편차' or title=='입력용' or 'Backing Plate' in title:continue
                if not (title.startswith('(') or title.startswith('[A6')):continue
                height=5
                # Some TTS measurements contain seven actual rows, not five.
                if kind not in ('Spacing','Shim 변경이력') and any(number(sheet.cell(r+8+i,c+j).value) is not None for i in range(2) for j in range(7)):height=7
                grid=[[number(sheet.cell(r+3+i,c+j).value) for j in range(7)] for i in range(height)]
                cell_notes=[f'{i+1}행 {j+1}열: {text(sheet.cell(r+3+i,c+j).value)}' for i in range(height) for j in range(7) if sheet.cell(r+3+i,c+j).value is not None and number(sheet.cell(r+3+i,c+j).value) is None]
                note=text(sheet.cell(r+2,c).value)
                record={'id':sha256(f'{name}|{block.coord}|{title}'.encode()).hexdigest()[:24],
                    'kind':kind,'sheet':name,'cell':sheet.cell(r,c).coordinate,'row':r,'column':c,
                    'title':title,'date':measured_date(title),'notes':note,'cell_notes':cell_notes,
                    'condition':' / '.join(re.findall(r'Temp\.?\s*(?:Up|Down)\s*(?:전|후)|(?:Vent|Pumping)\s*상태',title)),
                    'representation':'변환표' if '변환' in title else '원본 측정',
                    'grid':grid,'stats':stats(grid),'shim':[],'shim_notes':[]}
                if not record['date']:warnings.append(name+' '+record['cell']+': 날짜 확인 필요 · '+title.splitlines()[0])
                if kind=='Shim 변경이력':
                    # Nine-row spatial grid retains added positions and taper arrows.
                    record['shim']=[[number(sheet.cell(r+9+i,c+j).value) for j in range(7)] for i in range(9)]
                    end=next((m.min_row for m in blocks if m.min_col==c and m.min_row>r),sheet.max_row+1)
                    for rr in range(r+9,min(end,sheet.max_row+1)):
                        for cc in range(c,c+7):
                            v=sheet.cell(rr,cc).value
                            if v is not None and number(v) is None:record['shim_notes'].append(f'{sheet.cell(rr,cc).coordinate}: {text(v)}')
                sheet_records.append(record)
            if not sheet_records:raise ValidationError(name+': 인식 가능한 측정 블록이 없습니다.')
            records.extend(sheet_records)
        return {'schema':SCHEMA_VERSION,'equipment':'A6 BP-04','measurements':records,'warnings':warnings}
    finally:book.close()
