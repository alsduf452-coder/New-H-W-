"""Watch one local workbook and push stable changes over authenticated HTTPS."""
import argparse
import getpass
import hashlib
import os
from pathlib import Path
import time
import tomllib
from urllib.parse import urlparse
import requests

MAX_FILE = 20 * 1024 * 1024


class SyncError(ValueError):
    pass


def load_config(path):
    with open(path, 'rb') as file:
        config = tomllib.load(file)
    url = config.get('server_url', '').rstrip('/')
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise SyncError('server_url은 인증 정보가 없는 HTTPS 수신 서버 기본 주소여야 합니다.')
    excel = Path(config.get('excel_path', '')).expanduser()
    if not excel.is_absolute() or excel.suffix.lower() != '.xlsx' or excel.name.startswith('~$'):
        raise SyncError('excel_path에 실제 .xlsx 파일의 절대 경로를 입력해주세요.')
    interval = int(config.get('poll_seconds', 30))
    if not 10 <= interval <= 3600:
        raise SyncError('poll_seconds는 10~3600초로 설정해주세요.')
    return {'server_url': url, 'excel_path': excel, 'poll_seconds': interval}


def stable_read(path, settle_seconds=2):
    try:
        before = path.stat()
        if before.st_size > MAX_FILE:
            raise SyncError('파일이 20MB를 초과합니다.')
        time.sleep(settle_seconds)
        settled = path.stat()
        signature = lambda s: (s.st_size, s.st_mtime_ns, s.st_ino)
        if signature(before) != signature(settled):
            raise SyncError('파일 저장 중입니다. 다음 확인 시 다시 읽습니다.')
        with path.open('rb') as file:
            content = file.read(MAX_FILE + 1)
        after = path.stat()
        if len(content) > MAX_FILE or len(content) != before.st_size or signature(before) != signature(after):
            raise SyncError('파일 저장 중입니다. 다음 확인 시 다시 읽습니다.')
        return content
    except OSError:
        raise SyncError('파일을 읽지 못했습니다. 경로 또는 파일 사용 상태를 확인해주세요.') from None


def check_response(response):
    if response.status_code == 401:
        raise SyncError('동기화 토큰이 올바르지 않습니다.')
    if response.status_code == 409:
        raise SyncError('다른 전송이 먼저 반영됐습니다. 다음 확인 시 다시 시도합니다.')
    if response.status_code != 200:
        raise SyncError(f'서버 응답 오류({response.status_code}). 앱의 연결 상태와 서버 설정을 확인해주세요.')
    try:
        return response.json()
    except ValueError:
        raise SyncError('수신 서버 주소와 응답을 확인해주세요.') from None


def sync_once(config, token, session=None, settle_seconds=2):
    session = session or requests.Session()
    headers = {'Authorization': 'Bearer ' + token}
    try:
        status = check_response(session.get(config['server_url'] + '/v1/source/status', headers=headers, timeout=(10, 60), allow_redirects=False))
        content = stable_read(config['excel_path'], settle_seconds)
        digest = hashlib.sha256(content).hexdigest()
        if status.get('file_hash') == digest and not status.get('resend_required'):
            return '변경 없음' if status.get('pending_status') == 'applied' else '시트 전송 완료 · PENDING 열 연결 설정 필요'
        headers.update({'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'If-Match': str(status['revision']), 'X-Content-SHA256': digest})
        response = session.post(config['server_url'] + '/v1/source/workbook', headers=headers, data=content, timeout=(10, 120), allow_redirects=False)
        result = check_response(response)
        state = result.get('pending_status')
        if state == 'conflict':
            return '시트 전송 완료 · PENDING 충돌로 반영 보류 (앱에서 확인)'
        if state == 'mapping_required':
            return '시트 전송 완료 · PENDING 열 연결 설정 필요 (앱에서 확인)'
        return f"전송 완료 · PENDING 변경 {result.get('changed', 0)}건 반영"
    except requests.RequestException:
        raise SyncError('서버에 연결하지 못했습니다. 인터넷·서버 주소·인증서를 확인해주세요. 다음 확인 시 재시도합니다.') from None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=str(Path(__file__).with_name('config.toml')))
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    try:
        config = load_config(args.config)
    except (OSError, ValueError):
        print('config.toml을 확인해주세요. config.example.toml을 복사하여 파일 경로와 HTTPS 서버 주소를 설정합니다.')
        return 1
    token = os.environ.get('LOCAL_SYNC_TOKEN') or getpass.getpass('동기화 토큰 (입력 내용은 표시되지 않음): ')
    if not token or any(c.isspace() for c in token):
        print('동기화 토큰을 확인해주세요.'); return 1
    print('지정한 Excel 한 개를 감시합니다. 종료: Ctrl+C. 원본 Excel은 수정하지 않습니다.')
    with requests.Session() as session:
        while True:
            try:
                message = sync_once(config, token, session)
                code = 0
            except SyncError as exc:
                message = str(exc); code = 1
            except (KeyError, TypeError, ValueError):
                message = '설정 또는 서버 응답 형식을 확인해주세요.'; code = 1
            print(time.strftime('%Y-%m-%d %H:%M:%S'), message, flush=True)
            if args.once:
                return code
            time.sleep(config['poll_seconds'])


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\n동기화를 종료했습니다.')
