# leetlog

LeetCode 문제 URL 하나만 주면 풀이 파일을 만들고, 풀다 막히면 힌트를 단계별로 받고, 다 풀면 걸린 시간을 기록합니다. 풀이 문서와 커밋까지 이어서 남길 수 있습니다.

## 실행 흐름

```
/leetlog:prep <문제 URL>   문제 정보를 받아 코드 파일을 만듭니다
      ↓
    (풀이)                 막히면 /leetlog:hint
      ↓
/leetlog:done              걸린 시간을 기록하고 코드 피드백을 줍니다
      ↓
/leetlog:docs              풀이 문서를 만듭니다                (선택)
      ↓
/leetlog:commit            문서를 커밋합니다                   (선택)
```

## 시작하기

```
/plugin marketplace add yoouyeon/claude-plugin
/plugin install leetlog@yoouyeon-plugins
```

처음 `prep` 실행할 때 어떤 언어로 주로 풀지 한 번 확인하고, 그 답을 `.leetlog.json`에 담아 기본 언어로 설정합니다.

기본 언어로 TypeScript를 선택했다면 `.leetlog.json`은 다음과 같이 생성됩니다.

```json
{
  "default_language": "typescript",
  "solutions_dir": "solutions"
}
```

풀이 파일을 다른 곳에 저장하려면 저장소 루트의 `.leetlog.json`에서 `solutions_dir`을 원하는 상대 경로로 수정합니다(예: `leetcode/solutions`). 값을 생략해도 `solutions`를 사용합니다. 설정을 바꿔도 기존 파일은 자동으로 이동하지 않으므로, 기존 풀이를 계속 사용하려면 새 디렉토리로 옮겨야 합니다. 풀이 문서는 계속 `docs/`에 저장됩니다.

## 스킬 모음

| 스킬 | 사용 시점 |
|---|---|
| `/leetlog:prep` | 문제를 풀기 시작할 때 |
| `/leetlog:hint` | 풀다가 막혔을 때 |
| `/leetlog:done` | 다 풀었을 때 |
| `/leetlog:docs` | 풀이를 문서로 남기고 싶을 때 |
| `/leetlog:commit` | 풀이나 문서를 커밋하고 싶을 때 |

### 준비

문제 URL을 주면 정보를 받아 함수 시그니처가 담긴 코드 파일을 만듭니다.

```
/leetlog:prep https://leetcode.com/problems/spiral-matrix/
```

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

뒤에 언어를 붙이면 기본 언어 대신 그 실행에만 적용됩니다.

```
/leetlog:prep https://leetcode.com/problems/spiral-matrix/ python
```

### 힌트

LeetCode 공식 힌트를 한 번에 하나씩 줍니다.
힌트를 다 쓰고도 막혀 있으면 지금까지 쓴 코드를 보고 유도 질문을 만듭니다.
정답 코드는 직접 요청했을 때만 보여줍니다.

### 완료

`/leetlog:done`은 `prep` 이후 걸린 시간을 코드 주석에 남기고, 코드 피드백(정확성·성능, 가독성·네이밍)을 대화로 출력합니다.

### 문서

frontmatter, 작성한 코드가 담긴 빈 문서를 생성합니다.

```markdown
---
title: 54. Spiral Matrix
created: 2026-04-06T21:12:00+09:00
updated: 2026-08-08T14:51:00+09:00
difficulty: Medium
tags: [Array, Matrix, Simulation]
url: https://leetcode.com/problems/spiral-matrix/
---

<!-- Write your notes here -->

## 2026-08-08
```

같은 문제를 다시 풀면 새 날짜 섹션이 맨 위에 붙고 이전에 쓴 내용은 그대로 남습니다.

### 커밋

정해진 포맷으로 커밋합니다. push나 PR은 하지 않습니다.

```
solve: 54. Spiral Matrix
docs: 54. Spiral Matrix
```

## 저장 위치

기록은 모두 지금 작업 중인 저장소 안에 남습니다.

```
.leetlog.json                                                 설정 (기본 언어·풀이 디렉토리)
<solutions_dir>/{Easy|Medium|Hard}/{번호}_{slug}.{확장자}    풀이 코드
docs/{번호}_{slug}.md                                          풀이 문서
```

같은 문제를 같은 언어로 다시 풀면 기존 파일 위에 새 풀이가 쌓입니다.
다른 언어로 풀면 파일이 따로 생기고, 문서는 문제당 하나로 유지됩니다.
