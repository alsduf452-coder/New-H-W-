from datetime import date, datetime
from io import BytesIO
import re
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from pending_octa import target_date

MAIN = ['HW(설계)','공정','SW','전장','기타']
COLS = ['ID','범위','설비','분야','상태','Unit','내용','담당자','목표일','발생일','원인','진행 사항','조치내용','완료일','조치자','45호기 적용 여부','시트','개선 Item','상세 내용','원본 상태','진척도','비고','관련 메모','요청 구분','검토 결과','완료 여부 원문','기존 펜딩 중복 여부']


def text(value):
    return '' if value is None else str(value).strip()


def display_target_date(value):
    value=text(value)
    match=re.fullmatch(r'(\d{4}-\d{2}-\d{2})[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?',value)
    return match.group(1) if match else value


def pending_frame(snapshot):
    previews = snapshot.get('previews',{})
    details = previews.get('__pending_data__',{}).get('details',[])
    rows=[]
    for detail in details:
        rows.append({'ID':detail['ID'],'범위':detail.get('범위','주요 5개 분야'),'설비':text(detail.get('호기')) or '미기재','분야':detail.get('분야',detail.get('시트','')),'상태':'완료' if text(detail.get('완료여부')).upper() in ('O','○','완료') else '미완료','Unit':text(detail.get('Unit명')),'내용':text(detail.get('불합리 및 이슈 내용')),'담당자':text(detail.get('담당자')),'목표일':text(detail.get('목표일 원문')),'발생일':text(detail.get('발생일')),'원인':text(detail.get('사유 or 원인')),'진행 사항':text(detail.get('진행 사항',detail.get('진행 사항 (미팅내용)'))),'조치내용':text(detail.get('조치내용')),'완료일':text(detail.get('완료일')),'조치자':text(detail.get('담당자(조치자)')),'45호기 적용 여부':text(detail.get('45호기 적용 여부')),'시트':detail.get('시트',''),**{key:text(detail.get(key)) for key in ['개선 Item','상세 내용','원본 상태','진척도','비고','관련 메모']}})
    from classic_cloud.customer_requests import customer_rows
    rows.extend(customer_rows(previews, COLS))
    frame=pd.DataFrame(rows,columns=COLS)
    # Preserve original worksheet names and internal IDs; rename only 6G display categories.
    main=frame['범위'].eq('주요 5개 분야')
    frame.loc[main,'분야']=frame.loc[main,'분야'].replace({'HW(설계)':'설계','H/W':'설계','기타':'생기','S/W':'SW'})
    frame['목표일']=frame['목표일'].map(display_target_date)
    return frame


def filter_pending(frame, scope='주요 5개 분야', equipment=(), categories=(), states=(), query=''):
    result=frame.copy()
    scope={'주요 Pending':'주요 5개 분야','주요 펜딩':'주요 5개 분야','전체':'전체 시트'}.get(scope,scope)
    if scope!='전체 시트':result=result[result['범위']==scope]
    for field,values in [('설비',equipment),('분야',categories),('상태',states)]:
        if values:result=result[result[field].isin(values)]
    for term in query.split():
        if result.empty:break
        result=result[result.astype(str).agg(' '.join,axis=1).str.contains(term,case=False,regex=False)]
    return result


def summary(frame, group):
    if frame.empty:return pd.DataFrame(columns=[group,'완료','미완료','전체','완료율(%)'])
    grouped=pd.crosstab(frame[group],frame['상태']).reindex(columns=['완료','미완료','확인 필요'],fill_value=0)
    grouped['전체']=grouped.sum(axis=1);grouped['완료율(%)']=(grouped['완료']/grouped['전체']*100).round(1)
    return grouped.reset_index()


def deadlines(frame, today):
    counts={'기한초과':0,'임박':0,'여유':0};unresolved=0
    for row in frame.to_dict('records'):
        if row['상태']!='미완료':continue
        value=row['목표일']
        # Preview date cells are ISO datetime strings; retain raw text elsewhere.
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}[ T]00:00:00',value):value=value[:10]
        normalized,_=target_date(value)
        if not normalized:unresolved+=1;continue
        days=(date.fromisoformat(normalized)-today).days
        counts['기한초과' if days<0 else '임박' if days<=7 else '여유']+=1
    return counts,unresolved


def revision(snapshot):
    previews=snapshot.get('previews',{})
    name=next((n for n in previews if re.sub(r'\s','',n).lower()=='rev관리'),None)
    if not name:return {'history':[],'summary':[],'title':'','line':'','process':''}
    rows=previews[name]['rows']
    def val(r,c):return text(rows[r-1][c-1]) if r<=len(rows) and c<=len(rows[r-1]) else ''
    totals=[]
    for c in (2,4,6,8,10,12,14):
        if not val(5,c):continue
        rate=val(8,c+1)
        try:rate=f'{float(rate)*100:.1f}%'
        except ValueError:pass
        totals.append({'구분':val(5,c),'총 건수':val(7,c),'조치 건수':val(7,c+1),'조치율':rate or '—'})
    fields=['REV','구분','주요 변경내용','변경일자','작성자','변경점 Key Word / 비고']
    history=[dict(zip(fields,[val(r,c) for c in (2,3,4,10,11,12)])) for r in range(11,len(rows)+1) if re.fullmatch(r'\d+(?:\.0)?',val(r,2)) and val(r,4)]
    return {'title':val(2,4),'line':val(2,13),'process':val(3,13),'summary':totals,'history':history}


def workbook_export(tables):
    book=Workbook();book.remove(book.active)
    for name,frame in tables.items():
        sheet=book.create_sheet(name[:31]);sheet.append([str(c) for c in frame.columns])
        for row in frame.itertuples(index=False,name=None):
            sheet.append([None if pd.isna(v) else v for v in row])
        for row in sheet:
            for cell in row:
                if isinstance(cell.value,str):cell.data_type='s'
                cell.alignment=Alignment(vertical='top',wrap_text=True)
        for cell in sheet[1]:cell.font=Font(bold=True);cell.fill=PatternFill('solid',fgColor='CBD5E1')
        for i,column in enumerate(frame.columns,1):
            letter=sheet.cell(1,i).column_letter
            sheet.column_dimensions[letter].width=65 if str(column) in ('내용','주요 변경내용','변경점 Key Word / 비고') else 22
        sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
        sheet.sheet_view.zoomScale=85
        sheet.sheet_properties.pageSetUpPr.fitToPage=True
        sheet.page_setup.orientation='landscape';sheet.page_setup.fitToWidth=1;sheet.page_setup.fitToHeight=0
    output=BytesIO();book.save(output);return output.getvalue()

