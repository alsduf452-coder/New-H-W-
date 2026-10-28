# 별도 앱: HW-25 화면 구성 + Excel 자동 동기화

기존 로컬 HW-25와 현재 CLOUD-05 앱을 변경하지 않고, 같은 수신 데이터로 조회하는 새 Streamlit 앱입니다. 전용 브랜치 **classic-cloud**, 실행 파일 **classic_app.py**를 사용합니다. 기존 `main`의 app.py, 수신 API, PC 동기화 프로그램, DB 구조는 변경하지 않습니다.

## 새 앱 만들기

1. Streamlit Cloud에서 **Create app**을 선택합니다. 기존 앱의 설정을 바꾸지 않습니다.
2. Repository: `alsduf452-coder/New-H-W-`
3. Branch: `classic-cloud`
4. Main file path: `classic_app.py`
5. Python: 3.12. 새 앱 주소는 사용 가능한 이름을 선택하거나 자동 생성합니다.
6. 새 앱 **Settings → Secrets**에 기존 앱의 `[storage]`, `[database]`, `[login]`, `[local_auth.users.아이디]`, `[local_excel]` 설정을 복사합니다. 기존 사용자 해시를 재사용할 수 있습니다. Secrets를 GitHub나 채팅에 올리지 않습니다.
7. 아래 선택 설정으로 H/W 설비 표시 이름을 지정할 수 있습니다.

```toml
[classic]
hw_equipment_name = "표시할 설비 이름"
```

앱은 자체 로그인이 필요하며 DB는 기존과 동일한 Render PostgreSQL의 **External Database URL**을 사용합니다. `[local_excel] source_id` 기본값은 `local-excel`, `pending_source_id` 기본값은 `pending-excel`입니다. Render와 PC 설정을 변경할 필요는 없습니다. 새 앱을 만들 때까지 원래 앱은 원래 주소에서 계속 사용할 수 있습니다.

Secrets가 없으면 명확하게 표시된 가상 샘플 화면이 나옵니다. 실제 데이터로 자동 전환되지는 않습니다. 기존 회원이 editor 역할이어도 새 앱은 조회만 허용합니다.

## 옮긴 화면

- 사각 카드 메뉴: PENDING 현황 → PENDING List REV관리 → 설비 H/W 이력관리.
- PENDING: 전체/완료/미완료/완료율 카드와 상태별 목록, 주요 5개 분야·보조·전체 범위, 설비·분야·상태·키워드 필터, 분야별/설비별 그래프, 반폭·높이 280px 목표일 그래프, 원문 상세와 Excel 다운로드. 원본 행 열은 목록에 표시하지 않습니다.
- REV: 동기화된 Rev 관리 시트의 요약/변경 이력/검색/상세와 다운로드. 출처 열이나 등록·수정 폼은 없습니다. 요약은 Excel 저장된 계산값이고 Pending 카드는 항목 재집계이므로 다를 수 있습니다.
- H/W: 부품 행 × Chamber A~E 열 통합표, 가운데 정렬 부품명, 작업 이력 카드, S/N 기록 추적, Spacing·Diffuser/Susceptor Flatness.
- 전체 챔버: 최신 측정 요약(Center 포함)과 연도별 월간 측정 횟수. 특정 A 챔버 표를 자동으로 대신 표시하지 않습니다.
- 개별 챔버: 실측표와 위치도, 기록 선택, 두 기록의 같은 색상 범위 비교 및 차이 표, 측정 이력과 열 형태의 측정값 Excel 다운로드.
- 데이터 관리: 항목별 시트로 H/W Excel 다운로드. 장착 부품에 상태·산출 근거·관련 작업 ID를 추가하지 않습니다.

## 데이터 흐름과 제한

PC Excel 수정·저장 → 기존 PC 프로그램 → 기존 수신 서버 → cloud_local_excel → 새 앱의 SELECT 조회입니다. 새 앱은 테이블 생성/변경/쓰기 쿼리를 실행하지 않고 PostgreSQL 읽기 전용 트랜잭션으로 조회합니다. 화면은 15초마다 갱신합니다. 새 설비/분야가 추가되어 필터 선택지에 아직 없으면 최신 데이터 새로고침을 누르세요.

주요 PENDING은 `__pending_data__`의 원본 상세, H/W는 `__hw_data__`, REV와 보조 시트는 수신된 셀 미리보기를 사용합니다. 따라서 **기존 앱에서만 수정한 DB 값은 새 앱에 반영하지 않습니다. Excel이 기준입니다.** 기존 앱의 DB 반영 충돌이 있어도 수신된 최신 Excel을 표시하되 충돌 안내를 보여줍니다.

원본에서 수신된 데이터만 제공합니다. 기존 로컬 SQLite에만 있던 수동 작업·첨부 사진·별도 REV 수정은 이관하지 않습니다. 원본 Excel에 없는 작업자·교체 전 정보·측정 단위나 물리 이동은 임의 생성하지 않습니다. 작업 카드의 이전 S/N은 이전 Excel 이력 행으로 확인 가능한 범위만 표시합니다.

현재 한 개 H/W 파일과 한 개 PENDING 파일을 지원합니다. REV/보조 시트는 기존 수신 서버 미리보기 한도(시트당 500행·50열, 전체 100,000셀)의 영향을 받으며, 원본 이미지/도형/성적서는 옮기지 않습니다. 전체 원본을 수신하는 기능이 아니라 수신된 셀 값의 조회입니다.

부품 색상은 최근 기록일로부터 180일 이상 주황/365일 이상 빨강입니다. 장비 안전 판정이 아니라 경과일 표시이며 RFG/Matcher/Reactor/Generator는 색상 제외입니다. 5×7 Flatness의 부호·0·미측정 값을 보존합니다. 새 앱에서 측정 수치를 직접 편집하지 않습니다.

## 검증 및 로컬 실행

```bash
pip install -r requirements.txt
streamlit run classic_app.py
```

샘플 테스트는 `python -m pytest tests/test_classic.py -q`로 실행합니다. 실제 서버 URL/DB 비밀번호/사용자 Excel은 저장소에 포함하지 않습니다. 기존 앱·수신 서버 코드는 전용 브랜치에 기반 파일로 남아 있으나 새 앱 실행 파일에서 이를 호출하거나 데이터를 수정하지 않습니다.
