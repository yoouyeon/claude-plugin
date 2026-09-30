---
name: done
description: >
  LeetCode 문제를 다 푼 뒤 소요 시간을 마감하고 코드 피드백을 주는 스킬.
  "다 풀었어", "풀이 끝", "제출했어", "done" 같은 요청이 오면 이 스킬을 실행한다.
argument-hint: [문제 번호 또는 파일 경로]
arguments: [target]
allowed-tools: Read, Glob, Grep, Skill, Bash(git rev-parse:*), Bash(python3:*), Bash(echo:*)
metadata:
  version: "0.2.0"
---

- `ROOT`: !`git rev-parse --show-toplevel 2>/dev/null || pwd`

아래 스크립트를 실행하고 출력된 절대 경로를 `SOLUTION_DIR`로 쓴다. 종료 코드가 0이 아니면 오류를 알리고 중단한다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/solution_dir.py" "<ROOT>"
```

## 1. 대상 특정

대상은 파일 하나다.

`target`이 파일 경로면 그 파일이다.

`target`이 숫자면 `SOLUTION_DIR/*/<숫자>_*.*`를 Glob한다. 결과가 없으면 그 사실을 알리고 중단한다. 여럿이면(같은 문제를 여러 언어로 푼 경우) 아래 Grep 패턴으로 미마감 ANCHOR가 있는 것만 남긴다.

`target`이 없으면 `SOLUTION_DIR` 아래를 Grep으로 검색한다.

```
ANCHOR \d{4}\.\d{2}\.\d{2} \d{2}:\d{2} 풀이
```

- 파일이 하나면 그 파일로 진행한다.
- 여럿이면 **경로와 매치된 ANCHOR 줄을 목록으로 보여주고 고르게 한다.**
- 하나도 없으면 마감할 풀이가 없다고 알리고 종료한다.

## 2. ANCHOR 마감

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/done/scripts/close_anchor.py" "<대상 파일 경로>"
```

파일을 직접 고치지 않는다. 이 스크립트만 ANCHOR를 수정한다.

종료 코드로 분기한다.

| 종료 코드 | 처리 |
|---|---|
| `0` | 출력의 `+` 줄을 사용자에게 보여주고 3단계로 간다 |
| `2` | 이미 마감된 파일이라고 알리고 3단계로 간다 |
| `1` | 출력 메시지를 그대로 전하고 **종료한다** |

## 3. 코드 피드백

대상 파일을 읽는다. 재풀이 파일이면 맨 위 ANCHOR 아래의 이번 풀이만 대상으로 한다.

두 관점으로 나눠 제시한다.

**리뷰 (correctness / performance)**

- 시간·공간 복잡도 분석. 개선 가능하면 제안한다 (예: O(n²) → O(n)).
- 대안 자료구조나 패턴을 제안한다 (Set/Map, 투 포인터, 슬라이딩 윈도우 등).

**개선 (elegance / maintainability)**

- 가독성·네이밍·해당 언어의 관용 표현.
- 추상적인 조언이 아니라 구체적인 리팩토링 코드 스니펫으로 제시한다.
- 단순 스타일 변경은 명확성이나 성능 향상이 없으면 제안하지 않는다.

**대화에만 출력한다.** 풀이 파일에도 문서에도 쓰지 않는다. 사용자가 요청하지 않으면 코드를 고치지 않는다.

## 4. 커밋

커밋할지 묻는다. 사용자가 원하지 않으면 건너뛴다.

**REQUIRED SUB-SKILL:** Use leetlog:commit

대상 파일 경로 하나만 인자로 넘긴다.

## 5. 마무리

풀이 문서를 남기려면 `/leetlog:docs`를 부르면 된다고 안내한다.
