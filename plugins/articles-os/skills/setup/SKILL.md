---
name: setup
description: >
  articles-os를 처음 설정할 때 쓰는 온보딩 스킬. 메모 폴더 지정 → 알림 연결(Slack·Discord) → 매일 수집 스케줄 등록(macOS launchd)을 순서대로 진행한다.
disable-model-invocation: true
metadata:
  version: "0.1.0"
---

## 0. 현재 상태 확인

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/paths.py"
```

- `error` 키가 있는 경우 : 설정을 읽지 못한 상태다. `error`를 그대로 보여주고 중단한다.
- `initialized: false` 인 경우 : 최초 설정이다. 1단계로 진행한다.
- `initialized: true` 인 경우 : 이미 설정돼 있다. `notes_root`를 보여주고 다시 설정할지 확인한 뒤, 진행하면 1단계로 간다. 아니면 종료한다.

  폴더를 바꾸는 경우 **기존 메모 파일은 새 폴더로 옮겨지지 않는다** — 이전 폴더에 그대로 남고 새 폴더의 목차는 0개로 시작한다. 확인을 받기 전에 이 점을 먼저 알린다.

## 1. 메모 폴더 정하기

사용자에게 **메모(.md)를 저장할 폴더**를 묻는다. 기본값으로 **현재 폴더**를 제안하고, 그 절대경로를 함께 보여준다:

```bash
pwd
```

> 학습 메모를 저장할 폴더를 정해주세요. 기본값은 지금 이 폴더입니다:
> `<pwd 결과>`
> 그대로 쓰려면 Enter, 다른 곳에 두려면 경로를 입력해주세요 (예: `~/notes/articles`).

사용자가 입력한 값이 상대경로이거나 `~`로 시작하면 그대로 다음 단계에 넘긴다 — 절대경로 변환은 스크립트가 한다.

CAUTION : **소스·수집 이력 같은 기계 상태는 묻지 않는다** — 항상 `~/.articles-os/`에 고정된다. 매일 도는 수집이 임의의 작업 디렉토리에서 실행되기 때문에 이 경로는 설정 대상이 아니다.

## 2. 초기화 실행

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_data_folder.py" --notes-path "<1단계에서 정한 폴더>"
```

`ok: false`면 에러를 보여주고 중단한다. 성공하면 반환된 `data_root`·`notes_root`를 이후 안내에 쓰고, 이어서 빈 목차를 만든다:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_index.py"
```

초기화 이후의 구조는 아래와 같다. :

```
~/.articles-os/                 # 기계 상태 (고정 — 설정 불가)
├── config.yaml                 # notes_path + sources(RSS 목록, 초기: 비어 있음) + notify 백엔드
├── articles.json               # 수집 이력·중복 제거
└── state.json                  # last_run + 소스별 실패 상태

<사용자가 정한 폴더>/notes/       # 학습 메모 (사용자 소유 — git에 올려도 됨)
├── index.md                    # 메모 목차 (scripts/update_index.py 가 갱신)
└── YYYY-MM-DD-제목슬러그.md
```

시크릿(알림 웹훅)은 위 어느 쪽에도 저장하지 않는다 — `${CLAUDE_PLUGIN_DATA}`에 따로 보관한다.

## 3. 알림 연결

**REQUIRED SUB-SKILL:** Use articles-os:notify-config

articles-os:notify-config 스킬을 이용해서 알림 설정을 완료한다.

아래 스크립트로 완료 여부를 확인한다. :

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_notify_complete.py" "${CLAUDE_PLUGIN_DATA}"
```

- `{"complete": true, ...}` 면 다음 단계로 진행한다.
- `{"complete": false, "reason": "notify backend not configured" | "webhook not saved" | "unknown backend"}` 면 미완료 상태(notify-config 절차 중간 이탈, 또는 손으로 편집된 `config.yaml`)이므로, 사용자에게 알리고 articles-os:notify-config를 다시 안내한 뒤 재확인한다.
- 그 밖의 `reason`(종료 코드 1)은 완료 여부를 판정하지 못한 것이다. `reason`을 그대로 보여주고 중단한다 — notify-config를 다시 안내해도 해소되지 않는다.

## 4. 스케줄 등록

**REQUIRED SUB-SKILL:** Use articles-os:schedule

articles-os:schedule 스킬을 이용해서 수집 스케줄 등록을 완료한다.

아래 스크립트로 완료 여부를 확인한다. :

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_schedule.py" status
```

- `{"registered": true, ...}` 면 다음 단계로 진행한다.
- `{"error": "unsupported os", ...}` 면 이 환경에서는 스케줄을 등록할 수 없다(macOS 전용). 사용자에게 알리고, 수집이 필요할 때 `/articles-os:collect`를 직접 실행하면 된다고 안내한 뒤 5단계로 넘어간다.
- 그 밖의 `{"registered": false, ...}` 면 미완료 상태이므로, 사용자에게 알리고 articles-os:schedule을 다시 안내한 뒤 재확인한다. 사용자가 등록을 원하지 않으면 그대로 5단계로 넘어간다.

## 5. 마무리

아래 형식 그대로 요약을 보여준다 — 값은 2~4단계에서 확인한 결과로 채운다:

```
articles-os 설정 완료

- 메모 폴더: <notes_root>
- 알림: <Slack | Discord | 알림 없음>
- 수집 스케줄: <매일 HH:MM | 등록 안 함>

다음 단계:
- RSS 소스를 추가하려면: /articles-os:add-source
- 지금 바로 수집을 돌려보려면: /articles-os:collect
- 수집된 글 목록을 확인하려면: /articles-os:browse
```
