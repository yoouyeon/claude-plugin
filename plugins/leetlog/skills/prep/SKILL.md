---
name: prep
description: >
  LeetCode 문제를 풀기 전에 코드 파일을 준비하는 스킬.
  "이 문제 풀 준비 해줘", "leetcode 시작", "이거 다시 풀래", 문제 URL이나 slug만 던지는 요청이 오면 이 스킬을 실행한다.
argument-hint: <문제 URL 또는 slug> [언어]
arguments: [target, language]
allowed-tools: Read, Write, Edit, Glob, Bash(git rev-parse:*), Bash(date:*), Bash(python3:*), Bash(echo:*)
metadata:
  version: "0.1.0"
---

- `ROOT`: !`git rev-parse --show-toplevel 2>/dev/null || pwd`
- `현재 시각`: !`date "+%Y.%m.%d %H:%M"`

## 1. 인자 해석

`target`에서 slug를 뽑는다. `https://leetcode.com/problems/<slug>/` 뒤에 `description/`·`submissions/`·쿼리스트링이 붙어 있어도 `problems/` 다음 한 마디가 slug다.

`target`이 없으면 문제 URL을 묻고 중단한다.

`language`가 있으면 그것을, 없으면 2단계 설정값을 쓴다.

## 2. 설정

`ROOT/.leetlog.json`을 읽는다. 없으면 어떤 언어로 주로 풀지 묻고 답을 담아 만든다.

```json
{ "default_language": "typescript", "solutions_dir": "solutions" }
```

`language`가 있으면 이번 실행에만 그 값을 쓰고 `.leetlog.json`은 수정하지 않는다.

아래 스크립트를 실행하고 출력된 절대 경로를 `SOLUTION_DIR`로 쓴다. 설정 파일이 없거나 `solutions_dir` 키가 없으면 기본값인 `ROOT/solutions`가 나온다. 종료 코드가 0이 아니면 오류를 알리고 중단한다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/solution_dir.py" "<ROOT>"
```

## 3. 언어 매핑

`${CLAUDE_PLUGIN_ROOT}/reference/languages.md`를 읽어 `langSlug`, 확장자, 줄 주석, 블록 주석을 확보한다.

표에 없는 언어라면 적힌 값을 `langSlug`로 그대로 쓰고, 확장자와 주석 문법을 사용자에게 묻는다.

## 4. 재풀이 판정

`SOLUTION_DIR/*/*_<slug>.<ext>`를 Glob으로 찾는다.

- 파일이 있으면 재풀이이고 그 파일이 수정 대상이다.
- 없으면 첫 풀이다.

## 5. 메타 조회

아래 스크립트를 한 번만 실행한다. `<langSlug>`는 3단계에서 확보한 값이다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fetch_question.py" "<slug>" --lang "<langSlug>"
```

**실패해도 재시도하지 않는다.**

종료 코드가 0이 아니거나(응답 없음) 출력의 `question`이 `null`이면 문제 번호·제목·난이도를 사용자에게 묻는다. 태그는 비우고, 시그니처를 못 받았으므로 7단계에서 함수 자리를 빈 줄로 둔다.

## 6. 시그니처 선택

`codeSnippets`에 남은 항목의 `code`를 쓴다. 스크립트가 이미 `langSlug`로 걸러 두었다.

`codeSnippets`가 비어 있으면 `availableLangs`의 언어 목록을 보여주고 고르게 한 뒤, 3단계 매핑과 4단계 판정을 그 언어로 다시 한다. 다시 조회하지 않고, 필요하면 `--lang` 없이 한 번 더 실행해 고른 언어의 `code`를 얻는다.

## 7. 파일 쓰기

### 7-1. 첫 풀이

`SOLUTION_DIR/<difficulty>/<questionFrontendId>_<slug>.<ext>`를 만든다. `difficulty`는 `Easy`/`Medium`/`Hard` 그대로 설정한다.

메타는 블록 주석, ANCHOR는 줄 주석으로 쓴다. 주석 문법은 3단계에서 확보한 언어 것을 쓴다.

```ts
/*
문제 : 54 - Spiral Matrix
난이도 : Medium
링크 : https://leetcode.com/problems/spiral-matrix/
태그 : Array, Matrix, Simulation
*/

// ANCHOR 2026.08.08 14:30 풀이
function spiralOrder(matrix: number[][]): number[] {

};
```

- 링크는 `https://leetcode.com/problems/<slug>/`로 고정한다.
- 태그는 `topicTags`의 `name`을 쉼표로 잇는다. 없으면 `태그 :` 줄까지 뺀다.
- ANCHOR 날짜·시각은 맨 위 `현재 시각` 값을 그대로 쓴다.
- 함수 본문은 **반드시** 비워 둔다. 시그니처를 못 받았으면 함수 자리를 빈 줄로 둔다.

### 7-2. 재풀이

대상 파일에서 `ANCHOR`가 들어간 줄의 개수를 센다. 그 값 + 1 이 이번 순번이다.

새 스니펫이 도입하는 **모든 이름**(함수·클래스·타입·헬퍼)에 순번을 접미사로 붙인다. 어느 이름에 붙일지는 `reference/languages.md`의 계열 표를 따른다. 기존 파일에 있는 이름과 하나라도 겹치면 안 된다.

새 풀이는 헤더 블록 주석 바로 아래, 기존 첫 ANCHOR 위에 빈 줄 하나를 두고 넣는다. **기존 코드는 한 글자도 고치지 않는다.**

```ts
/*
문제 : 54 - Spiral Matrix
...
*/

// ANCHOR 2026.08.08 14:30 풀이
function spiralOrder2(matrix: number[][]): number[] { }

// ANCHOR 2026.04.06 풀이 (21분 소요)
function spiralOrder(matrix: number[][]): number[] { }
```

조회에 성공했고 헤더의 난이도나 태그가 응답과 다르면 그 줄만 최신값으로 고친다. 난이도가 바뀌어 파일이 든 폴더와 어긋나면 **파일을 옮기지 않고** 사용자에게 그 사실만 알린다.

## 8. 마무리

만든(또는 고친) 파일 경로를 알린다. 재풀이면 이번이 몇 번째 풀이인지 함께 알린다.

응답으로 받은 `hints` 배열은 이 대화 맥락에만 둔다. **파일에 저장하지 않고, 사용자에게 미리 보여주지도 않는다.** `/leetlog:hint`가 같은 세션에서 여기서 꺼내 쓴다.

완료 후 후속 액션을 안내한다: 다 풀면 `/leetlog:done`, 막히면 `/leetlog:hint`.
