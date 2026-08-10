---
name: commit
description: git 커밋을 만들거나 커밋 메시지를 작성할 때 사용한다. 변경사항을 논리 단위로 나눠 커밋 계획을 제안하고, 개인 컨벤션(Conventional Commits, 한국어, title 60자)에 맞춰 메시지를 쓴다. "커밋해줘", "commit this", "git commit", "/commit" 등에서 트리거.
---

# 커밋

## 절차

1. `git status`, `git diff HEAD`, `git log -5`, `git branch --show-current`를 병렬로 실행한다
2. 현재 브랜치가 `main`이면 커밋하지 말고 브랜치를 먼저 만들자고 제안한다
3. 변경을 논리 단위로 나눈 계획을 제안하고 승인을 받는다
4. 커밋마다 `git add <파일>` → `git commit`을 짝지어 실행한다
5. push는 요청받았을 때만 한다

커밋 단위는 타입(`feat`/`fix`/`docs`)이 섞이거나 리팩터링과 기능 변경이 섞이면 나누고, 한 기능을 위해 함께 움직이는 파일(구현 + 테스트 + 설정)은 나누지 않는다. 

계획은 어떤 파일이 어느 커밋에 들어가는지 보이게 쓴다.

훅이 커밋을 거부하거나 파일을 고치면 되돌리지 말고 알린 뒤 묻는다.

## 메시지

- Conventional Commits 형식 (`feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `test:` 등)
- title, body 모두 한국어, title은 60자 이내
- body는 필요할 때만 쓴다. 코드를 보고 알 수 있는 내용을 굳이 body에 추가로 적지 않는다
- body에는 무엇을 했는지가 아니라 **왜 그렇게 했는지**를 쓴다
- body에 항목이 여럿이면 bullet list, 한 항목은 길어도 한 줄로 쓴다
- '및', '박아 넣는다'를 쓰지 않는다
