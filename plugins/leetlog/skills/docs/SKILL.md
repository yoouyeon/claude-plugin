---
name: docs
description: >
  LeetCode 풀이를 `docs/` 아래 풀이 문서로 남기는 스킬.
  "문서로 남겨줘", "풀이 정리해줘", "docs" 같은 요청이 오면 이 스킬을 실행한다.
argument-hint: [문제 번호 또는 파일 경로]
arguments: [target]
allowed-tools: Read, Glob, Bash(git rev-parse:*), Bash(python3:*), Bash(echo:*)
metadata:
  version: "0.2.0"
---

- `ROOT`: !`git rev-parse --show-toplevel 2>/dev/null || pwd`

아래 스크립트를 실행하고 출력된 절대 경로를 `SOLUTION_DIR`로 쓴다. 종료 코드가 0이 아니면 오류를 알리고 중단한다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/solution_dir.py" "<ROOT>"
```

## 1. 대상 특정

대상은 풀이 파일 하나다.

`target`이 파일 경로면 그 파일이다.

`target`이 숫자면 `SOLUTION_DIR/*/<숫자>_*.*`를 Glob한다.

- 결과가 없으면 그 사실을 알리고 중단한다.
- 하나면 그 파일로 진행한다.
- 여럿이면(같은 문제를 여러 언어로 푼 경우) **경로 목록을 보여주고 고르게 한다.** 방금 그 파일을 다뤘더라도 맥락에서 고르지 않고 매번 묻는다.

`target`이 없으면 대화 맥락에서 방금 다룬 문제 번호를 쓴다. 맥락에 없으면 문제 번호를 묻고 중단한다.

## 2. 펜스 태그

`${CLAUDE_PLUGIN_ROOT}/reference/languages.md`를 읽어 대상 파일 확장자에 해당하는 펜스 태그를 확보한다.

표에 없는 확장자면 **사용자에게 묻고, 답을 받기 전에는 3단계로 가지 않는다.** 확장자에서 태그를 유추하지 않는다 — 표 안에도 `.cs`→`csharp`, `.kt`→`kotlin`처럼 확장자와 태그가 다른 경우가 있다. 답이 뻔해 보여도, 후보가 하나뿐으로 보여도 묻는다.

## 3. 문서 쓰기

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/docs/scripts/write_doc.py" "<대상 파일 경로>" --fence <펜스 태그> --root "<ROOT>"
```

문서를 직접 만들거나 고치지 않는다. 이 스크립트만 문서를 수정한다.

종료 코드로 분기한다.

- `0`: 출력의 `+` 줄을 사용자에게 보여주고 4단계로 간다. `!` 줄이 있으면 헤더와 문서 frontmatter가 어긋났다는 뜻이므로 그대로 전하고, 어느 쪽도 고치지 않는다
- `1`: 출력 메시지를 그대로 전하고 종료한다.

종료 코드가 `1`이고 메시지가 헤더에서 읽지 못한 항목을 가리키면, 그 값을 **사용자에게 묻는다.** 답을 받은 뒤에만 `--title`·`--difficulty`·`--url`·`--tags`로 넘겨 한 번 다시 실행한다. 그 외의 실패는 재시도하지 않는다.

**그 문제를 안다고 여겨 스스로 채우지 않는다.** 번호·slug로 제목이나 난이도를 짐작해 넣지 않는다. 값은 사용자에게서만 온다.

## 4. 문서 본문 임의 수정 금지

- `<!-- Write your notes here -->` 자리를 채우지 않는다.
- 기존 날짜 섹션과 사용자가 쓴 본문을 고치지 않는다.

## 5. 마무리

문서 경로와 추가된 날짜 섹션을 알리고, 빈 칸에 직접 메모를 적으면 된다고 안내한다.

현재 문서 상태는 초안이므로, 바로 **커밋하지 않는다.**
