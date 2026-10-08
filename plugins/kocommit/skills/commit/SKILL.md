---
name: commit
description: >
  변경사항을 논리 단위로 나눠 한국어 Conventional Commits 메시지로 커밋하는 스킬. "커밋해줘", "커밋 메시지 만들어줘", "지금까지 작업한 거 커밋" 같은 요청이 오면 실행한다.
allowed-tools: Read, Glob, Grep, Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git symbolic-ref:*), Bash(git switch:*), Bash(git add:*), Bash(git commit:*), Bash(python3:*)
metadata:
  version: "0.1.0"
---

# 커밋

변경사항을 읽고 커밋 메시지 규칙에 맞는 메시지를 만들어 커밋한다.

## 1. 레포 규칙 확인

레포에 커밋 규칙이 있는지 먼저 본다. 아래에서 커밋 메시지 규칙을 찾는다.

- `CLAUDE.md`, `.claude/CLAUDE.md`
- `CONTRIBUTING.md`, `.github/CONTRIBUTING.md`
- `.claude/skills/commit/SKILL.md`

규칙이 있으면 **그 규칙이 이 스킬의 3장보다 우선**한다. 레포 규칙이 다루지 않는 부분만 3장을 따른다.

## 2. 변경사항 파악

다음을 한 번에 실행한다.

```bash
git status --short
git diff HEAD
git log --oneline -10
git branch --show-current
git symbolic-ref --short refs/remotes/origin/HEAD
```

**diff를 반드시 확인한 뒤 메시지를 쓴다.**

현재 브랜치가 기본 브랜치(`origin/HEAD`, 확인되지 않으면 `main` 또는 `master`)면 커밋하지 않고 브랜치를 먼저 만들자고 제안한다. 사용자가 그대로 커밋하라고 하면 진행한다.

### 커밋 단위

판단 기준은 "이 커밋 하나를 되돌렸을 때 말이 되는가"다.

- 나누는 예: 타입이 섞인 변경(`feat` + `docs`), 리팩터링 + 기능 변경, 기능 추가 + 무관한 오타 수정, 설정 변경 + 그 설정으로 인한 전체 포맷팅
- 나누지 않는 예: 한 기능을 위해 함께 움직이는 구현·테스트·설정, 함수 추가와 그 함수를 쓰는 호출부 수정

커밋이 하나면 바로 커밋한다. 여러 개로 나눌 때만 각 커밋의 메시지와 포함할 파일을 먼저 보여주고 승인을 받는다.

## 3. 메시지 규칙

[Conventional Commits](https://www.conventionalcommits.org) 형식을 따른다.

```
<type>: <description>

[optional body]
```

### type

| type | 용도 |
|---|---|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서만 변경 |
| `style` | 포맷팅·공백·세미콜론 등 동작이 바뀌지 않는 변경 |
| `refactor` | 동작을 바꾸지 않는 코드 구조 변경 |
| `test` | 테스트 추가·수정 |
| `chore` | 의존성 업데이트, 도구 설정 등 유지보수 |
| `revert` | 이전 커밋 되돌리기 |

### description

- 한국어로 쓰고 **명사형으로 끝낸다.** `~다`, `~했다`, `~한다`, `~합니다`로 끝내지 않는다.
- 커밋에 담긴 변경만 설명한다. 이유는 쓰지 않는다.
- `<type>: <description>` 전체가 50자를 넘지 않는다.
- 마침표를 붙이지 않는다.

### body

- **기본값은 쓰지 않는 것이다.** diff를 봐도 알 수 없는 **이유**가 있을 때만 쓴다.
- title을 다시 풀어 쓰지 않는다. diff를 보면 알 수 있는 내용(파일명·함수명 나열, 변경 절차)을 쓰지 않는다.
- 지우고 남는 줄이 없으면 body를 쓰지 않는다.
- 항목이 2개 이상이면 전부 bullet으로, 1개면 bullet 없이 한 줄로 쓴다. 한 body 안에서 둘을 섞지 않는다.
- 한 항목은 길어도 한 줄로 쓴다.
- description처럼 한국어로 쓰고 명사형으로 끝낸다. 이유는 "~므로", "~도록"으로 이어 붙인다.

```
chore: Vite를 Next.js App Router 프로젝트로 교체

- 키가 없으면 Next가 `true`로 다시 채우므로 `allowJs: false` 명시
- `.next`가 없을 때 라우트 타입 누락으로 실패하지 않도록 typecheck 전에 `next typegen` 실행
```

### 금지어

title과 body 모두 `및`, `박아 넣는다`를 쓰지 않는다.

## 4. 검사

1장에서 레포 규칙을 따르기로 했으면 이 단계를 건너뛴다.

메시지마다 아래 스크립트로 검사한다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" <<'MSG'
<메시지>
MSG
```

- exit 0: 5장으로 간다.
- exit 1: 걸린 줄을 고치고 다시 검사한다. 종결어미 항목이 `~다`로 끝나는 명사(예: `바다`)를 가리키면 그대로 둔다.
- exit 2: 메시지가 비었으니 다시 쓴다.

## 5. 커밋

커밋마다 `git add <파일>`과 `git commit`을 짝지어 실행한다.

- `git add -A`와 `git commit -a`를 쓰지 않는다. 그 커밋에 들어갈 파일만 스테이징한다.
- 훅이 커밋을 거부하거나 파일을 고치면 되돌리지 말고 무슨 일이 있었는지 알린 뒤 어떻게 할지 묻는다.
- push와 PR 생성은 요청받았을 때만 한다.

## 6. 마무리

만든 커밋의 메시지와 각 커밋에 담긴 파일을 알린다.
