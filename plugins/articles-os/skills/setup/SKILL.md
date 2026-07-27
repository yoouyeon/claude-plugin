---
name: setup
description: >
  This skill should be used when the user asks to "set up articles-os", "articles-os 설정",
  "온보딩", "초기 설정", or right after installing the plugin when `config.yaml` doesn't
  exist yet at the data folder. Walks through the 3-step onboarding: RSS sources,
  notification backend, and daily collection schedule (launchd/cron).
metadata:
  version: "0.1.0"
---

# articles-os 온보딩

데이터 폴더 경로는 플러그인 활성화 시 Claude Code가 이미 물어본 값 `${user_config.data_path}`를
그대로 쓴다 — 이 스킬에서 다시 묻지 않는다. 이하 `<DATA>`는 이 값을 가리킨다.

3단계를 순차 진행한다: **① 소스 추가 → ② 알림 연결 → ③ 스케줄 등록**.
공통 경로·스키마는 `${CLAUDE_PLUGIN_ROOT}/docs/conventions.md` 참조.

## 0. 데이터 폴더 초기화

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_data_folder.py" "<DATA>"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_index.py" "<DATA>"
```

이미 초기화돼 있으면(재설정 목적으로 setup을 다시 부른 경우) 기존 파일은 건드리지 않는다 — 사용자에게 재설정인지 확인하고 이어서 진행한다.

## ① 소스 추가 (필수 — 없으면 플러그인이 동작하지 않음)

`add-source` 스킬과 같은 로직을 인라인으로 수행한다: RSS URL을 받아 `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_feed.py`로 검증 후 `config.yaml`에 추가. 상세 절차는 `${CLAUDE_PLUGIN_ROOT}/skills/add-source/SKILL.md`를 따른다. 최소 1개 이상 등록을 권하되, 사용자가 나중으로 미루면 "소스가 없으면 수집이 조기 종료된다"고 알리고 진행한다.

## ② 알림 연결

`${CLAUDE_PLUGIN_ROOT}/skills/notify-config/SKILL.md`의 절차를 그대로 따른다 — 백엔드 선택부터 `save_secret.py` 호출·`config.yaml` 갱신·테스트 알림까지 그 스킬의 절차(스크립트 호출 포함)를 재사용한다. 여기서 새로 규정하지 않는다.

## ③ 스케줄 등록 (자동 등록 + 사용자 확인)

수집 시각을 물어본다 (기본 제안: 매일 09:00). OS는 `uname`으로 판별. **등록 커맨드를 사용자에게 먼저 보여주고 확인받은 뒤** 실행한다.

실행 파일 경로를 먼저 확정해 커맨드에 절대경로로 박아 넣는다 — 로그인 비대화형 셸(`-lc`)은 `.zshrc`를 읽지 않아 PATH에 `claude`가 안 잡힐 수 있다:

```bash
command -v claude              # <CLAUDE_BIN>
```

공통 실행 커맨드 — 데이터 경로는 인자로 넘기지 않는다. `data_path`는 `userConfig`로 저장돼 있어 헤드리스 `-p` 호출에서도 `${user_config.data_path}`가 그대로 해석된다:

```
<CLAUDE_BIN> -p '/articles-os:collect' --allowedTools 'Bash,Task'
```

`--allowedTools`는 `Bash,Task`로 좁힌다 — `collect` 스킬은 소스 읽기·상태 갱신·dedup·저장을 전부 스크립트(`manage_config.py`, `apply_collection_results.py`)에 위임하고 `fetch-source` 서브에이전트 소환에 `Task`를 쓸 뿐, Read/Write/Edit/Glob/Grep/WebFetch/WebSearch를 직접 호출하지 않는다.

### macOS (launchd 우선)

`~/Library/LaunchAgents/com.articles-os.plist` 작성:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.articles-os</string>
  <key>ProgramArguments</key>
  <array>
    <string><CLAUDE_BIN></string>
    <string>-p</string>
    <string>/articles-os:collect</string>
    <string>--allowedTools</string>
    <string>Bash,Task</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer><HH></integer><key>Minute</key><integer><MM></integer></dict>
  <key>StandardOutPath</key><string><HOME>/Library/Logs/articles-os.log</string>
  <key>StandardErrorPath</key><string><HOME>/Library/Logs/articles-os.log</string>
</dict>
</plist>
```

등록·확인:

```bash
launchctl load ~/Library/LaunchAgents/com.articles-os.plist
launchctl list | grep com.articles-os
```

### Linux (cron)

crontab에 한 줄 추가 (식별 주석 필수 — 나중에 이 주석으로 찾아 제거·갱신):

```bash
(crontab -l 2>/dev/null; echo "<MM> <HH> * * * <CLAUDE_BIN> -p '/articles-os:collect' --allowedTools 'Bash,Task' >> \$HOME/.articles-os.log 2>&1 # articles-os") | crontab -
crontab -l | grep articles-os
```

## 마무리

3단계 요약을 보여준다: 등록된 소스 수, 알림 백엔드, 스케줄 시각·확인 결과. 다음 행동 안내: 즉시 첫 수집을 돌려보려면 `/articles-os:collect`, 소스 추가는 `/articles-os:add-source`, 목록 보기는 `/articles-os:browse`.

## 주의

- 플러그인 디렉토리에 아무것도 쓰지 않는다. 쓰기 대상은 `<DATA>`와 `${CLAUDE_PLUGIN_DATA}`(시크릿)뿐.
- 시크릿(웹훅 URL)은 `config.yaml`·데이터 폴더에 절대 넣지 않는다 — 오직 `${CLAUDE_PLUGIN_DATA}/secrets.json`(600).
- Windows는 1차 범위 밖 — 감지되면 macOS/Linux에서 사용하라고 안내한다.
