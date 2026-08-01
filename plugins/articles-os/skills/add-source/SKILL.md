---
name: add-source
description: >
  articles-os가 수집할 RSS 소스를 추가·삭제·조회할 때 쓰는 스킬.
  "소스 추가해줘", "RSS 등록", "피드 추가", "소스 삭제", "소스 목록 보여줘" 같은 요청이 오면 이 스킬을 실행한다.
argument-hint: [add|remove]
arguments: [action]
metadata:
  version: "0.1.0"
---

## 0. 스킬 실행 조건 확인

아래 스크립트로 초기화 여부를 확인한다:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/paths.py"
```

- `error` 키가 있는 경우 : 설정을 읽지 못한 상태다. `error`를 그대로 보여주고 종료한다.
- `initialized: false` 인 경우 : "먼저 `/articles-os:setup`을 실행하세요" 안내 후 종료한다.
- `initialized: true` 인 경우 : 이후 단계를 순차 진행한다. **데이터 경로는 스크립트들이 스스로 찾으므로 따로 넘기지 않는다.**

## 1. 현재 목록 표시

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" sources list
```

실행 결과가 :

- `ok: false`면 소스 목록을 읽지 못한 것이다. `error`를 그대로 보여주고 **중단**한다 — 소스가 없는 것과 구분한다.
- 그 밖의 경우 `sources`를 `이름 · URL` 으로 bullet list 형식으로 보여준다. 목록이 비어 있으면 그 사실을 안내한다.

## 2. 흐름 판단

`$action`이

- `remove`(또는 "제거"/"삭제")면 [3. 추가](#3-추가)를 건너뛰고 [4. 삭제](#4-삭제)로 간다.
- `add`(또는 "추가"/"등록") 또는 인수가 비어 있으면 [3. 추가](#3-추가)로 간다.

## 3. 추가

### 3-1. RSS URL 입력받기

사용자에게 등록할 RSS URL을 입력받는다. 여러 개를 한 번에 등록할 수 있다는 것, Shift+Enter로 줄을 바꿔가며 URL을 한 줄에 하나씩 입력하면 여러 개를 한 번에 보낼 수 있다는 것을 함께 안내한다.

> 등록할 RSS URL을 입력해주세요. 여러 개를 한 번에 등록하려면 Shift+Enter로 줄바꿈해서 한 줄에 하나씩 입력해주세요.

### 3-2. RSS 검증과 등록

입력받은 URL마다 아래를 반복한다:

1. 검증 : `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fetch_feed.py" "<url>"` 실행. 출력은 **원소 1개짜리 배열**이므로 그 첫 원소를 본다.
   - `ok: false`면 에러를 보여주고 해당 URL은 저장하지 않은 채 다음 URL로 넘어간다. 사용자가 블로그 홈 URL만 줬으면 일반 관례(`/rss.xml`, `/feed`, `/atom.xml`, `/rss`)를 시도해 피드 URL을 찾아본다.
   - `ok: true`면 `name`은 검증 결과의 `feed_title`을 기본 제안하고, 사용자가 바꿀 수 있게 한다.
2. 등록 실행 : `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" sources add --name "<name>" --url "<url>"`
   - `error`가 `duplicate url`이면 이미 등록된 소스다. 중복임을 알리고 해당 URL은 건너뛴 채 다음 URL로 넘어간다.
   - 그 밖의 `ok: false`는 설정 파일에 쓰지 못한 것이다(예: `config.yaml I/O failed: ...`). **중복으로 안내하지 않는다** — `error`를 그대로 보여주고, 남은 URL도 같은 이유로 실패하므로 반복을 중단한다.

모든 URL 처리가 끝나면 [5. 마무리](#5-마무리)로 간다.

## 4. 삭제

### 4-1. 삭제할 소스 선택 및 확인

[1. 현재 목록 표시](#1-현재-목록-표시) 기준으로 번호나 이름으로 삭제할 소스를 지정받는다. 

해당 소스의 이름과 URL을 보여주고 삭제해도 될지 사용자에게 확인받는다.

### 4-2. 삭제 실행

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" sources remove --url "<url>"
```

- `ok: false`면 에러를 보여주고 중단한다. `error`가 `url not found`면 이미 지워졌거나 URL이 어긋난 것이고, 그 밖(예: `config.yaml I/O failed: ...`)은 설정 파일을 읽거나 쓰지 못한 것이다 — 둘을 구분해 안내한다.
- `ok: true`면 [5. 마무리](#5-마무리)로 간다. `articles.json`의 이미 수집된 아티클은 그대로 둔다 — 건드리지 않는다.

## 5. 마무리

`add`/`remove`가 성공한 적이 있으면 그 호출이 반환한 갱신된 `sources`로 목록을 다시 보여준다. 성공한 호출이 하나도 없으면(전부 중복이거나 검증에 실패한 경우) 목록이 그대로임을 알리고, 어떤 URL이 왜 등록되지 않았는지 요약한다.

추가한 경우엔 검증 fetch에서 나온 최신 글 제목 1–2개도 함께 보여줘 "제대로 연결됐다"는 확신을 준다.
