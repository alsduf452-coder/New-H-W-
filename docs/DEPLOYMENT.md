# 운영 연결 안내

Cloud-04는 샘플 체험과 운영 연결을 분리합니다. 샘플 실행은 바로 가능하지만 실제 DB·로그인 제공자 연결은 운영 계정에서 설정하고 검증해야 합니다.

**Google/Microsoft 없이 시작하려면 [자체 로그인 설정](PASSWORD_LOGIN.md)을 사용하세요.** 아래 2~4번은 OIDC를 선택하는 경우의 절차입니다. 자체 로그인에서는 `.streamlit/secrets.password.example.toml`과 생성된 계정 해시를 사용합니다.

1. 회사에서 사용 가능한 PostgreSQL을 준비합니다. 앱 전용 DB 계정에 해당 DB의 테이블 생성·조회·추가·수정 권한을 부여합니다. 연결은 SSL을 사용합니다.
2. 회사 Microsoft Entra ID 등 OIDC 제공자에서 웹 앱을 등록합니다. callback 주소는 배포된 앱 주소의 `/oauth2callback`입니다. 클라이언트 ID, 비밀키, 제공자 metadata URL을 확인합니다. 로그인 응답에 `email`이 제공되어야 합니다.
3. Streamlit Cloud 앱 설정의 Secrets에 `.streamlit/secrets.example.toml`을 참고하여 실제 값을 입력합니다. 예시 비밀번호나 주소를 그대로 사용하지 마세요. `cookie_secret`은 충분히 긴 무작위 값으로 생성합니다.
4. `allowed_emails`에는 접근 가능한 계정, `editor_emails`에는 편집 가능한 계정을 입력합니다. 편집 계정도 allowed_emails에 있어야 합니다.
5. 앱을 재시작하고 허용되지 않은 계정 차단, 조회 계정의 편집 차단, 편집 계정의 등록·수정·Excel 반영을 확인합니다.
6. 두 편집 계정으로 같은 항목을 수정하여 오래된 변경이 차단되는지 확인합니다. 앱 재시작 후 데이터가 유지되는지도 확인합니다.
7. DB 제공자의 자동 백업과 복원 정책을 설정하고 복원 시험을 수행합니다. Excel 내보내기는 PENDING 현재 값이며 변경 이력을 포함한 전체 DB 백업을 대신하지 않습니다.

앱은 최초 접속 시 `cloud_pending_items`, `cloud_pending_events` 테이블을 생성합니다. 기존 업무 DB와 별도 DB를 사용하는 것을 권장합니다. 운영 데이터는 GitHub나 Streamlit 서버의 로컬 파일에 저장하지 않습니다.

PC 로컬 Excel 연결은 [로컬 Excel 안내](LOCAL_EXCEL.md)에 따라 별도 HTTPS 수신 서버와 PC 동기화 프로그램을 설정합니다. 앱과 수신 서버는 같은 PostgreSQL을 사용합니다. 샘플 모드는 실제 파일 연결에 사용할 수 없습니다.
