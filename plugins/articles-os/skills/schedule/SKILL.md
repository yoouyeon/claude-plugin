---
name: schedule
description: >
  articles-os의 매일 수집 스케줄(macOS launchd)을 등록·변경·삭제할 때 쓰는 스킬. "스케줄 등록","수집 시간 변경", "매일 몇 시에 수집되게 해줘", "launchd 등록" 같은 요청이 오면 이 스킬을 실행한다.
  수집 시각을 정하는 스킬이다. "지금 수집 돌려줘"처럼 즉시 실행하려는 요청은 이 스킬이 아니라 `articles-os:collect`다.
argument-hint: [register|remove]
arguments: [action]
metadata:
  version: "0.1.0"
---

## 1. 흐름 판단

`$action`이

- `remove`(또는 "제거"/"삭제"/"꺼줘" 등)면 [2. 등록·변경](#2-등록변경)을 건너뛰고 [3. 제거](#3-제거)로 간다.
- `register`(또는 "등록"/"변경") 또는 인수가 비어 있으면 [2. 등록·변경](#2-등록변경)으로 간다.

## 2. 등록·변경

### 2-1. 현재 등록 상태 확인

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_schedule.py" status
```

위 스크립트 결과에서 :

- `"os"`가 `macos`가 아니면 "예약 수집은 macOS에서만 지원합니다."라고 안내한 뒤 종료한다.
- `"registered": true`면 현재 등록된 시각(`hour:minute`)을 보여주고, 시각 변경이 맞는지 사용자에게 확인한 뒤 [2-2. 실행 파일 경로 확정](#2-2-실행-파일-경로-확정) 단계로 이동한다.
- `"registered": false`면 그대로 [2-2. 실행 파일 경로 확정](#2-2-실행-파일-경로-확정) 단계로 이동한다. `error` 키가 함께 있으면 등록된 plist를 읽지 못한 것이다. 등록이 그 파일을 덮어쓰므로 그대로 진행한다.

### 2-2. 실행 파일 경로 확정

2-1 결과의 `"claude_cli"`가 :

- `{"available": true, "path": "..."}`면 그 `path`를 `<CLAUDE_BIN>`으로 쓴다.
- `{"available": false, ...}`면 `claude` 실행 파일을 PATH에서 찾지 못한 것이다. 사용자에게 실행 파일의 절대경로를 입력받아 `<CLAUDE_BIN>`으로 쓴다. 경로를 알 수 없으면 등록해도 예약 실행이 불가능하므로 그 사실을 안내하고 종료한다.

### 2-3. 수집 시각 입력받기 및 확인

사용자에게 매일 아티클을 수집할 시각을 입력받는다(기본 제안: 매일 09:00). 입력받으면 같은 응답에서 등록될 내용을 요약해 보여주고 실행해도 될지 확인받는다:

> 매일 `<HH>:<MM>`에 아티클 수집이 자동 실행되도록 등록합니다. 기존 등록이 있으면 교체됩니다.

확인되면 [2-4. 등록 실행](#2-4-등록-실행)으로 이동한다.

### 2-4. 등록 실행

1. 등록 실행

   CAUTION : **예약 실행은 user scope 설치를 전제로 한다**. OS 스케줄러는 임의의 작업 디렉토리에서 `claude`를 띄우므로, project/local scope로 설치돼 있으면 `/articles-os:collect` 커맨드를 찾지 못한다. 수집 데이터 자체는 고정 경로에 있어 작업 디렉토리와 무관하다.

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_schedule.py" register --claude-bin "<CLAUDE_BIN>" --hour <HH> --minute <MM>
   ```

   위 스크립트 실행 결과가 :

   - `ok: false`이고 `error`가 `hour must be 0-23` 또는 `minute must be 0-59`면 입력한 시각이 범위를 벗어난 것이다. 그 사실을 알리고 [2-3. 수집 시각 입력받기 및 확인](#2-3-수집-시각-입력받기-및-확인)부터 다시 진행한다.
   - `ok: false`이고 `error`가 `not an executable file: ...`이면 실행 파일 경로가 잘못된 것이다. 그 사실을 알리고 [2-2. 실행 파일 경로 확정](#2-2-실행-파일-경로-확정)부터 다시 진행한다.
   - 그 밖의 `ok: false`면 에러를 보여주고 중단한다.
   - `ok: true`면 그대로 2단계를 진행한다.

2. 등록 확인 : 다시 `manage_schedule.py status`를 호출해 `registered: true`와 방금 입력한 시각이 일치하는지 확인한 뒤 사용자에게 최종 결과를 보여준다. 등록 방식(launchd `~/Library/LaunchAgents/com.articles-os.plist`)과 수집 로그 위치(`~/Library/Logs/articles-os.log`)도 참고용으로 함께 안내한다.

## 3. 제거

### 3-1. 현재 등록 상태 확인

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_schedule.py" status
```

위 실행 결과가 :

- `"os"`가 `macos`가 아니면 : "예약 수집은 macOS에서만 지원합니다."라고 안내한 뒤 종료한다.
- `"registered": true`면 : 등록된 시각(`hour:minute`)을 보여주고 수집 스케줄을 제거할지 사용자에게 다시 확인한 후 [3-2. 제거 실행](#3-2-제거-실행) 단계로 이동한다.
- `"registered": false`이고 `error` 키가 있으면 : 등록된 plist를 읽지 못한 것이다. 파일이 남아 있고 예약 실행이 걸려 있을 수 있으므로, 그 사실을 알리고 제거할지 확인한 뒤 [3-2. 제거 실행](#3-2-제거-실행) 단계로 이동한다.
- `"registered": false`이고 `error` 키가 없으면 : "등록된 스케줄이 없습니다"라고 안내한 뒤 종료한다.

### 3-2. 제거 실행

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_schedule.py" remove
```

위 스크립트 실행 결과가 :

- `removed: true`면 제거 완료를 안내한다.
- `ok: true`이고 `removed: false`면 제거할 스케줄이 없었다고 안내한다.
- `ok: false`면 에러를 보여주고 중단한다.
