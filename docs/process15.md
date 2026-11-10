# 6G 15호기 H/W · 공정 Map

6G → 15호기 → H/W · 공정 Map 메뉴입니다. 기존 H/W 메뉴는 유지합니다.
공정 파일의 Unif 결과 데이터 시트만 읽고 다른 시트/원본 좌표 행열은 저장하지 않습니다.
각 평가 블록의 Date를 사용합니다. 상단 요약의 월/일 또는 파일명 날짜로 대체하지 않습니다.
동일 날짜·챔버의 여러 Recipe는 별개 기록으로 유지합니다.

Map이 없는 기록도 삭제하지 않으며 같은 영역에 Data 없음, 하단에 원본 Unif.만 표시합니다.
Unif.를 재계산하지 않습니다. 미기재 Unif.도 Data 없음으로 표시합니다.

H/W 연결: 같은 15호기 소스/PC/측정 종류에서 공정일 당일 또는 이전 최근 측정일을 찾습니다.
미래 데이터는 제외합니다. Spacing은 두 부품 S/N, Flatness는 해당 부품 S/N이 일치해야 합니다.
S/N에서 공백·하이픈·밑줄과 대소문자만 정규화합니다. 문자 개수 차이/다른 번호는 추측 보정하지 않습니다.
최근 측정일의 S/N이 다르거나 여러 기록이 일치하면 연결 확인 필요로 표시합니다.
더 오래된 같은 S/N으로 되돌아가서 대체하지 않습니다. 연결된 H/W의 실제 날짜와 사유를 표시합니다.

## 연결 설정

Render hw-excel-sync-classic 최신 classic-cloud를 배포하고 기존 SYNC_SOURCES_JSON에
`"process-15":{"mode":"process15"}`를 추가합니다. 기존 항목을 보존합니다.

PC local_sync에서 agent.py, daily_sync.py, manual_sync.py를 업데이트하고 config.toml 최상위에 추가:

```toml
process15_excel_path = 'Q:\실제폴더\A4_BP_15_결과_A4CVD15I MT 결과_v*_*.xlsx'
process15_source_id = 'process-15'
```

`.\.venv\Scripts\python.exe .\agent.py --config .\config.toml --once`로 최초 전송합니다.
자동/수동 예약에도 포함됩니다. 기존 부재·일시정지·실패 시 중단 동작은 유지합니다.
Streamlit 기본 process-15 소스는 Secrets 수정 없이 조회합니다.
다른 ID를 쓰려면 [local_excel] process15_source_id도 일치시킵니다.
