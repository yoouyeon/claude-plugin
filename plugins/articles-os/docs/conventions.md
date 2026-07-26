# articles-os 공통 규약

모든 스킬·에이전트가 공유하는 경로·스키마·규칙. 스킬 실행 시 필요한 부분만 참조한다.

## 실행 환경 전제

- Claude Code 전용, 순수 터미널(헤드리스 서버 포함). artifact·데스크톱 알림 없음 — 모든 출력은 터미널 마크다운.
- 플러그인 설치 디렉토리(`${CLAUDE_PLUGIN_ROOT}`)는 **읽기 전용**. 사용자 데이터는 절대 여기에 쓰지 않는다.

## 경로

**홈 레벨 (`~/.articles-os/`)** — 설치 목록·시크릿·로그. 데이터가 아니라 이정표.

| 파일 | 역할 | 권한 |
|---|---|---|
| `registry.json` | 이 머신의 설치 목록 | 기본 |
| `secrets.json` | 웹훅 시크릿, `install_id` 키 | **600 필수** |
| `logs/<install_id>.log` | 헤드리스 수집 로그 | 기본 |

**데이터 폴더 (설치별, 레지스트리의 `path`)** — 사용자 영구 데이터.

```
<data-path>/
├── config/
│   ├── sources.yaml      # RSS 소스 목록 (초기: 비어 있음)
│   └── notify.yaml       # 알림 백엔드 (시크릿 없음 — 커밋 안전)
├── data/
│   ├── articles.json     # 기계 상태: 수집 이력·중복 제거
│   └── state.json        # last_run + 소스별 실패 상태
└── notes/
    ├── index.md          # 메모 목차 (scripts/update_index.py 가 갱신)
    └── YYYY-MM-DD-제목슬러그.md
```

## 활성 설치 결정 규칙 (모든 대화형 스킬 공통)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_install.py"
```

출력의 `reason`에 따라:

1. `cwd` — 현재 폴더가 어떤 설치 `path`의 하위 → 그 설치를 그대로 사용
2. `single` — 설치가 하나뿐 → 그것 사용
3. `multiple` — 후보 목록을 사용자에게 보여주고 선택 받기
4. `none` — 설치 없음 → "먼저 `/articles-os:setup`을 실행하세요" 안내 (**자동 실행 금지**, 유도만)

추가로 `sources.yaml`이 비어 있으면 `/articles-os:add-source`를 유도한다.

## 파일 스키마

### `~/.articles-os/registry.json`

```json
{
  "installs": [
    {
      "install_id": "a1b2c3d4",
      "path": "/abs/path/to/articles-os",
      "label": "표시용 이름",
      "scheduler_job_id": "com.articles-os.a1b2c3d4",
      "created_at": "2026-07-14T09:00:00+09:00"
    }
  ]
}
```

- `install_id`: 온보딩 1단계에서 생성하는 영구 식별자. `secrets.json`의 키. 스케줄러 작업이 재등록돼도 불변.
- `scheduler_job_id`: launchd label 또는 cron 식별 주석. 4단계 전에는 `null`.

### `~/.articles-os/secrets.json` (chmod 600)

```json
{ "a1b2c3d4": { "slack_webhook_url": "https://hooks.slack.com/..." } }
```

시크릿은 **오직 여기**. `notify.yaml`·데이터 폴더·플러그인 디렉토리에 절대 두지 않는다.

### `config/sources.yaml`

```yaml
sources:
  - name: 토스 기술블로그
    url: https://toss.tech/rss.xml
```

`name`은 표시용, `url`이 fetch 대상. 비어 있으면 수집은 조기 종료.

### `config/notify.yaml`

```yaml
backend: slack   # slack | none
```

### `data/articles.json`

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

### `data/state.json`

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
echo "<메시지 텍스트>" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/notify.py" <data-path>
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
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_index.py" <data-path>
```

## 원칙 요약

- json = 기계 상태, md = 사람 산출물. 섞지 않는다.
- 요약은 알림용, 학습은 원문. 본문은 지연 fetch.
- 부분 성공 허용: 소스 1개 장애가 전체를 막지 않는다.
- 자동 실행은 수집(daily)뿐.
