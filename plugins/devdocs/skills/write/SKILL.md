---
name: write
description: >
  개발 산출물 문서를 한국어로 새로 쓸 때 쓰는 스킬. 스펙·설계 문서, 리서치 메모, PR 본문, 이슈 본문, README가 대상이다.
  "스펙 문서 써줘", "설계 문서 작성해줘", "PR 본문 써줘", "PR 설명 작성", "이슈 써줘", "조사한 거 메모로 정리해줘", "README 써줘" 같은 요청이 오면 실행한다.
  이미 있는 문서를 고치는 요청과 커밋 메시지에는 쓰지 않는다.
argument-hint: "[존댓말] [문서 종류]"
allowed-tools: Read, Write, Edit, Bash(pwd), Bash(python3:*)
metadata:
  version: "0.1.0"
---

- `ROOT`: !`pwd`

모호한 것은 추측하지 않고 사용자에게 묻는다.

## 1. 문서 종류

요청과 스킬 인자에서 문서 종류를 `spec`, `memo`, `pr`, `issue`, `readme` 중 하나로 정한다. 하나로 정해지지 않으면 묻는다. 다섯 종류에 들지 않는 문서면 이 스킬의 대상이 아니라고 알리고 중단한다.

## 2. 버전

요청이나 스킬 인자에 "존댓말"이 있으면 존댓말 버전, 없으면 기본 버전이다.

## 3. 작성

`${CLAUDE_PLUGIN_ROOT}/reference/writing.md`를 읽는다. `model-check.md`는 이 단계에서 읽지 않는다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/write/scripts/draft.py" new "<ROOT>" <종류>
```

출력된 경로를 `DRAFT`로 쓴다. `writing.md`의 문체 표와 작성 지침을 따라 본문을 `DRAFT`에 쓴다. 내용은 대화와 사용자가 준 자료에서만 가져오고, 모르는 내용은 묻는다.

## 4. 1차 검사

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" "<DRAFT>" --type <종류> [--polite]
```

존댓말 버전이면 `--polite`를 붙인다. 종료 코드가 `2`면 출력을 전하고 중단한다.

`${CLAUDE_PLUGIN_ROOT}/reference/model-check.md`를 읽고 `DRAFT`를 다시 읽으며 그 항목을 찾는다. 스크립트 출력과 함께 고칠 후보로 삼아, 고칠 곳만 `DRAFT`에서 고친다.

## 5. 2차 검사

4단계의 스크립트를 한 번 더 실행한다. 여기서 걸린 것은 고치지 않고 줄 번호, 항목, 내용을 목록으로 보여 준다.

## 6. 전달

`pr`, `issue`: `DRAFT` 경로를 알려 주고 끝낸다. `gh pr create --body-file`, `gh issue create --body-file`에 쓸 수 있다고 안내한다. 게시하지 않는다.

`spec`, `memo`, `readme`: 저장할 경로를 묻는다. 답을 받으면 옮긴다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/write/scripts/draft.py" move "<DRAFT>" "<최종 경로>"
```

- `0`: 출력된 경로를 알린다.
- `3`: 그 경로에 파일이 있다고 알리고 덮어쓸지 묻는다. 덮어쓰라고 하면 `--force`를 붙여 다시 실행하고, 아니면 다른 경로를 묻는다.
- `2`: 출력을 전하고 `DRAFT` 경로를 알린다.
