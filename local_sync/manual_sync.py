"""Check once for an app request. Scheduler runs this each minute."""
from pathlib import Path
from datetime import datetime,date
import json
import os
import requests
from agent import load_config,sync_once,check_response,SyncError
from sync_lock import sync_lock

ROOT=Path(__file__).resolve().parent


def permitted(settings,today):
    if settings.get('paused',False):return False
    for period in settings.get('absence',[]):
        start=date.fromisoformat(period['start']);end=date.fromisoformat(period['end'])
        if end<start:raise ValueError('Invalid absence period')
        if start<=today<=end:return False
    return True


def run(root=ROOT,now=None,sync=sync_once,session_factory=requests.Session):
    now=now or datetime.now()
    state=root/'daily-state';state.mkdir(exist_ok=True)
    failed=state/(now.date().isoformat()+'.manual-failed')
    if failed.exists():return 0
    def log(message):
        with (state/(now.strftime('%Y-%m')+'.log')).open('a',encoding='utf-8') as f:f.write(now.isoformat(timespec='seconds')+' 수동 · '+message+'\n')
    try:
        settings=json.loads((root/'schedule.json').read_text(encoding='utf-8-sig'))
        if not permitted(settings,now.date()):return 0
        config=load_config(root/'config.toml');token=os.environ.get('LOCAL_SYNC_TOKEN','')
        if not token or any(c.isspace() for c in token):raise ValueError()
    except (OSError,ValueError,KeyError,TypeError):
        failed.touch();log('설정 오류 · 당일 요청 확인 중단');return 1
    with sync_lock(root) as locked:
        if not locked:return 0
        headers={'Authorization':'Bearer '+token}
        with session_factory() as session:
            try:
                response=session.post(config['server_url']+'/v1/manual/claim',headers=headers,timeout=(10,60),allow_redirects=False)
                request=check_response(response).get('request')
                if not request:return 0
                status='done';messages=[]
                # Recheck absence after claim before reading any Excel files.
                settings=json.loads((root/'schedule.json').read_text(encoding='utf-8-sig'))
                if not permitted(settings,now.date()):
                    status='blocked';messages=['부재 또는 일시정지로 전송하지 않았습니다.']
                else:
                    jobs=[('45호기',config)]
                    if config.get('pending_excel_path'):jobs.append(('PENDING',{**config,'excel_path':config['pending_excel_path'],'source_id':config['pending_source_id']}))
                    if config.get('hw15_excel_path'):jobs.append(('15호기',{**config,'excel_path':config['hw15_excel_path'],'source_id':config['hw15_source_id']}))
                    if config.get('pending8_excel_path'):jobs.append(('8G PENDING',{**config,'excel_path':config['pending8_excel_path'],'source_id':config['pending8_source_id']}))
                    if config.get('hw86_excel_path'):jobs.append(('8.6G H/W',{**config,'excel_path':config['hw86_excel_path'],'source_id':config['hw86_source_id']}))
                    if config.get('process15_excel_path'):jobs.append(('15호기 공정 Map',{**config,'excel_path':config['process15_excel_path'],'source_id':config['process15_source_id']}))
                    for label,job in jobs:
                        try:
                            message=sync(job,token,session)
                            messages.append(label+': '+message)
                            if '충돌' in message or '설정 필요' in message:
                                status='failed';failed.touch();break
                        except (SyncError,OSError,ValueError,KeyError,TypeError):
                            status='failed';failed.touch();messages.append(label+': 전송 실패. 남은 파일 중단 · 당일 재시도 없음');break
                summary=' / '.join(messages)[:500]
                check_response(session.post(config['server_url']+'/v1/manual/result',headers=headers,json={'request_id':request['request_id'],'status':status,'summary':summary},timeout=(10,60),allow_redirects=False))
                log(summary)
                return 1 if status=='failed' else 0
            except (requests.RequestException,SyncError,OSError,ValueError,KeyError,TypeError):
                failed.touch();log('서버 연결 또는 응답 오류 · 당일 요청 확인 중단');return 1


if __name__=='__main__':raise SystemExit(run())

