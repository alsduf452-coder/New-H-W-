# 45호기 H/W 형상 · 공정 Map

6G → 45호기 → H/W · 공정 Map에서 조회합니다.
전용 인증 소스 `process-45` (mode `process45`)를 기본 등록합니다. 명시적인 서버 소스 설정이 있으면 그 설정이 우선합니다.
기존 45호기 H/W, 15호기 공정, PENDING 소스는 그대로 유지합니다.

## 읽는 범위

- `PC_A`, `PC_B`, `PC_C`, `PC_D`, `PC_E` 시트만 파싱·저장합니다. Summary, Lists, Comparison, 양식, 경시변화는 저장하지 않습니다.
- YCNT / YILD / YILD2의 각 공정 결과 표 Date가 평가일입니다. 상단 MT 일자나 파일명 날짜로 대체하지 않습니다.
- Date가 미확정이거나 결과 전체가 비어 있는 표는 제외합니다.
- `Data 없음`, 빈칸, `##`, Excel 오류값은 결과 항목에서 제외합니다. 0과 음수는 실측값으로 유지합니다.
- 숫자 Map이 없어도 Unif.·D/R 등 실제 결과가 있으면 해당 항목만 표시합니다. 빈 Map은 표시하지 않습니다.
- 공정 Map은 원본 6×5, Flatness는 원본 7×5, Spacing은 ①⑥② / ⑨⑤⑦ / ④⑧③ 배열을 유지합니다.
- RF 사양이나 작업 메모를 공정 조건으로 추가하지 않고 해당 블록 Date와 부품 S/N을 사용합니다.

## H/W 연결

같은 PC·평가 블록에 기록된 H/W snapshot ID를 사용합니다. 측정 Date가 공정 결과 Date 당일 또는 이전이고, Spacing은 두 S/N, Flatness는 해당 부품 S/N이 같아야 표시합니다.
같은 측정일에 서로 다른 형상이 있어도 다른 평가 블록으로 대체하지 않습니다.
평가 카드에 반복 복사된 동일 측정일·PC·종류·관련 S/N·전체 grid만 중복 제거합니다.
날짜/수치 미기재는 `측정 자료 미기재`로 남기고 0이나 과거 다른 상태로 채우지 않습니다.
공백·하이픈·밑줄·대소문자 이외의 S/N 차이는 추정 보정하지 않습니다.

## PC 동기화

`local_sync/config.toml`에 다음 두 키를 추가합니다. 파일 경로는 실제 원본의 절대 경로입니다.

```toml
process45_excel_path = 'C:\실제폴더\A4_OCTA_45_설비 작업이력 및 공정 Data 정리본_v01_20261113.xlsx'
process45_source_id = 'process-45'
```

agent.py, daily_sync.py, manual_sync.py 모두 이 소스를 처리합니다.
Streamlit은 기본 `process-45`를 조회하며, 다른 소스를 쓰면 `[local_excel] process45_source_id`를 지정합니다.
원본 Excel 파일은 저장소에 넣지 않습니다.
