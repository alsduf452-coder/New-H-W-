# 자체 아이디·비밀번호 로그인

Microsoft/Google 앱 등록 없이 사용하는 관리자 등록 계정 방식입니다. 원본 데이터는 기존 PostgreSQL을 그대로 사용합니다. 회원가입·비밀번호 이메일 재설정 기능은 없습니다.

## 1. PC에서 계정 설정 생성

GitHub에서 최신 ZIP을 받아 압축을 풉니다. 프로젝트 최상위 폴더(create_login.py가 있는 곳)의 PowerShell에서 실행하세요. 추가 라이브러리 설치는 필요하지 않습니다.

```powershell
py -3.12 .\create_login.py
```

아이디와 새 비밀번호를 두 번 입력합니다. 비밀번호는 4~256자이며 화면에 표시되지 않습니다. 기존 Render SYNC_TOKEN과는 별개입니다. `login-secrets.generated.toml` 파일이 생성됩니다. 파일에는 비밀번호 원문이 아닌 임의 salt와 PBKDF2-SHA256 600,000회 해시가 기록됩니다. 생성 파일도 GitHub나 채팅에 올리지 않습니다.

## 2. Streamlit Secrets 설정

Streamlit Cloud에서 앱 Settings → Secrets를 엽니다. `.streamlit/secrets.password.example.toml`을 참고해 아래를 설정합니다.

```toml
[storage]
mode = "postgres"

[database]
url = "여기에 Render PostgreSQL의 External Database URL"

[local_excel]
source_id = "local-excel"
```

이 아래에 생성된 `login-secrets.generated.toml` 내용을 그대로 붙여넣습니다. 기존 Google/Microsoft용 `[auth]`, `[access]` 설정은 제거해도 됩니다. 같은 이름의 TOML 섹션을 중복 작성하지 않습니다. DB 주소는 Excel 수신 서버와 같은 DB의 **External Database URL**이어야 합니다. 비밀번호의 URL 특수문자는 제공된 연결 문자열 그대로 유지합니다.

저장하고 앱을 재시작한 뒤 만든 아이디와 비밀번호로 로그인합니다. `로컬 Excel 연동`에서 마지막 수신 시각과 H/W 측정 기록을 확인합니다. 앱 기본 주소는 그대로이며 `/oauth2callback`을 등록할 필요가 없습니다. Render의 SYNC_TOKEN, PC의 Excel 경로 및 동기화 프로그램 설정은 변경하지 않습니다.

## 계정 관리

- `[local_auth.users.아이디]` 항목을 추가하면 여러 계정을 사용할 수 있습니다. 아이디는 영문 소문자·숫자·밑줄·하이픈 3~64자입니다.
- `role = "editor"`는 PENDING 편집/가져오기, `role = "viewer"`는 조회/다운로드 권한입니다. H/W 화면은 둘 다 조회 전용입니다.
- 비밀번호 변경은 새 해시를 생성하여 해당 계정 password_hash를 바꾸고 재시작합니다. 계정 삭제 또는 해시·권한 변경 시 기존 세션도 다음 검증 시 종료됩니다.
- 생성 파일이 이미 있으면 덮어쓰지 않습니다. 기존 생성 파일을 다른 안전한 곳에 보관하거나 삭제한 뒤 새로 생성하세요.
- 비밀번호 분실 시 Secrets를 관리하는 사람이 해시를 재설정합니다. 기본 계정/기본 비밀번호는 제공하지 않습니다.

## 세션과 로그인 제한

로그인 세션은 서버 측 Streamlit session_state에서만 유지하며 최대 8시간 후 만료됩니다. 별도 로그인 쿠키를 만들지 않으며 새로고침/연결 종료로 재로그인이 필요할 수 있습니다. 자동 갱신 화면에서도 데이터를 읽기 전에 계정·만료를 확인합니다. 로그아웃하면 해당 세션의 편집 입력과 미리보기 캐시도 지웁니다.

계정별 15분 동안 5회 시도 제한(로그인 성공 시 해당 계정 초기화), 프로세스 전체 15분 동안 100회 제한을 적용합니다. 존재하지 않는 아이디의 시도는 하나로 합칩니다. 제한은 브라우저 간 공유되지만 서버 프로세스 재시작 시 초기화됩니다. 여러 서버 인스턴스 간 분산 제한·MFA는 포함하지 않습니다. Streamlit Cloud의 HTTPS 주소로 접속하세요.
