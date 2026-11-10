# 8G CPO PENDING 연결

classic-cloud 전용 변경. 6G는 pending-excel, 8G는 pending-8g를 기본 소스로 사용합니다.
8G는 별도 스냅샷으로 저장하며 기존 편집용 PENDING 테이블에 항목을 추가하지 않습니다.

## 서버와 PC 설정

1. Render의 hw-excel-sync-classic 서비스를 최신 classic-cloud 커밋으로 배포합니다.
2. 기존 SYNC_SOURCES_JSON 객체에 `"pending-8g":{"mode":"pending_cpo"}` 항목을 추가합니다.
   기존 pending-excel / hw-15 등의 항목을 보존합니다. DB URL과 토큰은 변경하지 않습니다.
3. PC local_sync의 agent.py, daily_sync.py, manual_sync.py를 업데이트합니다.
4. 기존 config.toml 최상위에 아래 두 줄을 추가합니다. 이미 있으면 해당 값만 수정합니다.

```toml
pending8_excel_path = 'C:\실제폴더\A6_BP_04_정리_CPO_Qual_Pending_List_v*_*.xlsx'
pending8_source_id = 'pending-8g'
```

5. local_sync에서 `.\.venv\Scripts\python.exe agent.py --once`를 실행하고 기존 토큰을 입력합니다.
   `8G PENDING 전송 완료 · 29건 반영`처럼 전송 결과를 확인합니다. 건수는 파일 내용에 따라 달라집니다.
6. Streamlit에서 8G → PENDING 현황을 선택하고 수신 시간과 건수를 확인합니다.
   기본 소스 ID 사용 시 Streamlit Secrets 추가는 필요 없습니다. 사용자 지정 시
   기존 [local_excel]에 pending8_source_id를 설정하고 서버/PC와 동일하게 맞춥니다.

09:00 자동 작업과 수동 요청 처리 모두 8G를 포함합니다. 기존 부재/일시정지/실패 시 중단 규칙은 유지됩니다.
수동 요청 작업을 Disabled로 해둔 PC는 앱 버튼으로 요청을 처리하지 않습니다. 이 변경은 작업을 재등록하거나
숨김 실행 방식을 바꾸지 않습니다. 최초 검증은 위 --once 명령으로 가능합니다.

## 양식과 해석

- Summary 상단의 A6 BP-04 형식 설비명과 CPO Pending Item 머리글을 검사합니다.
- No.로 항목을 식별합니다. 순서/내용/분류가 바뀌어도 같은 ID를 유지합니다. 기존 번호를 다른 항목에 재사용하지 않습니다.
- 완료 / 고객 전달 완료만 완료 집계. Monitoring / 준비 완료 / SDC 검토중 / 추후 진행 / 미완료는 미완료 집계.
- 진척도는 원본 백분율, 분류는 원문, 일정은 목표일 원문으로 표시합니다.
- 분류가 비고인 행은 같은 No.의 관련 메모로 연결하고 건수에서 제외합니다.
- 없는 담당자나 REV 이력은 생성하지 않습니다. 파일명 v08을 REV 기록으로 간주하지 않습니다.
- 날짜 해석 불가 항목은 기한 집계에서 제외하고 안내합니다.
- 번호 중복, 알 수 없는 상태, 범위 밖 진척도, 연결되지 않은 메모는 수신을 거부하여 직전 데이터를 보존합니다.
- 파일명 패턴은 고정 폴더 내 최근 수정 파일을 선택하며 ~$ 임시 파일은 제외합니다.
  수정 시각이 같은 후보가 여러 개면 임의 선택하지 않고 오류를 표시합니다.
- 세대 전환 시 PENDING 검색/필터/카드 선택을 초기화합니다. 8G 미수신 상태에서 6G로 대체하지 않습니다.
