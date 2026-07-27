# articles-os

RSS 기반 기술 아티클 학습 파이프라인 플러그인. 매일 아티클을 수집해 Slack으로 알리고, 원문 기반 Q&A → 회상 인터뷰 메모로 이어지는 학습 루프를 제공한다.

**Claude Code 전용** — 순수 터미널(헤드리스 서버 포함)에서 동작하며, Desktop 앱·Cowork를 요구하지 않는다. 설계 배경과 결정 근거는 [OS.md](OS.md) 참조.

## 흐름

소스 등록 → 매일 자동 수집(OS 스케줄러) → 신규 알림(Slack) → 브라우징·읽기 → Q&A → 회상 인터뷰 메모(.md).

## 시작하기

플러그인 설치 후:

```
/articles-os:setup
```

플러그인 활성화 시 Claude Code가 데이터 폴더 경로를 먼저 물어본다(기본 제안: `./articles-os`). 이어서 `setup` 온보딩이 3단계를 안내한다: RSS 소스 추가 → 알림 연결(Slack Incoming Webhook) → 일일 수집 스케줄 등록(macOS launchd / Linux cron). 기본 소스는 없다 — 소스를 추가해야 동작한다.

## 스킬

| 스킬 | 역할 |
|---|---|
| `/articles-os:setup` | 온보딩 (최초 1회, 3단계) |
| `/articles-os:add-source` | RSS 소스 추가/삭제 |
| `/articles-os:notify-config` | 알림 백엔드 변경 (slack / none) |
| `/articles-os:collect` | 수집 파이프라인 (스케줄러가 매일 호출, 수동 실행도 가능) |
| `/articles-os:browse` | 수집된 아티클 목록 (이번 수집분 / 최근 N일 / 전체) |
| `/articles-os:qa` | 아티클 원문 기반 Q&A (qa_log 기록) |
| `/articles-os:note` | 자유 덤프 → 회상 인터뷰 → 학습 메모 .md |

에이전트(자동 위임): 소스별 병렬 fetch, 소스 헬스체크("소스 상태 확인해줘"), 메모 검색("내 메모에서 X 찾아줘"), Q&A 외부 조사.

## 데이터 저장 위치

플러그인 디렉토리는 읽기 전용이다. 사용자 데이터는 전부 밖에 저장되고, 새로 만드는 홈 디렉토리는 없다 — Claude Code가 이미 관리하는 인프라 위에 얹는다:

- **데이터 폴더** (플러그인 활성화 시 지정, 기본 `./articles-os`): 소스·알림 설정(`config.yaml`), 수집 이력, 학습 메모(.md)
- **`~/.claude/settings.json`**: 데이터 폴더 경로 (Claude Code의 플러그인 설정 저장소)
- **`${CLAUDE_PLUGIN_DATA}`**: 웹훅 시크릿(`secrets.json`, chmod 600) — Claude Code가 관리하는 플러그인 영구 데이터 디렉토리

메모는 이식성 있는 순수 마크다운이라 Obsidian 등 어느 에디터에서도 열린다. 시크릿은 데이터 폴더에 두지 않으므로 프로젝트를 git 커밋해도 새지 않는다.

## 요구 사항

- Claude Code (터미널), macOS 또는 Linux (Windows는 1차 범위 외)
- Python 3 (표준 라이브러리만 사용 — 추가 설치 없음)
- 알림을 쓰려면 Slack Incoming Webhook URL (온보딩 때 입력, `backend: none`으로 끌 수도 있음)

## 스케줄 해제

- macOS: `launchctl unload ~/Library/LaunchAgents/com.articles-os.plist && rm` 해당 plist
- Linux: `crontab -e`에서 `# articles-os` 주석이 붙은 줄 제거
