---
name: notify-config
description: >
  This skill should be used when the user asks to "configure notifications", "알림 설정",
  "슬랙 연결", "웹훅 변경", "알림 꺼줘", or wants to change how articles-os notifies
  about new articles. Standalone re-entry point; also reused by the setup onboarding.
metadata:
  version: "0.1.0"
---

## 권한 근거

시크릿 저장은 사용자가 웹훅 URL을 붙여넣은 직후 같은 턴에서 검증까지 끝내야 하는 동기적 흐름이라, 서브에이전트로 위임하면 대화 왕복만 늘고 이득이 없다. 위험한 JSON 병합·파일 권한(`chmod 600`) 로직 자체는 `scripts/save_secret.py`로 분리했다.

# 알림 백엔드 설정

`notify.yaml`(백엔드 선택) + `~/.articles-os/secrets.json`(웹훅 시크릿) 관리.
공통 규칙은 `${CLAUDE_PLUGIN_ROOT}/docs/conventions.md` 참조.

## 절차

1. **활성 설치 결정**: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_install.py"` — `none`이면 `/articles-os:setup` 유도.
2. **현재 상태 표시**: `notify.yaml`의 `backend`와, Slack이면 `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/save_secret.py" has "<install_id>"`로 시크릿 존재 여부만 확인(URL 값 자체는 출력하지 않는다).
3. **백엔드 선택**: `slack` 또는 `none`. 순수 터미널 전제라 데스크톱 알림 옵션은 없다.

### Slack 선택 시

1. 안내: "Slack Incoming Webhook URL을 붙여넣어 주세요. Slack → 앱 관리 → Incoming Webhooks에서 발급할 수 있습니다."
2. 저장 — 활성 설치의 `install_id`로 실행 (검증·병합·`chmod 600`을 스크립트가 전담):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/save_secret.py" save "<install_id>" --url "<입력값>"
```

`ok: false`(`error: "invalid webhook url ..."`)면 형식이 잘못됐다고 알리고 재입력을 받는다.

3. `notify.yaml`을 `backend: slack`으로 갱신. **웹훅 URL은 notify.yaml·데이터 폴더에 절대 넣지 않는다.**
4. 테스트 알림으로 검증:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/notify.py" "<DATA>" --test
```

실패하면 에러를 보여주고 URL 재입력을 받는다. 성공하면 "웹훅은 언제든 Slack에서 폐기·재발급할 수 있고, 그 경우 이 스킬을 다시 실행하면 된다"고 안내한다.

### none 선택 시

`notify.yaml`을 `backend: none`으로 갱신. 웹훅 입력 단계는 건너뛴다. 기존 시크릿은 지우지 않는다(다시 slack으로 돌아올 때 재사용 여부를 물어본다).

## 주의

- 대화·출력에 저장된 웹훅 URL 전체를 다시 표시하지 않는다 (마지막 8자 정도만).
- 알림 발송은 항상 `scripts/notify.py`를 통한다 — 직접 curl 하지 않는다.
