---
name: notify-config
description: >
  articles-os의 새 글 알림을 설정·변경할 때 쓰는 스킬. "알림 설정해줘",
  "알림 설정", "슬랙 연결", "웹훅 변경", "알림 꺼줘" 같은 요청이 오면 이 스킬을 실행한다.
metadata:
  version: "0.1.0"
---

## 권한 근거

시크릿 저장은 웹훅 URL 붙여넣기 직후 같은 턴에서 검증까지 끝내야 하는 동기적 흐름이라 서브에이전트 위임 이득이 없다. 위험한 JSON 병합·파일 권한(`chmod 600`) 로직은 `scripts/save_secret.py`로 분리했다.

## 0. 상수 확인

아래 스크립트를 실행하고, 그 JSON 결과를 `DATA_FOLDER_INFO`로 기억해둔다:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_data_path.py" '${user_config.data_path}'
```

- `<DATA>` = `DATA_FOLDER_INFO.path`: 확인된 실제 경로 문자열로 치환해서 적는다. (path가 존재하지 않을 수 있다.)
- `<PDATA>` = `${CLAUDE_PLUGIN_DATA}`: 변수를 치환하지 말고 글자 그대로를 리터럴로 넣는다.

## 1. 스킬 실행 조건 확인

`DATA_FOLDER_INFO.configured`가

- `false`인 경우 : "`/plugin configure articles-os@yoouyeon-plugins`를 먼저 실행해주세요"라고 안내한 뒤 종료한다.
- `true`인 경우 : `<DATA>`를 확정하고 이후 단계를 순차 진행한다.

## 2. 알림 파일 확인

`<DATA>/config.yaml` 파일이 존재하는지 확인한다.

- 존재하지 않는 경우 : "먼저 `/articles-os:setup`을 실행하세요" 안내 후 종료한다.
- 존재하는 경우 : 다음 3단계를 진행한다.

## 3. 현재 상태 확인

아래 스크립트로 현재 `notify.backend`를 확인한다:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" notify get <DATA>
```

- `{"backend": "none"}` 인 경우 : "현재 알림: 꺼짐"이라고 보여주고 다음 4단계로 진행한다.
- `{"backend": "slack"}` 인 경우 : 아래 스크립트로 시크릿 존재 여부를 추가 확인한다 (URL 값은 출력하지 않는다)

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/save_secret.py" has <PDATA>
  ```
  
  - `{"exists": true}` : "현재 알림: Slack 연결됨"이라고 보여주고 다음 4단계로 진행한다.
  - `{"exists": false}` : "현재 알림: Slack으로 설정되어 있지만 저장된 웹훅이 없습니다 — 다시 연결해주세요"라고 안내하고, 백엔드 선택 없이 곧바로 아래 `### Slack 선택 시`로 진행한다.

## 4. 알림 방식 설정

3단계 결과에 따라 다음 중 하나를 사용자에게 묻는다 (`{"exists": false}`였던 경우는 3단계에서 이미 이 단계를 건너뛰고 `### Slack 선택 시`로 이동했으므로 여기서 다루지 않는다):

- 3단계가 `{"backend": "none"}`이었던 경우:

  > 알림을 받을 방법을 선택해주세요:
  > 1. Slack
  > 2. 계속 끄기

  - `1` 선택 : 아래 `### Slack 선택 시`로 진행한다.
  - `2` 선택 : 변경 없이 종료한다.

- 3단계가 `{"backend": "slack"}` + `{"exists": true}`였던 경우:

  > 지금 Slack으로 연결되어 있습니다. 어떻게 할까요?
  > 1. 그대로 유지
  > 2. 다시 연결(웹훅 교체)
  > 3. 알림 끄기

  - `1` 선택 : "변경 사항이 없습니다"라고 안내한 뒤 종료한다.
  - `2` 선택 : 아래 `### Slack 선택 시`로 진행한다.
  - `3` 선택 : 아래 `### none 선택 시`로 진행한다.

## 5. 알림 방식별 설정

### Slack 선택 시

1. 안내: "Slack Incoming Webhook URL을 붙여넣어 주세요. Slack → 앱 관리 → Incoming Webhooks에서 발급할 수 있습니다."
2. 설정 스크립트 실행:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/save_secret.py" save <PDATA> --url "<입력값>"
  ```

  실행 결과가 `ok: false`(`error: "invalid webhook url ..."`)면 형식이 잘못됐다고 알리고 재입력을 받는다.

CAUTION : **저장된 웹훅 URL 전체를 대화·출력에 다시 표시하지 않는다**

3. `config.yaml`의 `notify.backend`를 `slack`으로 갱신:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" notify set <DATA> --backend slack
  ```

CAUTION : **웹훅 URL은 `config.yaml`·데이터 폴더에 절대 넣지 않는다.**

4. 테스트 알림으로 검증:

CAUTION : **반드시 아래 `notify.py`로만 검증한다 — 직접 curl로 웹훅을 호출하지 않는다.**

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/notify.py" "<DATA>" <PDATA> --test
  ```

  검증이 실패하면 에러를 보여주고 URL 재입력을 받는다. 성공하면 "알림이 연결됐습니다"라고 안내한다.

### none 선택 시

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" notify set <DATA> --backend none
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/save_secret.py" delete <PDATA>
```

웹훅 입력 단계는 건너뛴다. 기존 시크릿은 지운다. 완료 후 "알림을 껐습니다"라고 안내한다.
