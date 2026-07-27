# articles-os 공통 규약

모든 스킬·에이전트가 공유하는 경로·스키마·규칙. 스킬 실행 시 필요한 부분만 참조한다.

## 실행 환경 전제

- Claude Code 전용, 순수 터미널(헤드리스 서버 포함). artifact·데스크톱 알림 없음 — 모든 출력은 터미널 마크다운.
- 플러그인 설치 디렉토리(`${CLAUDE_PLUGIN_ROOT}`)는 **읽기 전용**. 사용자 데이터는 절대 여기에 쓰지 않는다.

## 경로

**Claude Code 기존 인프라 (우리가 만드는 홈 디렉토리 없음)**

| 위치 | 역할 | 권한 |
|---|---|---|
| `~/.claude/settings.json`의 `pluginConfigs[<plugin-id>].options.data_path` | 데이터 폴더 절대경로 (userConfig) | Claude Code 관리 |
| `${CLAUDE_PLUGIN_DATA}/secrets.json` | 웹훅 시크릿 하나만, flat | **600 필수** |

수집 실행 로그는 OS 스케줄러의 표준 출력 리다이렉션(launchd `StandardOutPath`/cron `>> ... 2>&1`)에 맡긴다 — 별도 로그 파일을 우리가 관리하지 않는다.

**데이터 폴더 (`${user_config.data_path}`)** — 사용자 영구 데이터.

```
<data_path>/
├── config.yaml        # sources(RSS 목록, 초기: 비어 있음) + notify(백엔드, 시크릿 없음 — 커밋 안전)
├── articles.json       # 기계 상태: 수집 이력·중복 제거
├── state.json          # last_run + 소스별 실패 상태
└── notes/
    ├── index.md        # 메모 목차 (scripts/update_index.py 가 갱신)
    └── YYYY-MM-DD-제목슬러그.md
```

## 데이터 폴더 경로 (모든 스킬·에이전트 공통)

`<DATA>` = `${user_config.data_path}` — 스킬·에이전트 콘텐츠에 이 자리표시자를 그대로 적으면 Claude Code가 실제 절대경로로 치환한다(대화형·헤드리스 `-p` 모두 동작). 별도 스크립트로 해석할 필요가 없다.

- `<DATA>/config.yaml`이 없으면 → "먼저 `/articles-os:setup`을 실행하세요" 안내 (**자동 실행 금지**, 유도만)
- 있지만 `sources`가 비어 있으면 → `/articles-os:add-source`를 유도한다.

## 파일 스키마

### `${CLAUDE_PLUGIN_DATA}/secrets.json` (chmod 600)

```json
{ "slack_webhook_url": "https://hooks.slack.com/..." }
```

`${CLAUDE_PLUGIN_DATA}`는 Claude Code가 관리하는 플러그인 영구 데이터 디렉토리 경로(`~/.claude/plugins/data/<plugin-id>/`)다. `save_secret.py`/`notify.py`는 이 경로를 **인자로만 받는다** — 스크립트 내부에서 `os.environ`으로 다시 읽지 않는다. 호출하는 SKILL.md가 `${CLAUDE_PLUGIN_DATA}` 플레이스홀더를 커맨드에 그대로 적어 넘긴다. 근거: `docs/rationale.md#secrets`. 시크릿은 **오직 여기**. `config.yaml`·데이터 폴더·플러그인 디렉토리에 절대 두지 않는다.

### `config.yaml` (데이터 폴더 바로 밑)

```yaml
sources:
  - name: 토스 기술블로그
    url: https://toss.tech/rss.xml
notify:
  backend: slack   # slack | none
```

`sources[].name`은 표시용, `url`이 fetch 대상. `sources`가 비어 있으면 수집은 조기 종료. `notify.backend`엔 시크릿이 없으므로 프로젝트째 커밋·동기화돼도 안전하다. 읽기·쓰기는 항상 `scripts/manage_config.py`를 통한다(직접 파싱하지 않는다).

### `articles.json` (데이터 폴더 바로 밑)

```json
{
  "articles": [
    {
      "url": "...",
      "title": "...",
      "source": "...",
      "published_at": "ISO8601 (UTC 정규화)",
      "collected_at": "ISO8601",
      "summary": "RSS description 재사용 — 알림·목록 표시 전용",
      "qa_log": [],
      "note_path": null
    }
  ]
}
```

- `summary`: RSS `description` 그대로. AI 생성 금지. **Q&A·인터뷰에는 사용 금지**(손실 정보) — 그쪽은 항상 원문.
- 본문(원문)은 `articles.json`에 저장하지 않는다. Q&A/메모가 첫 진입 시 지연 fetch하며, 세션 한정(대화 컨텍스트에만 남고 디스크에 캐시되지 않음) — 다음 세션엔 다시 fetch한다.
- `qa_log`: `[{ "asked_at": "...", "question": "...", "answer_digest": "..." }]`. 메모 저장 시 비운다.
- 중복 판정은 `url` 기준.

### `state.json` (데이터 폴더 바로 밑)

```json
{
  "last_run": null,
  "sources": {
    "<source url>": {
      "consecutive_failures": 0,
      "last_success_at": null,
      "alerted": false
    }
  }
}
```

- `last_run`: 하나 이상의 소스가 성공한 실행만 갱신. 전부 실패 시 유지(발행분 유실 방지).
- `consecutive_failures` ≥ 3 → "죽은 소스" 경고 1회 (`alerted`로 중복 방지, 성공 시 false 리셋).

## 알림 (notify 추상화)

파이프라인은 백엔드를 모른다. 항상 스크립트를 통해서만 보낸다:

```bash
echo "<메시지 텍스트>" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/notify.py" <DATA> "${CLAUDE_PLUGIN_DATA}"
```

- `backend: none`이면 스크립트가 조용히 스킵(exit 0).
- 알림 실패는 경고만 남기고 **파이프라인을 중단하지 않는다**.

## 메모 .md 형식

파일명: `notes/YYYY-MM-DD-제목슬러그.md` (슬러그: 한글 유지, 공백→`-`, 특수문자 제거)

```markdown
---
title: 아티클 제목
url: https://...
source: 출처명
date: 2026-07-14
---

# 아티클 제목

## 덤프 (원문 그대로)
사용자가 쏟아낸 생각 원문. 다듬지 않는다.

## 회상 인터뷰
Q/A 형태로 사용자 발화 중심 기록.

## 정리
사용자가 덤프·인터뷰에서 한 말을 구조화. AI 재서술 금지.
```

메모 저장 후 반드시:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_index.py" <DATA>
```

## 원칙 요약

- json = 기계 상태, md = 사람 산출물. 섞지 않는다.
- 요약은 알림용, 학습은 원문. 본문은 지연 fetch.
- 부분 성공 허용: 소스 1개 장애가 전체를 막지 않는다.
- 자동 실행은 수집(daily)뿐.
