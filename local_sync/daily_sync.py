"""One scheduled attempt per local calendar day; never prompt or retry."""
import json
import time
import os
from datetime import datetime, date
from pathlib import Path
import requests
from agent import load_config, sync_once, SyncError
from sync_lock import sync_lock

ROOT = Path(__file__).resolve().parent


def eligible(settings, now):
    if settings.get('paused', False):return False, '일시정지'
    # A late login or delayed task must not cause a catch-up transfer.
    if (now.hour, now.minute) != (9, 0):return False, '09:00 실행 시간이 아님'
    for period in settings.get('absence', []):
        start = date.fromisoformat(period['start'])
        end = date.fromisoformat(period['end'])
        if end < start:raise ValueError('부재 기간 오류')
        if start <= now.date() <= end:return False, '부재 기간'
    return True, ''


def _run(root=ROOT, now=None, sync=sync_once):
    now = now or datetime.now()
    state = root / 'daily-state'
    state.mkdir(exist_ok=True)
    def log(message):
        with (state / (now.strftime('%Y-%m')+'.log')).open('a',encoding='utf-8') as f:
            f.write(now.isoformat(timespec='seconds')+' '+message+'\n')
    try:
        settings = json.loads((root/'schedule.json').read_text(encoding='utf-8-sig'))
        allowed, reason = eligible(settings, now)
    except (OSError, ValueError, KeyError, TypeError):
        log('예약 설정 오류 · 전송하지 않음');return 1
    if not allowed:log('건너뜀 · '+reason);return 0
    # Exclusive creation also blocks concurrent launches and repeat runs after failure.
    try:
        with (state/(now.date().isoformat()+'.attempt')).open('x') as f:f.write(now.isoformat())
    except FileExistsError:
        log('오늘 이미 실행함 · 재시도하지 않음');return 0
    try:
        token = os.environ.get('LOCAL_SYNC_TOKEN','')
        if not token or any(c.isspace() for c in token):raise ValueError()
        config = load_config(root/'config.toml')
    except (OSError, ValueError):
        log('토큰 또는 파일 경로 설정 오류 · 당일 재시도하지 않음');return 1
    jobs = [('45호기 H/W',config)]
    if config.get('pending_excel_path'):
        jobs.append(('PENDING',{**config,'excel_path':config['pending_excel_path'],'source_id':config['pending_source_id']}))
    if config.get('hw15_excel_path'):
        jobs.append(('15호기 H/W',{**config,'excel_path':config['hw15_excel_path'],'source_id':config['hw15_source_id']}))
    with requests.Session() as session:
        for label,job in jobs:
            try:
                log(label+' · '+sync(job,token,session))
            except (SyncError,OSError,ValueError,KeyError,TypeError):
                log(label+' · 전송 실패 · 남은 파일 중단, 당일 재시도하지 않음');return 1
    log('예약 동기화 완료');return 0


def run(root=ROOT, now=None, sync=sync_once):
    started = now or datetime.now()
    state = root/'daily-state'
    state.mkdir(exist_ok=True)
    def note(message):
        with (state/(started.strftime('%Y-%m')+'.log')).open('a',encoding='utf-8') as f:
            f.write(datetime.now().isoformat(timespec='seconds')+' 자동 · '+message+'\n')
    note('예약 프로그램 시작')
    deadline = time.monotonic()+180
    waiting = False
    while True:
        with sync_lock(root) as locked:
            if locked:
                if waiting:note('다른 작업 종료 확인 · 자동 동기화 진행')
                # Eligibility uses scheduled launch time, not time after lock waiting.
                return _run(root,started,sync)
        if not waiting:
            note('다른 동기화 작업 실행 중 · 최대 3분 대기')
            waiting=True
        if time.monotonic()>=deadline:
            note('대기 시간 초과로 건너뜀 · 당일 자동 재시도 없음')
            return 1
        time.sleep(2)


if __name__=='__main__':
    raise SystemExit(run())
