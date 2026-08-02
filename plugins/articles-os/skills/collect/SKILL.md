---
name: collect
description: >
  articles-os의 일일 RSS 수집 파이프라인. OS 스케줄러가 `/articles-os:collect`로 헤드리스 호출한다.
  수집 → dedup·상태 갱신 → 알림 발송을 순서대로 진행한다.
disable-model-invocation: true
metadata:
  version: "0.1.0"
---

## 실행 제약

OS 스케줄러가 헤드리스로 호출하므로 **비대화형으로 완주해야 한다**

## 1. 기준 실행 시각 고정

이번 실행의 기준 시각(UTC):

!`python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).replace(microsecond=0).isoformat())"`

위 값을 **RUN_TS**라 부른다. 아래에서 시각이 필요한 모든 지점은 3단계에서 `apply_collection_results.py`에 전달하는 `<RUN_TS>` 하나를 그대로 쓴다. **각 단계에서 "현재 시각"을 새로 구하지 않는다.**

## 2. 소스 확인

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" sources list` 실행.

실행 결과에 따라:

- `ok: false` : `error`를 그대로 보여주고 **중단**
- `sources`가 빈 배열 : "등록된 소스가 없습니다. `/articles-os:add-source`로 추가하세요." 출력하고 **조기 종료**
- 그 밖 : 소스 개수만 기억하고 3단계로 간다. **목록 내용을 옮겨 적지 않는다.**

## 3. 수집·저장

아래 파이프를 그대로 한 번에 실행한다. **중간 출력을 읽거나 다시 실어 나르지 않는다** — 소스 목록과 fetch된 아티클 전문이 프로세스 사이로만 흐른다:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" sources list \
  | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fetch_feed.py" \
  | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apply_collection_results.py" "<RUN_TS>"
```

소스별 병렬 fetch·재시도, state.json 상태 갱신(성공/실패 카운터), last-run 필터, dedup, articles.json 저장, last_run 갱신을 스크립트가 전담한다.

**fetch에 실패한 소스는 스킵하고 성공한 소스만으로 계속 진행한다 (부분 성공 허용, 전체 실행 중단 없음).** 파이프 마지막 출력(요약 JSON)을 아래 단계에서 그대로 쓴다:

```json
{ "new_articles": [{"title","source","summary","url"}], "new_count": 0,
  "failure_warnings": [{"name","url"}], "success_sources": 0, "fail_sources": 0 }
```

`ok: false`면 아무것도 저장되지 않은 것이다 — 그 출력을 그대로 4단계로 넘긴다(수집 실패로 알림이 나간다). 5단계 리포트에도 실패로 적는다. **신규 0건으로 취급하지 않는다.**

## 4. 알림

**항상** 보낸다 — 신규가 0건이어도 "신규 없음"을, 3단계가 실패했으면 "수집 실패"를 알린다 (조용히 스킵하지 않는다). 3단계 출력 JSON을 그대로 stdin에 실어 포맷팅 스크립트에 넘기고, 그 출력을 전송 스크립트로 파이프한다.:

```bash
echo '<3단계 출력 JSON>' | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/format_notification.py" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/notify.py" "${CLAUDE_PLUGIN_DATA}"
```

`${CLAUDE_PLUGIN_DATA}` 자리표시자를 그대로 적는다 — 스크립트 내부에서 환경변수로 다시 읽지 않는다.

알림 전송 실패는 stderr 내용을 결과에 남기되 파이프라인 실패로 치지 않는다.

## 5. 종료 리포트

터미널(과 로그)에 요약 출력: `success_sources`/`fail_sources`, `new_count`건 목록, 알림 발송 여부. `new_count`가 0이면 "신규 없음"이라고 명시한다.

3단계가 `ok: false`였으면 위 필드가 없다 — `error`를 그대로 싣고 저장된 것이 없다고 명시한다.
