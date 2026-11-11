# 창 없는 동기화 및 대화 연결 준비

## PC: 한 번만 설정

최신 classic-cloud local_sync 파일을 기존 local_sync에 복사합니다. config.toml, token.dpapi,
schedule.json, daily-state는 기존 것을 보존합니다.
반드시 .venv와 token.dpapi가 있는 local_sync 폴더의 enable_background.bat를 실행합니다.
기존 두 예약 작업이 있어야 합니다. 이 설치는 기존 작업의 실행 프로그램만 pythonw.exe로 바꾸고
수동 요청 작업을 활성화합니다. 트리거/로그인 사용자/09:00 시각은 유지합니다.
예약 일시정지/부재/당일 실패 마커는 변경하지 않습니다. 실패 마커가 있으면 당일 요청 확인이
중단된 상태이므로 로그와 원인을 먼저 확인해야 합니다. 새 작업이나 중복 상시 감시기를 만들지 않습니다.

앱의 Excel 동기화 요청 버튼을 누르고 1분 정도 후 상태를 확인합니다.
PC 로그인과 Q: 접근이 필요합니다. 원본 Excel을 저장한 뒤 요청하세요.
수동 상태 로그: daily-state/YYYY-MM.log, 런처 로그: daily-state/launcher.log.
로그에 토큰이나 원본 예외 메시지를 남기지 않습니다.

Windows Task Scheduler → Actions에서 pythonw.exe가 실행 프로그램인지 확인합니다.
본 변경의 Windows 실행은 실제 PC에서 검증해야 합니다. Linux 테스트는 프로세스 인자,
CREATE_NO_WINDOW 플래그, 종료 코드 전파, API/큐 동작을 검증합니다.

## 서버: 선택 기능, 기본 비활성화

기존 SYNC_SOURCES_JSON은 변경할 필요가 없습니다.
Render hw-excel-sync-classic에 별도 SYNC_CONTROL_TOKEN을 설정하고 최신 코드를 배포하면 활성화됩니다.
토큰은 secrets.token_urlsafe(32) 등으로 로컬에서 생성하며 기존 SYNC_TOKEN과 달라야 합니다.
토큰을 채팅, GitHub, URL 쿼리에 넣지 마세요. Render 환경 변수와 연결 클라이언트의 보안 자격 증명란에만 보관합니다.

- POST /v1/control/sync: 동기화 요청 등록(완료 의미가 아님)
- GET /v1/control/sync?request_id=...: 해당 요청의 현재 상태 확인
- POST /mcp: stateless Streamable HTTP JSON-RPC
- Authorization: Bearer <SYNC_CONTROL_TOKEN>

MCP 도구: request_excel_sync, get_excel_sync_status.
이 토큰은 업로드, PC 작업 claim/result, DB 편집, 임의 명령 실행 권한이 없습니다.
기존 SYNC_TOKEN으로 제어 API에 접근할 수 없습니다.
진행 중 요청은 합쳐지며 PC의 부재/일시정지 정책을 우회하지 않습니다.

## ChatGPT 연결 제한

서버 배포만으로 ChatGPT에 도구가 생기지 않습니다. 사용 중인 클라이언트에서 사용자 지정
MCP 연결과 인증된 Bearer 헤더를 지원해야 합니다. 이 어댑터는 OAuth 서버가 아니므로
OAuth만 지원하는 연결 UI에서는 별도의 OAuth 인증 연동이 필요합니다.
인증 없는 공개 MCP로 전환하거나 토큰을 URL에 넣어 해결하지 마세요.
도구가 실제 대화에 나타나기 전에는 대화로 동기화할 수 있다고 안내하지 않습니다.
Render 관리 플러그인은 배포/로그 확인을 도울 수 있지만 사용자 정의 동기화 도구를 자동으로 추가하지 않습니다.

도구 연결 후 사용자가 명시적으로 요청할 때만 request_excel_sync를 호출하고,
반환 request_id로 get_excel_sync_status를 조회합니다. pending/running을 완료로 보고하지 않습니다.
다른 요청으로 교체되면 superseded이며 이전 요청 완료 여부를 추측하지 않습니다.
