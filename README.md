# yoouyeon-plugins

Claude Code 플러그인 모음.

## 플러그인

| 플러그인 | 설명 |
|---|---|
| [articles-os](plugins/articles-os/README.md) | RSS 기반 기술 아티클 학습 파이프라인. 매일 수집·Slack/Discord 알림·원문 Q&A·회상 인터뷰 메모 |
| [leetlog](plugins/leetlog/README.md) | LeetCode 풀이 기록. 문제 준비·단계별 힌트·소요 시간 기록·풀이 문서·로컬 커밋 |
| [devdocs](plugins/devdocs/README.md) | 개발 산출물 문서 작성·검사. 스펙·리서치 메모·PR 본문·이슈 본문·README |
| [kocommit](plugins/kocommit/README.md) | 한국어 Conventional Commits 커밋. 커밋 단위 나누기·메시지 검사 |

## 설치

```
/plugin marketplace add yoouyeon/claude-plugin
/plugin install articles-os@yoouyeon-plugins
/plugin install leetlog@yoouyeon-plugins
/plugin install devdocs@yoouyeon-plugins
/plugin install kocommit@yoouyeon-plugins
```
