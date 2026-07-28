---
name: setup
description: >
  articles-os를 처음 설정할 때 쓰는 온보딩 스킬. "articles-os 설정해줘", "articles-os 설정",
  "온보딩", "초기 설정" 같은 요청이 오거나, 플러그인 설치 직후 데이터 폴더에
  config.yaml이 아직 없을 때 이 스킬을 실행한다. 데이터 폴더 초기화 → 알림 연결(Slack) →
  매일 수집 스케줄 등록(launchd/cron)을 순서대로 진행한다.
metadata:
  version: "0.1.0"
---

## 0. 스킬 실행 조건 확인

아래 스크립트로 데이터 폴더 설정 여부를 확인한다:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_data_path.py" '${user_config.data_path}'
```

데이터 폴더 설정 여부가

- `{"configured": false}` 인 경우 : "`/plugin configure articles-os@yoouyeon-plugins`를 먼저 실행해주세요"라고 안내한 뒤 종료한다.
- `{"configured": true, "path": "..."}` 인 경우 : 그 `path`를 `<DATA>`로 쓰고 이후 단계를 순차 진행한다.

## 1. 데이터 폴더 초기화

아래 두 script를 실행하여 데이터 폴더를 초기화한다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_data_folder.py" "<DATA>"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_index.py" "<DATA>"
```

데이터 폴더 초기화 이후의 디렉토리 구조는 아래와 같다. :

```
<data_path>/
├── config.yaml        # sources(RSS 목록, 초기: 비어 있음) + notify(백엔드, 시크릿 없음 — 커밋 안전)
├── articles.json       # 기계 상태: 수집 이력·중복 제거
├── state.json          # last_run + 소스별 실패 상태
└── notes/
    ├── index.md        # 메모 목차 (scripts/update_index.py 가 갱신)
    └── YYYY-MM-DD-제목슬러그.md
```

## 2. 알림 연결

**REQUIRED SUB-SKILL:** Use articles-os:notify-config

articles-os:notify-config 스킬을 이용해서 알림 설정을 완료한다.

아래 스크립트로 완료 여부를 확인한다. :

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_notify_complete.py" <DATA> ${CLAUDE_PLUGIN_DATA}
```

- `{"complete": true, ...}` 면 다음 단계로 진행한다.
- `{"complete": false, ...}` 면 미완료 상태(notify-config 절차 중간 이탈)이므로, 사용자에게 알리고 articles-os:notify-config를 다시 안내한 뒤 재확인한다.

## 3. 스케줄 등록

**REQUIRED SUB-SKILL:** Use articles-os:schedule

articles-os:schedule 스킬을 이용해서 수집 스케줄 등록을 완료한다.

아래 스크립트로 완료 여부를 확인한다. :

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_schedule.py" status
```

- `{"registered": true, ...}` 면 다음 단계로 진행한다.
- `{"registered": false, ...}` 면 미완료 상태이므로, 사용자에게 알리고 articles-os:schedule을 다시 안내한 뒤 재확인한다.

## 4. 마무리

아래 형식 그대로 요약을 보여준다 — 값은 2·3단계에서 확인한 결과로 채운다:

```
articles-os 설정 완료

- 알림: <Slack | 알림 없음>
- 수집 스케줄: 매일 <HH>:<MM>

다음 단계:
- RSS 소스를 추가하려면: /articles-os:add-source
- 지금 바로 수집을 돌려보려면: /articles-os:collect
- 수집된 글 목록을 확인하려면: /articles-os:browse
```
