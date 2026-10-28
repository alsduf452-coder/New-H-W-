"""Generate a private Streamlit Secrets account entry on the administrator's PC."""
import getpass
from pathlib import Path
import re
from password_auth import hash_password


def main():
    username = input('로그인 아이디 (영문 소문자/숫자/_/- 3~64자): ').strip().lower()
    if not re.fullmatch(r'[a-z0-9_-]{3,64}', username):
        raise ValueError('아이디 형식을 확인해주세요.')
    password = getpass.getpass('새 비밀번호 (4자 이상, 입력 내용 숨김): ')
    if password != getpass.getpass('비밀번호 다시 입력: '):
        raise ValueError('비밀번호가 일치하지 않습니다.')
    encoded = hash_password(password)
    out = Path(__file__).with_name('login-secrets.generated.toml')
    with out.open('x', encoding='utf-8') as file:
        file.write('[login]\nmethod = "password"\n\n[local_auth.users.' + username + ']\npassword_hash = "' + encoded + '"\nrole = "editor"\n')
    print('login-secrets.generated.toml을 생성했습니다. 내용을 Streamlit Secrets에 붙여넣으세요. GitHub나 채팅에 올리지 마세요.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, FileExistsError) as exc:
        print('설정 파일이 이미 있습니다. 기존 파일을 보관/삭제 후 다시 실행하세요.' if isinstance(exc, FileExistsError) else str(exc))
        raise SystemExit(1)
