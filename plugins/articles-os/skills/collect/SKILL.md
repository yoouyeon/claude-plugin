---
name: collect
description: >
  articles-os의 일일 RSS 수집 파이프라인을 실행하는 오케스트레이터 스킬. "아티클 수집해줘", "수집 실행", "지금 수집 돌려줘" 같은 요청이 오거나, 
  OS 스케줄러가 `/articles-os:collect`로 헤드리스 호출할 때 이 스킬을 실행한다. 
  소스별 병렬 fetch → dedup·상태 갱신 → 알림 발송을 순서대로 진행한다.
metadata:
  version: "0.1.0"
---

## 권한 근거

이 스킬은 OS 스케줄러가 헤드리스로 호출하는 진입점이다. 실제로 쓰는 도구는 `Bash`(스크립트 호출)와 `Task`(fetch-source 병렬 소환) 뿐이다 — 소스 읽기·상태 갱신·dedup·저장이 전부 스크립트(`manage_config.py`, `apply_collection_results.py`)로 위임되어 있어 Read/Write/Edit/Grep/WebFetch/WebSearch가 필요 없다.

매일 1회 OS 스케줄러가 헤드리스로 부르거나 사용자가 수동으로 부른다. **비대화형으로 완주 가능해야 한다**

## 0. 스킬 실행 조건 확인

아래 스크립트로 초기화 여부를 확인한다:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/paths.py"
```

- `error` 키가 있는 경우 : 설정을 읽지 못한 상태다. `error`를 그대로 보여주고 종료한다.
- `initialized: false` 인 경우 : "먼저 `/articles-os:setup`을 실행하세요" 안내 후 종료한다.
- `initialized: true` 인 경우 : 이후 단계를 순차 진행한다. **데이터 경로는 스크립트들이 스스로 찾으므로 따로 넘기지 않는다.**

## 1. 기준 실행 시각 고정

이번 실행의 기준 시각(UTC):

!`python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).replace(microsecond=0).isoformat())"`

위 값을 **RUN_TS**라 부른다. 아래에서 시각이 필요한 모든 지점은 4단계에서 `apply_collection_results.py`에 전달하는 `<RUN_TS>` 하나를 그대로 쓴다. **각 단계에서 "현재 시각"을 새로 구하지 않는다.**

## 2. 소스 읽기

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" sources list` 실행. 

실행 결과가 :

- `ok: false`면 소스 목록을 읽지 못한 것이다. `error`를 그대로 보여주고 **중단**한다 — 소스가 없는 것과 구분한다.
- `sources`가 빈 배열이면 **조기 종료** — "등록된 소스가 없습니다. `/articles-os:add-source`로 추가하세요." 출력하고 끝.

## 3. 소스별 병렬 fetch

소스마다 `fetch-source` 에이전트(`articles-os:fetch-source`)를 **하나의 메시지에서 병렬로** 소환한다. 

각 에이전트에 전달: 소스 `name`, `url`, 플러그인 루트 경로. 

각 에이전트는 `{ok, source_name, source_url, entries}` 또는 `{ok: false, source_name, source_url, error}`를 반환한다 — 반환값을 그대로 배열로 모은다.

**fetch에 실패한 소스(`ok: false`)는 스킵하고 성공한 소스만으로 계속 진행한다 (부분 성공 허용, 전체 실행 중단 없음).** 다만 반환값의 형식 자체가 어긋나면(`source_url` 누락 등) 다음 단계가 아무것도 저장하지 않고 중단한다.

## 4. 병합·저장

3단계에서 모은 결과 배열을 JSON으로 그대로 stdin에 실어 한 번에 호출한다:

```bash
echo '<3단계 결과 배열 JSON>' | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apply_collection_results.py" "<RUN_TS>"
```

state.json 소스별 상태 갱신(성공/실패 카운터), last-run 필터, dedup, articles.json 저장, last_run 갱신을 스크립트가 전담한다. 반환값(요약 JSON)을 아래 단계에서 그대로 쓴다:

```json
{ "new_articles": [{"title","source","summary","url"}], "new_count": 0,
  "failure_warnings": [{"name","url"}], "success_sources": 0, "fail_sources": 0 }
```

`ok: false`면 아무것도 저장되지 않은 것이다 — 그 출력을 그대로 5단계로 넘긴다(수집 실패로 알림이 나간다). 6단계 리포트에도 실패로 적는다. **신규 0건으로 취급하지 않는다.**

## 5. 알림

**항상** 보낸다 — 신규가 0건이어도 "신규 없음"을, 4단계가 실패했으면 "수집 실패"를 알린다 (조용히 스킵하지 않는다). 4단계 출력 JSON을 그대로 stdin에 실어 포맷팅 스크립트에 넘기고, 그 출력을 전송 스크립트로 파이프한다.:

```bash
echo '<4단계 출력 JSON>' | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/format_notification.py" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/notify.py" "${CLAUDE_PLUGIN_DATA}"
```

`${CLAUDE_PLUGIN_DATA}` 자리표시자를 그대로 적는다 — 스크립트 내부에서 환경변수로 다시 읽지 않는다.

알림 전송 실패는 stderr 내용을 결과에 남기되 파이프라인 실패로 치지 않는다.

## 6. 종료 리포트

터미널(및 로그)에 요약 출력: `success_sources`/`fail_sources`, `new_count`건 목록, 알림 발송 여부. `new_count`가 0이면 "신규 없음"이라고 명시한다.

4단계가 `ok: false`였으면 위 필드가 없다 — `error`를 그대로 싣고 저장된 것이 없다고 명시한다.
