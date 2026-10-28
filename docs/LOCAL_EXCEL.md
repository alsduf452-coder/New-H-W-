# 로컬 Excel → 클라우드 앱 연결

현재 앱이 샘플 모드라면 아래 1~3번 서버 설정을 먼저 완료해야 합니다. GitHub 코드 업데이트만으로 PC의 파일이나 실제 데이터가 연결되지는 않습니다.

구성: **PC의 지정 Excel → PC 동기화 프로그램 → HTTPS 수신 서버 → PostgreSQL → Streamlit 앱**.

## 1. 같은 데이터를 저장할 PostgreSQL 준비

회사에서 사용할 수 있는 PostgreSQL 또는 관리형 PostgreSQL을 준비합니다. SSL 연결이 가능한 연결 문자열을 확인합니다. 앱과 수신 서버는 같은 DB를 사용해야 합니다. 이 버전은 앱 전용 DB와 테이블 생성 권한이 필요합니다. DB 제공자의 백업·복원 설정도 구성합니다.

DB 비밀번호, 토큰, 원본 Excel은 GitHub나 채팅에 올리지 않습니다. Secrets/환경변수 설정 화면에 입력합니다.

## 2. Excel 수신 서버 배포

Streamlit Cloud는 화면 실행용입니다. 파일 수신 API는 별도 Python 웹 서비스로 배포합니다. 예를 들어 Render의 Web Service에서 이 GitHub 저장소를 연결하여 다음처럼 설정할 수 있습니다. 서버 제공자와 요금제는 사용 환경에 맞게 선택하세요.

| 항목 | 값 |
|---|---|
| 저장소 | `alsduf452-coder/New-H-W-` |
| 브랜치 | `main` |
| Python | 3.12 |
| Build command | `pip install -r requirements-sync.txt` |
| Start command | `uvicorn sync_api:create_app --factory --host 0.0.0.0 --port $PORT --no-access-log` |
| Health check | `/healthz` |

환경변수는 `sync.env.example`을 참고합니다.

- `DATABASE_URL`: PostgreSQL 연결 문자열. Streamlit 앱의 DB와 동일합니다.
- `SYNC_TOKEN`: PC 프로그램용 전용 토큰. PC에서 `py -3.12 -c "import secrets; print(secrets.token_urlsafe(32))"`를 실행해 생성한 값을 서버 환경변수에 입력합니다. 이 값은 생성하는 사용자에게만 표시되며 채팅으로 보낼 필요가 없습니다.
- `SYNC_SOURCE_ID`: `local-excel`. 서버 하나에서 파일 하나를 연결합니다. 같은 토큰을 여러 PC에서 같은 파일의 서로 다른 복사본에 사용하는 구성은 지원하지 않습니다.
- `SYNC_MAPPING_JSON`: 아래 열 연결 설정. 기본값 `{}`는 시트 `PENDING`, 머리글 1행, 앱과 같은 열 이름을 사용합니다.

배포 후 `https://수신서버주소/healthz`가 `{"status":"ok"}`를 반환하는지 확인합니다. PC 설정에는 이 수신 서버의 HTTPS 기본 주소를 입력합니다. Streamlit 앱 주소를 입력하면 동작하지 않습니다.

## 3. Streamlit 앱 운영 모드로 전환

외부 계정 없이 자체 아이디·비밀번호로 로그인하려면 [자체 로그인 안내](PASSWORD_LOGIN.md)를 사용하세요. 아래 OIDC 등록 절차는 생략할 수 있습니다.

Streamlit Cloud의 Secrets에 `.streamlit/secrets.example.toml`을 참고하여 PostgreSQL, OIDC 로그인, 허용 계정을 설정합니다. `[local_excel] source_id = "local-excel"`은 수신 서버와 같게 설정합니다.

OIDC는 Microsoft Entra ID 또는 Google 등 사용 가능한 제공자를 선택할 수 있습니다. Google을 사용하는 경우 metadata URL은 `https://accounts.google.com/.well-known/openid-configuration`이며, Google Cloud에서 웹 OAuth 클라이언트를 등록하고 배포된 앱의 `/oauth2callback`을 승인된 리디렉션 URI로 지정합니다. 회사 계정 정책에 맞는 제공자를 사용하세요. 앱은 로그인 응답의 `email`이 allowed_emails에 있는지 확인합니다.

실제 DB가 설정되지 않은 샘플 모드는 회사 데이터를 받지 않습니다. 수신 API는 별도의 토큰으로 인증하고, 앱의 조회·수정은 로그인 허용 계정으로 제한합니다. API의 토큰을 가진 PC는 지정 소스의 PENDING을 수정할 수 있으므로 토큰은 해당 PC에서만 사용합니다.

