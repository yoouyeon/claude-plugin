---
name: schedule
description: >
  articles-os의 매일 수집 스케줄(launchd/cron)을 등록·변경·삭제할 때 쓰는 스킬. "스케줄 등록",
  "수집 시간 변경", "매일 몇 시에 수집되게 해줘", "launchd/cron 등록" 같은 요청이 오면 이 스킬을
  실행한다.
argument-hint: [register|remove]
arguments: [action]
metadata:
  version: "0.1.0"
---

## 권한 근거

등록될 내용을 사용자에게 보여주고 확인받은 즉시 실행해야 하는 동기적 흐름이라 서브에이전트 위임 이득이 없다. OS 판별·plist 작성·launchctl/crontab 호출·중복 방지 로직은 전부 `scripts/manage_schedule.py`로 분리했다.

## 0. 스킬 실행 조건 확인

아래 스크립트로 데이터 폴더 설정 여부를 확인한다:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_data_path.py" '${user_config.data_path}'
```

데이터 폴더 설정 여부가

- `{"configured": false}` 인 경우 : "`/plugin configure articles-os@yoouyeon-plugins`를 먼저 실행해주세요"라고 안내한 뒤 종료한다.
- `{"configured": true, "path": "..."}` 인 경우 : 그 `path`를 `<DATA>`로 쓰고 이후 단계를 순차 진행한다.

## 1. 설정 파일 확인

`<DATA>/config.yaml` 파일이 존재하는지 확인한다.

- 존재하지 않는 경우 : "먼저 `/articles-os:setup`을 실행하세요" 안내 후 종료한다.
- 존재하는 경우 : 다음 단계로 진행한다.

## 2. 흐름 판단

`$action`이

- `remove`(또는 "제거"/"삭제"/"꺼줘" 등)면 [3-1. 등록·변경](#3-1-등록변경)을 건너뛰고 [3-2. 제거](#3-2-제거)로 간다.
- `register`(또는 "등록"/"변경") 또는 인수가 비어 있으면 [3-1. 등록·변경](#3-1-등록변경)으로 간다.

## 3-1. 등록·변경

### 3-1-1. 현재 등록 상태 확인

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_schedule.py" status
```

위 스크립트 결과에서 :

- `"os"`가 `macos`/`linux`가 아니면(예: `windows`) "Windows는 지원 범위 밖입니다. macOS 또는 Linux에서 사용이 가능합니다."라고 안내한 뒤 종료한다.
- `"registered": true`면 현재 등록된 시각(`hour:minute`)을 보여주고, 시각 변경이 맞는지 사용자에게 확인한 뒤 [3-1-2. 실행 파일 경로 확정](#3-1-2-실행-파일-경로-확정) 단계로 이동한다.
- `"registered": false`면 그대로 [3-1-2. 실행 파일 경로 확정](#3-1-2-실행-파일-경로-확정) 단계로 이동한다.

### 3-1-2. 실행 파일 경로 확정

```bash
command -v claude              # <CLAUDE_BIN>
```

### 3-1-3. 수집 시각 입력받기 및 확인

사용자에게 매일 아티클을 수집할 시각을 입력받는다(기본 제안: 매일 09:00). 입력받으면 같은 응답에서 등록될 내용을 요약해 보여주고 실행해도 될지 확인받는다:

> 매일 `<HH>:<MM>`에 아티클 수집이 자동 실행되도록 등록합니다. 기존 등록이 있으면 교체됩니다.

확인되면 [3-1-4. 등록 실행](#3-1-4-등록-실행)으로 이동한다.

### 3-1-4. 등록 실행

1. 등록 실행

CAUTION : **데이터 경로는 등록 커맨드 인자로 넘기지 않는다** — `${user_config.data_path}` 치환이 헤드리스 `-p` 실행에서도 동작하기 때문.

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_schedule.py" register --claude-bin "<CLAUDE_BIN>" --hour <HH> --minute <MM>
   ```

   위 스크립트 실행 결과가 :

   - `ok: false`면 에러를 보여주고 중단한다.
   - `ok: true`면 그대로 2단계를 진행한다.

2. 등록 확인 : 다시 `manage_schedule.py status`를 호출해 `registered: true`와 방금 입력한 시각이 일치하는지 확인한 뒤 사용자에게 최종 결과를 보여준다. 등록 방식(macOS는 launchd `~/Library/LaunchAgents/com.articles-os.plist`, Linux는 crontab)과 수집 로그 위치(macOS는 `~/Library/Logs/articles-os.log`, Linux는 `~/.articles-os.log`)도 참고용으로 함께 안내한다.

## 3-2. 제거

### 3-2-1. 현재 등록 상태 확인

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_schedule.py" status
```

위 실행 결과가 :

- `"registered": false`면 : "등록된 스케줄이 없습니다"라고 안내한 뒤 종료한다.
- `"registered": true`면 : 등록된 시각(`hour:minute`)을 보여주고 수집 스케줄을 제거할지 사용자에게 다시 확인한 후 [3-2-2. 제거 실행](#3-2-2-제거-실행) 단계로 이동한다.

### 3-2-2. 제거 실행

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_schedule.py" remove
```

위 스크립트 실행 결과가 :

- `removed: true`면 제거 완료를 안내한다.
- `ok: false`면 에러를 보여주고 중단한다.
