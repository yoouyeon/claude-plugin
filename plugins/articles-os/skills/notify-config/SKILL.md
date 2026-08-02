---
name: notify-config
description: >
  articles-os의 새 글 알림을 설정·변경할 때 쓰는 스킬. "알림 설정해줘", "알림 설정", "슬랙 연결", "디스코드 연결", "웹훅 변경", "알림 꺼줘" 같은 요청이 오면 이 스킬을 실행한다.
metadata:
  version: "0.1.0"
---

## 표기 규칙

`<PDATA>` = `${CLAUDE_PLUGIN_DATA}`: 변수를 치환하지 말고 글자 그대로를 리터럴로 넣는다.

## 1. 현재 상태 확인

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_notify_complete.py" "<PDATA>"
```

- `{"complete": false, "reason": "notify backend not configured"}` : "현재 알림: 아직 설정되지 않음"이라고 보여주고 2단계로 진행한다.
- `{"complete": true, "backend": "none"}` : "현재 알림: 꺼짐"이라고 보여주고 2단계로 진행한다.
- `{"complete": true, "backend": "slack" | "discord"}` : "현재 알림: <Slack | Discord> 연결됨"이라고 보여주고 2단계로 진행한다.
- `{"complete": false, "backend": "slack" | "discord", "reason": "webhook not saved"}` : "현재 알림: <Slack | Discord>로 설정되어 있지만 저장된 웹훅이 없습니다 — 다시 연결해주세요"라고 안내하고, 백엔드 선택 없이 곧바로 아래 `### 웹훅 백엔드 선택 시`를 그 백엔드로 진행한다.
- `{"complete": false, "backend": "...", "reason": "unknown backend"}` : `config.yaml`에 이 플러그인이 모르는 백엔드가 적혀 있다. 그 값을 보여주고 2단계로 진행해 다시 고르게 한다.
- 그 밖의 `reason`(종료 코드 1) : 현재 상태를 판정하지 못한 것이다. `reason`을 그대로 보여주고 종료한다.

## 2. 알림 방식 설정

1단계 결과에 따라 다음 중 하나를 사용자에게 묻는다:

- 1단계가 "아직 설정되지 않음"·"꺼짐"·"모르는 백엔드"였던 경우:

  > 알림을 받을 방법을 선택해주세요:
  > 1. Slack
  > 2. Discord
  > 3. 알림 없이 사용하기

  - `1` 선택 : 아래 `### 웹훅 백엔드 선택 시`를 `slack`으로 진행한다.
  - `2` 선택 : 아래 `### 웹훅 백엔드 선택 시`를 `discord`로 진행한다.
  - `3` 선택 : 아래 `### none 선택 시`로 진행한다.

- 1단계가 "연결됨"이었던 경우 (`<현재>`는 Slack 또는 Discord):

  > 지금 `<현재>`로 연결되어 있습니다. 어떻게 할까요?
  > 1. 그대로 유지
  > 2. 다시 연결(알림 방식·웹훅 다시 선택)
  > 3. 알림 끄기

  - `1` 선택 : "변경 사항이 없습니다"라고 안내한 뒤 종료한다.
  - `2` 선택 : 위 3지선다를 다시 물어 백엔드부터 고르게 한다.
  - `3` 선택 : 아래 `### none 선택 시`로 진행한다.

## 3. 알림 방식별 설정

### 웹훅 백엔드 선택 시

`<BACKEND>`는 고른 백엔드(`slack` 또는 `discord`)다.

1. 발급 위치를 안내하고 URL을 받는다:

  - `slack` : "Slack Incoming Webhook URL을 붙여넣어 주세요. Slack → 앱 관리 → Incoming Webhooks에서 발급할 수 있습니다."
  - `discord` : "Discord Webhook URL을 붙여넣어 주세요. 서버 설정 → 연동(Integrations) → 웹후크(Webhooks)에서 발급할 수 있습니다."

  어느 쪽이든 뒤에 덧붙인다: "지금 발급이 어려우면 알림 없이 사용도 가능합니다. — 나중에 `/articles-os:notify-config`로 다시 설정할 수 있습니다."

  URL 대신 알림 없이 사용하겠다는 답이 오면 아래 `### none 선택 시`로 진행한다. 이 이탈 경로는 아래 재입력 단계에서도 계속 열려 있다.

2. 설정 스크립트 실행:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/save_secret.py" save "<PDATA>" --backend <BACKEND> --url "<입력값>"
  ```

  실행 결과가 `ok: false`(`error: "invalid webhook url ..."`)면 형식이 잘못됐다고 알리고 재입력을 받는다. 다른 서비스의 웹훅을 붙여넣은 경우도 여기서 걸린다.

CAUTION : **저장된 웹훅 URL 전체를 대화·출력에 다시 표시하지 않는다**

3. `config.yaml`의 `notify.backend`를 `<BACKEND>`로 갱신:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" notify set --backend <BACKEND>
  ```

CAUTION : **웹훅 URL은 `config.yaml`·데이터 폴더에 절대 넣지 않는다.**

4. 테스트 알림으로 검증:

CAUTION : **반드시 아래 `notify.py`로만 검증한다 — 직접 curl로 웹훅을 호출하지 않는다.**

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/notify.py" "<PDATA>" --test
  ```

  검증이 실패하면 에러를 보여주고 URL 재입력을 받는다. 성공하면 "알림이 연결됐습니다"라고 안내한다.

### none 선택 시

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" notify set --backend none
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/save_secret.py" delete "<PDATA>"
```

웹훅 입력 단계는 건너뛴다. 둘 다 성공하면 "알림을 껐습니다"라고 안내한다.
`delete`가 `ok: false`면 저장돼 있던 웹훅을 지우지 못한 것이다 — 에러를 그대로 보여주고, 알림은 꺼졌지만 웹훅이 남아 있다고 알린다.