## 4. PC 설치 및 실행 (Windows)

1. GitHub 저장소에서 **Code → Download ZIP**으로 코드를 받고 압축을 풉니다.
2. 회사에서 사용 가능한 Python 3.12를 설치합니다. 설치 시 Python Launcher(`py`)를 포함합니다.
3. `local_sync/install.bat`을 실행합니다. PC 프로그램에는 requests 라이브러리만 설치합니다.
4. 생성된 `local_sync/config.toml`을 메모장으로 열어 `excel_path`와 `server_url`을 수정합니다. Windows 경로의 작은따옴표를 유지합니다.
5. `local_sync/start.bat`을 실행하고 서버에서 설정한 `SYNC_TOKEN`을 입력합니다. 입력 내용은 화면에 표시되지 않으며 파일로 저장하지 않습니다.
6. Excel을 수정하고 저장한 뒤, 프로그램 창의 `전송 완료`와 앱의 **로컬 Excel 연동** 화면을 확인합니다.

예시 설정:

```toml
excel_path = 'C:\EquipmentData\Pending.xlsx'
server_url = 'https://YOUR-SYNC-SERVER.example.com'
poll_seconds = 30
```

실제 파일은 회사에서 허용한 고정 폴더에 보관하세요. `AppData\Local\Temp`의 임시 파일은 이름이나 위치가 바뀌거나 삭제될 수 있습니다. 프로그램은 지정 파일 한 개만 읽으며 폴더 전체를 검색하지 않습니다. 파일 경로나 원본 파일명은 서버로 보내지 않습니다.

프로그램은 30초마다 확인하고, 저장 중인 파일은 잠시 기다린 뒤 읽습니다. 파일 내용이 같으면 본문을 재전송하지 않습니다. 변경 파일은 HTTPS로 전송하고, 실패하면 다음 확인 시 재시도합니다. 기본 동작은 창이 열려 있는 동안입니다. 창을 닫거나 PC가 꺼지면 전송이 멈추며 앱에는 마지막 데이터가 남습니다. 자동 시작 등록은 이 버전에서 수행하지 않습니다.

반복 실행 없이 한 번만 확인하려면 `local_sync` 폴더에서 `.venv\Scripts\python.exe agent.py --once`를 실행합니다. 선택적으로 `LOCAL_SYNC_TOKEN` 환경변수를 설정하면 실행 시 토큰 입력을 생략할 수 있습니다. 로그에는 파일 내용과 토큰을 출력하지 않습니다.

## 5. Excel 시트에 맞게 연결

**시트별 표:** 보이는 시트 이름을 탭으로 표시합니다. 화면 폭에 맞춰 표를 표시하며 열이 많으면 가로 스크롤을 제공합니다. 각 시트에서 머리글 행을 선택할 수 있습니다. Excel의 색·병합 셀·차트·인쇄 배율까지 복제하지는 않습니다. 수식은 Excel에 저장된 계산 결과를 표시하며 앱이 재계산하지 않습니다.

**PENDING 현황:** 실제 시트 이름, 머리글 행, 열 이름을 수신 서버 `SYNC_MAPPING_JSON`에 설정합니다. 예:

```json
{"pending_sheet":"Pending List","header_row":3,"columns":{"ID":"관리번호","설비":"설비명","분야":"분야","상태":"진행상태","내용":"조치내용","담당자":"담당자","목표일":"완료목표일"},"status_values":{"진행중":"미완료","종결":"완료"},"category_values":{"HW":"H/W","SW":"S/W"}}
```

- 필요한 필드: ID, 설비, 분야, 상태, 내용, 담당자, 목표일. 빈 목표일·담당자는 허용합니다.
- ID는 행 위치와 무관한 고유값을 유지합니다. 영문·숫자로 시작하는 80자 이하 값이며 콜론·밑줄·하이픈도 허용합니다. ID가 없으면 원본에 ID 열을 추가해야 합니다.
- 분야: H/W, S/W, 공정, 전장, 기타. 상태: 미완료, 완료. 다른 표현은 위처럼 연결합니다.
- 목표일: Excel 날짜 셀 또는 YYYY-MM-DD. PENDING 연결 열의 수식은 허용하지 않습니다.
- 표 머리글 선택은 미리보기용이며 PENDING 연결 규칙을 바꾸지 않습니다.
- 여러 시트를 합쳐 PENDING을 만드는 규칙은 아직 포함하지 않았습니다. 실제 파일 양식에 따라 추가 구현해야 합니다.

