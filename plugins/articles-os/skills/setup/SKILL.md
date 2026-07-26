---
name: setup
description: >
  This skill should be used when the user asks to "set up articles-os", "articles-os 설정",
  "온보딩", "초기 설정", or right after installing the plugin when no install exists yet.
  Walks through the 4-step onboarding: data path, RSS sources, notification backend,
  and daily collection schedule (launchd/cron).
metadata:
  version: "0.1.0"
---

# articles-os 온보딩

최초 설치 직후 4단계를 순차 진행한다: **① 데이터 경로 → ② 소스 추가 → ③ 알림 연결 → ④ 스케줄 등록**.
공통 경로·스키마는 `${CLAUDE_PLUGIN_ROOT}/docs/conventions.md` 참조.

시작 전에 `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_install.py"`로 기존 설치를 확인한다. 현재 프로젝트에 이미 설치가 있으면 사용자에게 알리고, 재설정(개별 단계 재실행)인지 새 설치인지 확인한다.

## ① 데이터 경로 지정 + install_id 생성

1. 기본값으로 `<현재 폴더>/articles-os`를 제안하고, 다른 절대경로 입력도 받는다. 표시명(label)도 확인한다(기본: 상위 폴더명).
2. 초기화 실행 — install_id 생성, 폴더·초기 파일 생성(`sources.yaml`/`notify.yaml`/`articles.json`/`state.json`), 홈 레지스트리(`~/.articles-os/registry.json`) 등록, `~/.articles-os/logs/` 생성을 스크립트가 한 번에 처리한다:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_install.py" create "<DATA 절대경로>" --label "<라벨>"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_index.py" "<DATA>"
```

반환된 `install_id`를 이후 단계(③ 시크릿 저장, ④ scheduler_job_id 갱신)에서 그대로 쓴다.

## ② 소스 추가 (필수 — 없으면 플러그인이 동작하지 않음)

`add-source` 스킬과 같은 로직을 인라인으로 수행한다: RSS URL을 받아 `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_feed.py`로 검증 후 `sources.yaml`에 추가. 상세 절차는 `${CLAUDE_PLUGIN_ROOT}/skills/add-source/SKILL.md`를 따른다. 최소 1개 이상 등록을 권하되, 사용자가 나중으로 미루면 "소스가 없으면 수집이 조기 종료된다"고 알리고 진행한다.

## ③ 알림 연결

`${CLAUDE_PLUGIN_ROOT}/skills/notify-config/SKILL.md`의 절차를 그대로 따른다 — 백엔드 선택부터 `save_secret.py` 호출·`notify.yaml` 갱신·테스트 알림까지 그 스킬의 절차(스크립트 호출 포함)를 재사용한다. 여기서 새로 규정하지 않는다.

## ④ 스케줄 등록 (자동 등록 + 사용자 확인)

수집 시각을 물어본다 (기본 제안: 매일 09:00). OS는 `uname`으로 판별. **등록 커맨드를 사용자에게 먼저 보여주고 확인받은 뒤** 실행한다.

헤드리스 실행은 현재 세션의 PATH나 cwd를 상속받지 못하므로, 실행 파일 경로와 플러그인 루트를 먼저 확정해 커맨드에 절대경로로 박아 넣는다:

```bash
command -v claude              # <CLAUDE_BIN>
echo "${CLAUDE_PLUGIN_ROOT}"   # <PLUGIN_ROOT> — inline 플러그인은 --plugin-dir 없이는 헤드리스에서 "Unknown command"로 실패한다
```

공통 실행 커맨드 (경로를 커맨드라인 자체에 박는다 — 헤드리스 실행이 스스로 데이터 폴더를 찾는 방법):

```
<CLAUDE_BIN> --plugin-dir <PLUGIN_ROOT> -p '/articles-os:collect <DATA 절대경로>' --allowedTools 'Bash,Task'
```

`--allowedTools`는 `Bash,Task`로 좁힌다 — `collect` 스킬은 소스 읽기·상태 갱신·dedup·저장을 전부 스크립트(`manage_sources.py`, `apply_collection_results.py`)에 위임하고 `fetch-source` 서브에이전트 소환에 `Task`를 쓸 뿐, Read/Write/Edit/Glob/Grep/WebFetch/WebSearch를 직접 호출하지 않는다.

### macOS (launchd 우선)

`~/Library/LaunchAgents/com.articles-os.<install_id>.plist` 작성:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.articles-os.<INSTALL_ID></string>
  <key>ProgramArguments</key>
  <array>
    <string><CLAUDE_BIN></string>
    <string>--plugin-dir</string>
    <string><PLUGIN_ROOT></string>
    <string>-p</string>
    <string>/articles-os:collect <DATA></string>
    <string>--allowedTools</string>
    <string>Bash,Task</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer><HH></integer><key>Minute</key><integer><MM></integer></dict>
  <key>StandardOutPath</key><string><HOME>/.articles-os/logs/<INSTALL_ID>.log</string>
  <key>StandardErrorPath</key><string><HOME>/.articles-os/logs/<INSTALL_ID>.log</string>
</dict>
</plist>
```

실행 파일·플러그인 루트를 배열 항목으로 각각 분리해 절대경로로 넣는다 — 로그인 비대화형 셸(`-lc`)은 `.zshrc`를 읽지 않아 PATH에 `claude`가 안 잡힐 수 있고, 셸 래퍼를 거치면 따옴표 이스케이프 문제도 생긴다. 등록·확인:

```bash
launchctl load ~/Library/LaunchAgents/com.articles-os.<INSTALL_ID>.plist
launchctl list | grep com.articles-os.<INSTALL_ID>
```

### Linux (cron)

crontab에 한 줄 추가 (식별 주석 필수 — 나중에 이 주석으로 찾아 제거·갱신):

```bash
(crontab -l 2>/dev/null; echo "<MM> <HH> * * * <CLAUDE_BIN> --plugin-dir <PLUGIN_ROOT> -p '/articles-os:collect <DATA>' --allowedTools 'Bash,Task' >> \$HOME/.articles-os/logs/<INSTALL_ID>.log 2>&1 # articles-os:<INSTALL_ID>") | crontab -
crontab -l | grep articles-os:<INSTALL_ID>
```

### 등록 후

레지스트리 항목의 `scheduler_job_id`를 갱신한다 — macOS: `com.articles-os.<install_id>`, Linux: `articles-os:<install_id>` (cron 주석):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_install.py" set-scheduler-job "<install_id>" "<job_id>"
```

## 마무리

4단계 요약을 보여준다: 데이터 경로, 등록된 소스 수, 알림 백엔드, 스케줄 시각·확인 결과. 다음 행동 안내: 즉시 첫 수집을 돌려보려면 `/articles-os:collect`, 소스 추가는 `/articles-os:add-source`, 목록 보기는 `/articles-os:browse`.

## 주의

- 플러그인 디렉토리에 아무것도 쓰지 않는다. 쓰기 대상은 `<DATA>`와 `~/.articles-os/`뿐.
- 시크릿(웹훅 URL)은 `notify.yaml`·데이터 폴더에 절대 넣지 않는다 — 오직 `~/.articles-os/secrets.json`(600).
- Windows는 1차 범위 밖 — 감지되면 macOS/Linux에서 사용하라고 안내한다.
