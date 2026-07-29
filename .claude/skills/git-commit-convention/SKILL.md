---
name: git-commit-convention
description: 이 저장소에서 git 커밋 메시지를 작성할 때 적용하는 개인 컨벤션. Conventional Commits 형식, 한국어 작성, title 60자 제한, 필요할 때만 body 작성 등의 규칙을 따른다. "커밋해줘", "commit this", "git commit" 등의 요청에서 사용.
---

# Git 커밋 컨벤션

git commit 메시지를 작성할 때 아래 규칙을 적용한다.

## 규칙

- Conventional Commits 형식 사용 (`feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `test:` 등)
- 커밋 메시지는 title, body 모두 한국어로 작성
- title은 60자 이내로 작업 내용을 간단히 요약
- body는 부연 설명이 필요할 때만 추가한다. 코드를 보면 명확히 알 수 있는 내용(무엇을 추가/삭제했는지 등)은 생략
- body에 여러 항목이 있으면 bullet list 형식 사용
- '및' 이라는 단어를 사용하지 않는다.
- '박아 넣는다' 라는 단어를 사용하지 않는다.