열이 없거나 잘못된 값이 있으면 시트는 보여주되 PENDING 반영을 보류하고 이유를 표시합니다. 설정을 변경해 수신 서버를 재시작하면 PC 프로그램이 같은 파일도 다시 전송합니다.

## 데이터 보호와 충돌 처리

Excel에서 행을 지워도 DB의 PENDING은 자동 삭제하지 않습니다. Excel만 바뀌면 자동 반영하고, 앱만 바뀌면 앱 값을 유지합니다. 같은 항목을 앱과 Excel 양쪽에서 서로 다르게 바꾸면 해당 파일의 PENDING 반영 전체를 보류합니다. 앱의 충돌 ID를 확인하여 양쪽 값을 일치시키면 다음 확인 때 다시 반영합니다. 시트 미리보기에는 수신한 최신 Excel 값이 표시되므로 충돌 중에는 PENDING 현황과 다를 수 있습니다.

원본 Excel에 앱의 변경을 다시 쓰지는 않습니다. 이 기능은 **Excel → 앱 단방향 연동**입니다. 최초 연결 시 DB에 같은 ID가 있으면서 값이 다르면 자동 덮어쓰지 않고 충돌로 처리합니다.

성공한 반영에는 `local-excel-sync` 변경자와 변경 전후 값이 기록됩니다. 실제 Excel 셀 편집자를 식별하지 않습니다. 전송·DB 실패 시 이전 데이터를 유지하며, 응답이 유실되어 재시도해도 성공한 동일 변경을 중복 기록하지 않습니다.

## 한도와 검증 범위

- 원본 .xlsx 전송 한도 20MB, 압축 해제 합계 40MB.
- 시트 미리보기: 시트당 앞 500행·50열, 전체 100,000셀, 셀당 최대 2,000자, 총 8MB. 한도 이후 시트는 생략될 수 있습니다.
- PENDING 반영: 5,000행, 200열 이내에서 지정 열 추출. 원본 .xlsx 파일 자체는 저장하지 않습니다.
- 앱은 15초마다 DB를 확인합니다. 일반적으로 파일 확인 주기와 화면 갱신 주기가 지난 후 변경이 보이며 네트워크·서버 기동에 따라 지연될 수 있습니다.
- 자동화 테스트는 샘플 파일, API 요청, 메모리 DB로 검증했습니다. 실제 Windows 실행, 운영 PostgreSQL 및 외부 HTTPS 배포는 사용자 환경 설정 후 확인해야 합니다.

## OCTA 설비 H/W 양식 연결 (Cloud-03)

`이력`, `Spacing`, `Diff Flatness`, `Susc Flatness` 시트가 있는 OCTA H/W 파일은 수신 서버의 `SYNC_MAPPING_JSON`을 아래 값으로 변경하고 재배포합니다.

```json
{"mode":"hw"}
```

PC 프로그램이 다음 확인 시 같은 파일도 다시 전송합니다. PC의 `local_sync/agent.py`도 최신 코드로 교체한 뒤 재실행하면 `H/W 전송 완료`로 안내합니다. 기존 PC 코드도 전송은 가능하지만 PENDING 관련 안내가 남을 수 있습니다. 기존 `config.toml`, 토큰과 Excel 파일은 보존합니다.

앱의 `로컬 Excel 연동` 화면에서 장착 부품, 작업·교체 이력, Spacing, Diffuser/Susceptor Flatness를 표시합니다. H/W 모드에서는 PENDING 항목을 만들거나 수정하지 않습니다. Streamlit도 최신 main을 배포하고, 기존 운영 DB·로그인 설정을 완료해야 볼 수 있습니다.

