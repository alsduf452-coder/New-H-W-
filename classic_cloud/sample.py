"""Synthetic preview only. No production data or identifiers."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def snapshots():
    today=datetime.now(ZoneInfo('Asia/Seoul')).date()
    details=[]
    for i,(category,state) in enumerate([('HW(설계)','X'),('SW','O'),('공정','X')],1):
        details.append({'ID':f'DEMO-{i}','시트':category,'No.':i,'호기':'DEMO-01' if i<3 else 'DEMO-02','완료여부':state,'Unit명':'샘플 Unit','불합리 및 이슈 내용':f'샘플 점검 항목 {i}','담당자':'샘플 담당자','목표일 원문':(today+timedelta(days=i*3-5)).isoformat(),'발생일':today.isoformat(),'조치내용':'샘플 조치','진행 사항':'샘플 확인'})
    rev=[['']*15 for _ in range(12)]
    rev[1][3]='샘플 REV 관리';rev[1][12]='DEMO LINE';rev[2][12]='DEMO PROCESS'
    rev[4][1]='Total';rev[6][1]='3';rev[6][2]='1';rev[7][2]=str(1/3)
    for c,v in zip([1,2,3,9,10,11],['001','공정','샘플 변경내용',today.isoformat(),'샘플 작성자','시연용 데이터']):rev[10][c]=v
    parts=['Diffuser','Backing Plate','Susceptor','Shadow Frame','RFG','Matcher','RPSC Reactor','Generator']
    history=[];installed={};measurements=[]
    for index,chamber in enumerate('ABCDE'):
        serials={part:f'DEMO-{chamber}-{i}' for i,part in enumerate(parts,1)}
        history.append({'chamber':chamber,'date':today.isoformat(),'reason':'가상 초기 설정','parts':serials,'source_row':index+4})
        installed[chamber]={part:{'sn':sn,'date':today.isoformat()} for part,sn in serials.items()}
        for kind in ['Spacing','Diffuser Flatness','Susceptor Flatness']:
            spacing=kind=='Spacing';grid=[[880+i*2+j+index for j in range(3)] for i in range(3)] if spacing else [[-(i*3+j+index) for j in range(7)] for i in range(5)]
            values=[v for row in grid for v in row]
            measurements.append({'id':f'DEMO-{kind}-{chamber}','kind':kind,'chamber':chamber,'date':today.isoformat(),'reason':'가상 측정','diffuser_sn':serials['Diffuser'],'susceptor_sn':serials['Susceptor'],'grid':grid,'center':grid[1][1] if spacing else grid[2][3],'count':len(values),'total':len(values),'min':min(values),'max':max(values),'range':max(values)-min(values),'source_row':index,'source_sheet':'가상 샘플','cells':[]})
    state={'received_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat()}
    return {'pending':{'revision':1,'state':{**state,'pending_status':'applied'},'previews':{'__pending_data__':{'details':details,'warnings':[]},'Rev 관리':{'rows':rev,'truncated':False}}},'hw':{'revision':1,'state':{**state,'mode':'hw'},'previews':{'__hw_data__':{'history':history,'installed':installed,'measurements':measurements,'parts':parts,'warnings':[]}}}}
