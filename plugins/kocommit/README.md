# kocommit

변경사항을 논리 단위로 나누고, 한국어 Conventional Commits 메시지로 커밋합니다. 레포에 커밋 규칙이 따로 있으면 그 규칙을 먼저 따릅니다.

## 시작하기

```
/plugin marketplace add yoouyeon/claude-plugin
/plugin install kocommit@yoouyeon-plugins
```

## 사용법

```
/kocommit:commit
```

"커밋해줘"라고만 해도 실행됩니다.

1. `CLAUDE.md`, `CONTRIBUTING.md`, 프로젝트 commit 스킬에서 커밋 규칙을 찾습니다. 있으면 그 규칙을 따릅니다.
2. diff를 읽고 커밋 단위를 정합니다. 기본 브랜치라면 브랜치를 먼저 만들자고 제안합니다.
3. 커밋이 하나면 바로 커밋합니다. 여러 개로 나눌 때만 커밋별 메시지와 파일을 보여 주고 승인을 받습니다.
4. 메시지를 스크립트로 검사한 뒤 커밋합니다. push와 PR 생성은 요청할 때만 합니다.

## 메시지 규칙

```
<type>: <description>

[optional body]
```

| 항목 | 규칙 |
|---|---|
| type | `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `revert` |
| title 길이 | type을 포함해 50자 이하 |
| 어미 | title과 body 모두 명사형. 마침표 없음 |
| description | 변경 내용만. 이유는 쓰지 않음 |
| body | diff로 알 수 없는 이유가 있을 때만. 2개 이상이면 전부 bullet, 1개면 bullet 없이 한 줄 |
| 금지어 | `및`, `박아 넣다` |

```
chore: Vite를 Next.js App Router 프로젝트로 교체

- 키가 없으면 Next가 `true`로 다시 채우므로 `allowJs: false` 명시
- `.next`가 없을 때 라우트 타입 누락으로 실패하지 않도록 typecheck 전에 `next typegen` 실행
```
