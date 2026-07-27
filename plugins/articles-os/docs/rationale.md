# 설계 근거 보충 (Rationale)

> OS.md 본문은 매 구현 세션마다 참조하는 문서라 "결정 + 한 줄 근거"만 남기고 짧게 유지한다. 여기는 각주 격 문서다 — 위협 모델·대안 비교·검토했지만 버린 옵션처럼, 결정을 재검토하지 않으려면 언젠가 필요할 배경을 전부 남긴다. 구현 시 매번 읽을 필요는 없고, 왜 이 선택인지 의문이 들 때만 연다.

## cowork

이 플러그인은 Claude Code 전용으로 설계하고 Cowork는 지원하지 않는다.

(1) 샌드박스 네트워크 egress가 Anthropic 관리 allowlist로 고정되어 있어 사용자가 등록한 임의 RSS 도메인·Slack 웹훅 도메인이 차단될 수 있고 커스텀 allowlist 설정도 무시된다는 보고가 있으며, 
(2) 플러그인 번들 hooks(`hooks/hooks.json`)가 발화되지 않는다는 보고가 있어, 이 플러그인의 핵심 파이프라인(수집·알림·index.md 자동 갱신)이 안정적으로 동작한다고 보장할 수 없다. 

Claude Code는 사용자 로컬 머신에서 직접 실행되므로 이런 제약이 없다.

## scheduling

스케줄링은 OS 네이티브 스케줄러(macOS: launchd 우선/cron, Linux: cron)로 확정하고, Claude 자체 스케줄링 기능은 전부 배제한다.

Claude Code가 제공하는 세 가지 옵션(Cloud Routines·Desktop scheduled task·`/loop`)은 각각 

- 로컬 파일 접근 불가(Routines), 
- **Desktop 앱이 실행 중이어야 함**(Desktop scheduled task — "앱이 열려 있어야만 fires"라 순수 터미널 요건과 정면 충돌), 
- 세션 종속·7일 만료(`/loop`)

라 전부 부적합. (근거: https://code.claude.com/docs/en/scheduled-tasks, https://code.claude.com/docs/en/desktop-scheduled-tasks)

Windows Task Scheduler는 1차 범위에서 제외한다 — 시크릿 파일 권한 모델이 POSIX `chmod 600`과 달라 동일한 방식으로 이식할 수 없다.

## secrets

웹훅 시크릿을 프로젝트 데이터 폴더가 아니라 홈(`~/.articles-os/secrets.json`)에 분리해 저장하는 결정의 전체 배경.

**위협 모델:** Slack Incoming Webhook URL은 "URL을 아는 사람이 그 채널에 글을 쓸 수 있는" bearer 시크릿이나 심각도는 낮다(한 채널 쓰기 한정, 유출 시 Slack에서 즉시 폐기·재발급 가능). 따라서 현실적 위협은 정교한 공격자가 아니라 **실수 유출**이고, 우리 설계에선 경로가 뚜렷하다 — 데이터 폴더 기본값이 `./articles-os`(프로젝트 안)라 사용자가 프로젝트를 git 커밋하거나 Dropbox/iCloud로 동기화하면 시크릿이 딸려 나간다.

**결정:** 시크릿을 프로젝트 밖 홈으로 분리한다. 이는 "빼먹지 말라고 표시"하는 방식이 아니라 **시크릿을 새어나갈 위치에 아예 두지 않는 구조적 방어**다.

- **`.gitignore` 대비 우위:** gitignore는 git만 커버하고(동기화·zip 못 막음), 올바른 설정에 의존하며, 한 번 커밋되면 히스토리에 영구 잔존, 남의 프로젝트 gitignore를 건드려야 해 침투적이다. 홈 분리는 이 모든 실수 경로와 무관하다. (원하면 데이터 폴더 기계 상태 파일 제외용으로 gitignore를 *보조*로 얹을 순 있으나, 시크릿 1차 방어선은 홈 분리다.)
- **키체인/OS 시크릿 매니저 대비:** 이식성(macOS `security` vs Linux libsecret, 헤드리스엔 시크릿 서비스 부재)과 헤드리스 접근(잠긴 키체인 프롬프트) 리스크가 있어 낮은 심각도 시크릿엔 과하다. 파일 분리 + `600`이 적정선.
- **헤드리스 수집:** 매일 도는 작업은 홈 파일을 그냥 읽으면 되므로 접근 문제 없음.
