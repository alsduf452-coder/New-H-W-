# 양산 설비 통합 관리 · Cloud-01

기존 로컬 앱과 별도로 만든 Streamlit 클라우드 초기 버전입니다. **현재 구현 범위는 PENDING 등록·수정·조회, Excel 변경 비교·반영, 변경 이력입니다.** 기존 H/W·REV·Spacing·Flatness 화면과 데이터는 아직 이관하지 않았습니다.

## 먼저 샘플로 배포하기

1. [Streamlit Community Cloud](https://share.streamlit.io/)에 GitHub 계정으로 로그인합니다.
2. 앱 생성에서 저장소 `alsduf452-coder/New-H-W-`, 브랜치 `main`, 실행 파일 `app.py`를 선택합니다.
3. Python 3.12를 선택하고 배포합니다. 샘플 실행에는 Secrets 설정이 필요 없습니다.
4. PENDING 샘플 3건을 확인하고 `Excel 동기화`에서 Excel을 다운로드합니다.
5. Excel의 내용을 수정하고 업로드한 후 `변경사항 비교` → 확인 체크 → `변경사항 반영`을 누릅니다.

샘플 모드는 방문자 세션마다 독립된 메모리 DB를 사용합니다. 세션이 끝나면 데이터가 사라집니다. 실제 업무 데이터는 운영 DB와 로그인 설정을 완료한 뒤 사용하세요. 이 저장소에는 샘플만 포함되어 있습니다.

## Excel 연동 규칙

- 앱에서 내려받은 `PENDING` 시트를 사용합니다. 기존 로컬 앱의 원본 Excel과는 다른 연동 양식입니다.
- 기존 항목의 `ID`와 `버전`은 유지합니다. 신규 항목에는 중복되지 않는 ID와 버전 `0`을 넣습니다.
- 분야: H/W, S/W, 공정, 전장, 기타. 상태: 미완료, 완료. 목표일: YYYY-MM-DD 또는 빈칸.
- 변경할 때마다 버전이 증가합니다. 오래된 Excel이나 비교 이후 다른 사용자가 수정한 항목은 덮어쓰지 않고 충돌로 처리합니다.
- 여러 행 반영 중 충돌이 생기면 해당 반영 작업 전체를 취소합니다.
- Excel에서 빠진 항목은 DB에 유지합니다. 자동 삭제하지 않습니다.
- 변경자, 변경 시각, 변경 전후 값을 DB에 함께 기록합니다.
- 파일당 최대 10MB, 5,000행이며 수식은 허용하지 않습니다.

현재는 **업로드 후 검토·반영 방식**입니다. PC의 Excel을 저장하는 즉시 앱에 반영하거나 OneDrive/SharePoint 변경을 자동 감지하는 기능은 아직 없습니다.

## 실제 데이터 운영 설정

[운영 연결 안내](docs/DEPLOYMENT.md)를 따라 PostgreSQL과 회사 OIDC 로그인을 구성합니다. `[storage] mode = "postgres"`로 설정하면 DB·로그인·허용 계정이 설정되어야 앱을 사용할 수 있습니다. 편집 권한이 없는 허용 계정은 조회와 다운로드만 할 수 있습니다.

실제 비밀번호, Excel, DB, 보정 JSON을 GitHub에 올리지 마세요. 현재 저장소가 공개되어 있으므로 소스 공개가 적절하지 않으면 GitHub에서 Private으로 전환한 후 운영하세요. 앱 접근 권한과 저장소 공개 범위는 별도입니다.

## 로컬 개발

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

검증: `pip install pytest` 후 `python -m pytest -q`. 테스트는 샘플 데이터만 사용합니다.

## 다음 단계

실제 PostgreSQL·회사 로그인으로 접속/권한/동시 수정 검증 → 기존 데이터 이관 규칙 확정 → H/W·REV·측정 화면 추가 → OneDrive/SharePoint 자동 동기화 순서로 확장합니다. 기존 로컬 앱의 사용자 데이터는 이 저장소로 복사하지 않았습니다.
