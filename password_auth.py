"""Local account password hashing and bounded, process-wide login throttling."""
from collections.abc import Mapping
import hashlib
import hmac
import re
import secrets
import threading
import time

ITERATIONS = 600_000
SESSION_SECONDS = 8 * 60 * 60


def hash_password(password):
    if not 12 <= len(password) <= 256:
        raise ValueError('비밀번호는 12~256자로 설정해주세요.')
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}'


def valid_hash(encoded):
    return isinstance(encoded, str) and bool(re.fullmatch(r'pbkdf2_sha256\$600000\$[0-9a-f]{32}\$[0-9a-f]{64}', encoded))


def verify_password(password, encoded):
    if not isinstance(password, str) or len(password) > 256 or not valid_hash(encoded):
        return False
    _, iterations, salt, expected = encoded.split('$')
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    return hmac.compare_digest(actual, expected)


def accounts(settings):
    users = settings.get('local_auth', {}).get('users', {})
    if not users or not isinstance(users, Mapping):
        raise ValueError('허용 계정 설정이 없습니다. 자체 로그인 안내를 확인해주세요.')
    for username, account in users.items():
        if not re.fullmatch(r'[a-z0-9_-]{3,64}', username) or not isinstance(account, Mapping) or not valid_hash(account.get('password_hash')) or account.get('role') not in ('editor', 'viewer'):
            raise ValueError('허용 계정의 아이디·비밀번호 해시·권한 설정을 확인해주세요.')
    return users


def fingerprint(account):
    return hashlib.sha256((account['password_hash'] + ':' + account['role']).encode()).hexdigest()


def identity(ticket, users, now=None):
    now = time.time() if now is None else now
    if not isinstance(ticket, dict):
        return None
    account = users.get(ticket.get('username'))
    if not account or not isinstance(ticket.get('expires'), (int, float)) or ticket['expires'] <= now or ticket.get('fingerprint') != fingerprint(account):
        return None
    return ticket['username'], account['role']


class LoginLimiter:
    """Shared across browser sessions. Limits reset on app process restart."""
    def __init__(self):
        self.lock = threading.Lock()
        self.attempts = {}

    def reserve(self, username, now=None):
        now = time.time() if now is None else now
        with self.lock:
            self.attempts = {k:[v for v in values if v > now-900] for k,values in self.attempts.items() if any(v > now-900 for v in values)}
            local = self.attempts.setdefault(username, [])
            total = self.attempts.setdefault('*', [])
            if len(local) >= 5 or len(total) >= 100:
                return False
            local.append(now);total.append(now)
            return True

    def success(self, username):
        with self.lock:
            self.attempts.pop(username, None)
