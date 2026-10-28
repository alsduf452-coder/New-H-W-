# 양산 설비 통합 관리 · Cloud-05

기존 로컬 앱과 별도로 만든 Streamlit 클라우드 앱입니다. PENDING 조회·등록·수정, Excel 수동 비교·반영, 변경 이력과 **PC 로컬 Excel 자동 동기화 코드**를 제공합니다. OCTA H/W Excel의 부품 이력·Spacing·Flatness 조회를 지원합니다. 기존 로컬 앱의 전체 기능 및 REV 관리는 아직 이관하지 않았습니다.

## 샘플로 실행하기

[Streamlit Community Cloud](https://share.streamlit.io/)에서 저장소 `alsduf452-coder/New-H-W-`, 브랜치 `main`, 실행 파일 `app.py`, Python 3.12를 선택합니다. 샘플 실행에는 Secrets가 필요 없습니다. 샘플 3건과 Excel 다운로드·업로드를 체험할 수 있습니다. 샘플 데이터는 방문자 세션별 메모리에 저장되며 세션이 끝나면 사라집니다.

## 로컬 Excel 자동 연결

회사 OneDrive 없이 **PC Excel → PC 동기화 프로그램 → HTTPS 수신 서버 → PostgreSQL → 앱**으로 연결합니다. [설치·배포·열 연결 안내](docs/LOCAL_EXCEL.md)를 순서대로 진행하세요.

- PC 프로그램은 지정한 파일을 각각 30초 주기로 확인하여 변경된 경우 전송합니다. 인터넷 연결과 실행 중인 PC 프로그램이 필요합니다.
- 시트별 값을 앱의 탭과 표로 표시합니다. PENDING은 시트 이름·머리글 행·열 이름을 설정해 현황에 반영합니다.
- 앱에서 바꾼 값과 충돌하면 파일 전체 PENDING 반영을 보류합니다. Excel에서 빠진 항목은 DB에 유지합니다.
- 앱은 마지막 수신 시각과 연결 오류·충돌 정보를 표시하며 15초마다 DB를 확인합니다.
- 코드 업로드만으로 실제 동기화가 켜지지는 않습니다. 운영 DB·로그인·수신 서버 설정이 필요합니다. 현재 저장소에는 샘플만 포함되어 있습니다.

## Excel 수동 가져오기

`Excel 동기화`에서 최신 연동용 Excel을 다운로드 → 값 수정 → 업로드 → 비교 → 확인 후 반영합니다.

- `PENDING` 시트의 기존 ID·버전은 유지합니다. 신규 항목은 고유 ID와 버전 0을 사용합니다.
- 분야: H/W, S/W, 공정, 전장, 기타. 상태: 미완료, 완료. 목표일: YYYY-MM-DD 또는 빈칸.
- 오래된 Excel과 다른 사용자가 수정한 항목은 덮어쓰지 않습니다. 일괄 반영 중 충돌이 나면 전체 작업을 취소합니다.
- 수동 연동용 양식은 기존 로컬 앱 원본 Excel과 다릅니다. 파일 한도는 20MB, PENDING 5,000행이며 수식은 허용하지 않습니다.

## 자체 아이디·비밀번호 로그인

Google/Microsoft 등록 없이 [자체 로그인 설정](docs/PASSWORD_LOGIN.md)을 사용할 수 있습니다. PC에서 `py -3.12 .\create_login.py`로 계정 해시를 만들고 Streamlit Secrets에 등록합니다. 비밀번호 원문과 생성 파일은 저장소에 올리지 않습니다. 기존 OIDC 로그인도 선택적으로 유지합니다.

## 운영과 개발

[운영 연결 안내](docs/DEPLOYMENT.md)와 `.streamlit/secrets.example.toml`을 참고하여 PostgreSQL·OIDC 로그인·허용 계정을 설정합니다. 조회 계정은 조회·다운로드만 할 수 있습니다. 실제 비밀번호·Excel·DB·보정 JSON은 GitHub에 올리지 않습니다.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

테스트: `pip install -r requirements.txt -r requirements-sync.txt pytest httpx` 후 `python -m pytest -q`. 테스트에는 샘플 데이터만 사용합니다. 실제 사용자 PC와 운영 서버의 연결 검증은 배포 후 진행해야 합니다.

## Cloud-03: OCTA H/W Excel

설비 H/W 양식은 `SYNC_MAPPING_JSON={"mode":"hw"}`로 연결합니다. `이력`의 챔버별 부품/교체 이력, Spacing 9점, Diffuser·Susceptor Flatness 5×7 표와 Center(R3C4), 최신 측정 요약 및 월별 건수를 표시합니다. [설정 및 범위](docs/LOCAL_EXCEL.md#octa-설비-hw-양식-연결-cloud-03)를 확인하세요. 원본 업무 파일은 저장소에 포함하지 않습니다.

## Cloud-05: 두 파일 연동

기존 H/W 연결을 유지하며 통합 PENDING 파일을 추가할 수 있습니다. Render에 `SYNC_SOURCES_JSON={"pending-excel":{"mode":"pending_octa"}}`를 추가하고, PC config.toml에 `pending_excel_path`를 지정합니다. [설정 안내](docs/LOCAL_EXCEL.md#cloud-05-hw--통합-pending-두-파일-동기화)를 참고하세요. 실제 업무 Excel·개인명·이슈 내용은 저장소에 포함하지 않습니다.
