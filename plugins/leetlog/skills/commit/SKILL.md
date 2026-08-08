---
name: commit
description: >
  leetlog가 만든 LeetCode 풀이 파일(`solutions/`)과 풀이 문서(`docs/`)를 로컬 커밋하는 스킬.
  그 외의 파일을 커밋할 때에는 이 스킬을 사용하지 않는다.
argument-hint: [문제 번호 또는 파일 경로]
arguments: [target]
allowed-tools: Read, Glob, Bash(git rev-parse:*), Bash(git status:*), Bash(git add:*)
metadata:
  version: "0.1.0"
---

- `ROOT`: !`git rev-parse --show-toplevel 2>/dev/null || pwd`
- `저장소 여부`: !`git rev-parse --is-inside-work-tree 2>/dev/null || echo false`

## 1. 저장소 확인

`저장소 여부`가 `true`가 아니면 git 저장소가 아니라 커밋을 건너뛴다고 알리고 종료한다. `git init`을 하지 않는다.

## 2. 대상 특정

`target`이 파일 경로면 그 파일 하나가 대상이다.

`target`이 문제 번호면 아래 둘을 Glob으로 찾아 나온 것을 전부 후보로 삼는다.

```
ROOT/solutions/*/<번호>_*.*
ROOT/docs/<번호>_*.md
```

`target`이 없으면 대화 맥락에서 방금 다룬 문제 번호를 쓴다. 맥락에 없으면 문제 번호를 묻고 중단한다.

후보가 하나도 없으면 그 사실을 알리고 종료한다.

## 3. 변경 확인

```bash
git status --porcelain -- <후보 경로들>
```

출력에 나온 경로만 대상으로 남긴다. 남은 것이 없으면 커밋할 변경이 없다고 알리고 종료한다.

`.leetlog.json`은 후보에 넣지 않는다.

## 4. 메시지

대상 파일마다 접두사를 **경로에서** 판정한다.

- `solutions/` 아래: `solve:`
- `docs/` 아래: `docs:`

문제 번호와 제목은 파일 안에서 읽는다.

- `solutions/` 파일: 헤더 블록 주석의 `문제 : <번호> - <제목>`
- `docs/` 파일: frontmatter의 `title: <번호>. <제목>`

읽지 못하면 **커밋하지 않고 멈춘 뒤** 제목을 묻는다. 답을 받고 나서 5단계로 간다.

```
solve: 54. Spiral Matrix
docs: 54. Spiral Matrix
```

- 번호 뒤에 마침표와 공백을 하나씩 둔다.
- 제목 한 줄로 끝낸다. 본문을 쓰지 않는다.
- 이모지를 쓰지 않는다.
- 플랫폼 이름을 넣지 않는다.
- 재풀이여도 형식이 같다. 회차를 표시하지 않는다.

## 5. 커밋

대상 파일 하나마다 커밋 하나를 만든다. 둘 다 남았으면 `solve:`를 먼저 커밋한다.

```bash
git add "<경로>"
git commit -m "<메시지>" -- "<경로>"
```

- `git add`를 먼저 실행한다. 순서를 바꾸면 untracked 파일에서 `pathspec did not match` 에러가 난다.
- `git add -A`와 `git commit -a`를 쓰지 않는다. 다른 파일을 스테이징하거나 커밋하지 않는다.
- `git push`와 PR 생성을 하지 않는다.

## 6. 마무리

만든 커밋의 메시지와 각 커밋에 담긴 파일 경로를 알린다.