- 이력: B3:L3 머리글, A~E 챔버, 부품별 S/N. 병합된 변경이력 셀만 실제 병합 범위에 맞춰 공유합니다. 최신 부품 현황은 날짜와 원본 행 순서대로 산출합니다.
- Spacing: 각 Date 블록의 ①~⑨ 3×3 위치를 검증합니다. `고장` 등 비수치 값은 원문으로 남기고 통계에서 제외합니다.
- Flatness: 각 Date 블록의 5×7 표를 그대로 읽습니다. 음수 부호·0·빈칸을 유지하며 Center는 R3C4입니다. 초기 Susceptor의 Center 열 공란을 0으로 채우지 않습니다.
- 같은 날 여러 기록은 합치지 않습니다. 최신 요약은 같은 날일 때 아래쪽 기록을 선택하며 원본 행 번호로 구별할 수 있습니다.
- 원본의 이상값과 측정 오류 메모도 보존합니다. 코드에서 임의로 수치를 보정하지 않습니다. 측정표는 조회 전용이며 Excel을 수정·저장하면 다음 전송에서 교체됩니다.
- H/W 이력·측정값은 현재 Excel의 스냅샷입니다. Excel에서 측정 블록을 삭제하면 다음 수신 화면에서도 빠집니다. PENDING의 변경 이력과 달리 과거 H/W 파일 버전을 누적 보관하지 않으므로 Excel 버전 백업은 별도로 유지합니다.
- 부품/측정 블록 구조가 바뀌거나 날짜를 읽을 수 없으면 반영을 보류하고 기존 H/W 화면을 유지합니다.
- 원본 시트의 이미지로 삽입된 성적서·사진은 숫자 데이터로 자동 추출하지 않습니다. 기타 시트는 셀 값 미리보기만 제공합니다.

원본 업무 Excel이나 S/N 값은 공개 GitHub에 포함하지 않았습니다. 양식 해석 코드와 가상 데이터 테스트만 배포합니다.

## Cloud-05: H/W + 통합 PENDING 두 파일 동기화

기존 H/W의 SYNC_SOURCE_ID, SYNC_MAPPING_JSON, 토큰, DB는 그대로 유지합니다. Render 환경변수에 **SYNC_SOURCES_JSON**을 추가합니다.

```json
{"pending-excel":{"mode":"pending_octa"}}
```

수신 서버를 최신 코드로 배포합니다. PC는 최신 `local_sync/agent.py`를 교체하고 기존 `config.toml`에 아래 두 줄을 추가합니다. 이미 있는 excel_path, server_url, poll_seconds를 유지하세요.

```toml
pending_excel_path = 'C:\EquipmentData\Pending_List.xlsx'
pending_source_id = 'pending-excel'
```

경로는 실제 PENDING 파일의 절대 경로로 변경합니다. `start.bat`을 다시 실행하면 같은 토큰으로 두 파일을 각각 확인합니다. 한 파일에서 실패해도 다음 파일을 처리합니다. 파일당 20MB 제한입니다. 앱의 `로컬 Excel 연동 → 연동 파일`에서 H/W와 PENDING을 전환합니다. 기본 소스 ID를 쓰면 Streamlit Secrets 변경은 필요 없습니다. 다른 소스 ID를 쓸 경우 `[local_excel] pending_source_id`에도 같은 ID를 설정하세요.

통합 PENDING은 HW(설계), 공정, 전장, SW, 기타의 실제 항목 행을 읽습니다. Rev 관리의 요약 숫자나 수식값을 집계에 쓰지 않습니다. 고객사요청, software불합리, 설비알람 등 보조 시트는 미리보기만 제공하고 5개 분야 집계에는 포함하지 않습니다. 상태 O는 완료, X는 미완료로 반영합니다. 담당자는 원본 `담당자`를 사용하고 조치자는 원본 상세에 유지합니다.

ID는 소스 ID + 시트 + 설비 + No. + 발생일을 조합해 결정합니다. 같은 번호라도 발생일이 다른 항목을 별개로 보존하고, 행 이동·정렬 및 내용/상태/담당자/목표일 수정 시 ID가 유지됩니다. **기존 항목의 No.·설비·발생일·시트는 식별 키이므로 변경하지 마세요.** 이 값이 바뀌면 신규 항목으로 취급되며 이전 항목은 자동 삭제되지 않습니다. 동일 식별 키가 중복되면 전체 반영을 보류합니다. 새 항목은 번호·발생일·설비·내용·O/X 상태를 입력합니다.

목표일의 Excel 날짜와 YY.MM.DD, YYYY-MM-DD 등을 YYYY-MM-DD로 정규화합니다. 협의 문구·연도 없는 날짜·2000~2100년 범위 밖의 날짜는 임의 보정하지 않고 기한 그래프에서 제외합니다. 원문은 PENDING 상세와 경고 목록에 보존합니다. 빈 날짜도 기한 집계에서 제외됩니다. 완료/미완료 총건수에는 포함됩니다.

H/W와 PENDING의 파일 해시·수신 시각·비교 기준은 소스별로 분리합니다. 재전송과 다른 파일 전송이 기존 데이터를 덮어쓰지 않습니다. PENDING에서 빠진 행은 기존 DB에 유지하고, 앱/Excel 동시 수정 충돌은 해당 PENDING 파일 반영을 보류합니다. 이력·경고를 확인하고 양쪽 값을 일치시킨 뒤 다시 동기화합니다.
