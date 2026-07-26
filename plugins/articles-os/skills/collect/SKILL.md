---
name: collect
description: >
  This skill should be used when the user asks to "collect articles", "수집 실행",
  "아티클 수집해줘", "지금 수집 돌려줘", or when invoked headlessly by the OS scheduler
  as `/articles-os:collect <data-path>`. Orchestrates the daily RSS collection pipeline:
  parallel fetch, dedupe, state update, and notification.
metadata:
  version: "0.1.0"
---

## 권한 근거

이 스킬은 OS 스케줄러가 헤드리스로 호출하는 진입점이다. 실제로 쓰는 도구는 `Bash`(스크립트 호출)와 `Task`(fetch-source 병렬 소환) 뿐이다 — 소스 읽기·상태 갱신·dedup·저장이 전부 스크립트(`manage_sources.py`, `apply_collection_results.py`)로 위임되어 있어 Read/Write/Edit/Grep/WebFetch/WebSearch가 필요 없다. 헤드리스 커맨드의 `--allowedTools`는 `setup/SKILL.md`에서 `'Bash,Task'`로 좁혀 생성한다.

# 수집 파이프라인 (오케스트레이터)

매일 1회 OS 스케줄러가 헤드리스로 부르거나, 사용자가 수동으로 부른다.
스키마·경로는 `${CLAUDE_PLUGIN_ROOT}/docs/conventions.md` 참조. **비대화형으로 완주 가능해야 한다 — 사용자에게 질문하지 않는다** (수동 호출이어도 확인 없이 진행).

## 실행 시각 고정 (최초 1회, 프리프로세싱)

이번 실행의 기준 시각(UTC):

!`python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).replace(microsecond=0).isoformat())"`

위 값을 **RUN_TS**라 부른다. 아래에서 시각이 필요한 모든 지점 — 3단계에서 `apply_collection_results.py`에 전달하는 `<RUN_TS>` 하나(내부적으로 `last_success_at`·신규 아티클의 `collected_at`·`state.json.last_run`에 모두 재사용됨) — 은 전부 이 값을 그대로 쓴다.

**각 단계에서 "현재 시각"을 새로 구하지 않는다.** (배경: OS.md "주요 결정 사항" 참조)

## 0. 데이터 폴더 결정

- 인자로 절대경로가 왔으면(스케줄러 호출) 그것을 쓴다.
- 없으면 `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_install.py"` 규칙을 따른다. `none`이면 `/articles-os:setup` 안내 후 종료.

## 1. 소스 읽기

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_sources.py" list <DATA>` 실행. `sources`가 빈 배열이면 **조기 종료** — "등록된 소스가 없습니다. `/articles-os:add-source`로 추가하세요." 출력하고 끝.

## 2. 소스별 병렬 fetch

소스마다 `fetch-source` 에이전트(`articles-os:fetch-source`)를 **하나의 메시지에서 병렬로** 소환한다. 각 에이전트에 전달: 소스 `name`, `url`, 플러그인 루트 경로. 각 에이전트는 `{ok, source_name, source_url, entries}` 또는 `{ok: false, source_name, source_url, error}`를 반환한다 — 반환값을 그대로 배열로 모은다.

**실패한 소스는 스킵하고 성공한 소스만으로 계속 진행한다 (부분 성공 허용).** 실패가 있어도 전체 실행을 멈추지 않는다.

## 3. 병합·저장

2단계에서 모은 결과 배열을 JSON으로 그대로 stdin에 실어 한 번에 호출한다:

```bash
echo '<2단계 결과 배열 JSON>' | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apply_collection_results.py" "<DATA>" "<RUN_TS>"
```

state.json 소스별 상태 갱신(성공/실패 카운터), last-run 필터, dedup, articles.json 저장, last_run 갱신을 스크립트가 전담한다. 반환값(요약 JSON)을 아래 단계에서 그대로 쓴다:

```json
{ "new_articles": [{"title","source","summary","url"}], "new_count": 0,
  "failure_warnings": [{"name","url"}], "success_sources": 0, "fail_sources": 0 }
```

## 4. 알림

**항상** 보낸다 — 신규가 0건이어도 "신규 없음"을 알린다 (조용히 스킵하지 않는다):

```bash
echo "<메시지>" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/notify.py" "<DATA>"
```

메시지 형식 (Slack 평문):

- `new_count > 0`일 때, `new_articles`·`failure_warnings`로 채운다:

```
📚 articles-os — 신규 아티클 N건
• <제목> — <출처>
  <summary 한 줄>
  <url>
⚠️ 소스 경고: <이름> — 연속 3회 fetch 실패 (<url>)
```

- `new_count == 0`일 때:

```
📭 articles-os — 신규 아티클 없음
⚠️ 소스 경고: <이름> — 연속 3회 fetch 실패 (<url>)
```

(`failure_warnings`가 비어 있으면 경고 줄은 생략한다.)

알림 전송 실패는 stderr 내용을 결과에 남기되 파이프라인 실패로 치지 않는다.

## 5. 종료 리포트

터미널(및 로그)에 요약 출력: `success_sources`/`fail_sources`, `new_count`건 목록, 알림 발송 여부. `new_count`가 0이면 "신규 없음"이라고 명시한다.
