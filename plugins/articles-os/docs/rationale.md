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

## storage-location

우리가 직접 만드는 홈 레벨 디렉토리(`~/.articles-os/` 같은 것)를 전부 없애고, Claude Code가 이미 관리하는 인프라(`userConfig`, `${CLAUDE_PLUGIN_DATA}`)에 얹기로 한 결정의 배경.

기존엔 설치 여러 벌을 지원한다는 전제로 홈 레지스트리(`registry.json`)·`install_id`·`resolve_install.py`의 cwd/단일/다중 판별 로직을 만들었다. 하지만 실사용 시나리오를 다시 짚어보니 "한 머신에 프로젝트별로 여러 벌 설치"는 실제 요구가 아니라 "혹시 몰라서" 넣어둔 가정이었다 — 보통 머신의 주인은 한 명이고, articles-os는 그 한 명의 개인 학습 파이프라인이다. 이 가정을 걷어내자 레지스트리·판별 로직 전체가 통째로 불필요해졌다.

그 자리를 대체한 것이 Claude Code 플러그인 매니페스트의 `userConfig` 필드다(`type: directory`) — 플러그인 활성화 시 Claude Code가 값을 물어보고 `~/.claude/settings.json`(이미 존재하는 파일)의 `pluginConfigs[<plugin-id>].options`에 저장하며, 스킬·에이전트 콘텐츠의 `${user_config.data_path}` 자리를 실제 경로로 치환해준다. 로컬 테스트 플러그인으로 직접 검증한 결과:

- `--plugin-dir`로 임시 로드했을 땐 치환이 되지 않았다 — 값이 실제로 `pluginConfigs`에 기록되지 않았기 때문으로 보인다.
- 마켓플레이스를 통해 정식 설치(`claude plugin install`)한 뒤에는 대화형 세션은 물론 **헤드리스 `-p` 호출에서도** `${user_config.data_path}`가 실제 경로로 정확히 치환됐다.
- `CLAUDE_PLUGIN_OPTION_<KEY>` 환경변수는 hook/MCP/LSP 서브프로세스에만 전달되고, 스킬 지침이 시키는 일반 Bash 호출에는 전달되지 않는다(실측 확인).
- `${CLAUDE_PLUGIN_DATA}`(플러그인 영구 데이터 디렉토리 경로)도 일반 Bash 호출의 `os.environ`으로 읽으면 **안전하지 않다** — 세션에 다른 플러그인의 hook(예: SessionStart/Stop hook)이 실행되면 그 값이 hook 프로세스 스코프를 넘어 일반 Bash 호출의 환경에도 남는다. 실제로 로컬 마켓플레이스 설치본으로 종단 테스트하던 중 이 문제를 직접 겪었다 — `save_secret.py`가 `os.environ.get("CLAUDE_PLUGIN_DATA")`로 읽은 값이 articles-os 자신의 디렉토리가 아니라 같은 세션에 활성화돼 있던 다른 플러그인(hook을 매 턴 실행하는 플러그인)의 디렉토리를 가리켰고, 그 결과 테스트 웹훅 값이 **그 플러그인의 실제 `secrets.json`을 덮어썼다**. 이 사고 이후 스크립트가 `${CLAUDE_PLUGIN_DATA}`를 환경변수로 다시 읽는 방식을 폐기하고, 호출하는 SKILL.md가 이 플레이스홀더를 텍스트로 치환한 값을 **명시적 CLI 인자**로 넘기도록 고쳤다 — `${user_config.*}` 치환과 동일한 안전한 경로(스킬 콘텐츠 안에서 Claude Code가 그 스킬 소속 플러그인 기준으로 정확히 스코프)를 타기 때문에 이 문제가 재발하지 않는다.

이 실측 결과가 시크릿 저장 위치 결정([#secrets](#secrets))의 근거이기도 하다.

## user-config

데이터 폴더 경로를 `userConfig(type: directory)`로 옮기면서 자연히 정리된 것들:

- **스케줄러 커맨드에 절대경로를 박아 넣던 관행 폐기.** 기존엔 "헤드리스 실행은 cwd를 상속받지 못한다"는 이유로 `claude -p '/articles-os:collect <절대경로>'`처럼 커맨드 자체에 경로를 심었다. `userConfig` 치환이 헤드리스에서도 동작함을 확인했으므로 `claude -p '/articles-os:collect'`(인자 없음)로 충분하다.
- **`setup` 스킬의 4단계 중 1단계(데이터 경로 지정)가 사라짐.** Claude Code가 플러그인 활성화 시점에 자동으로 프롬프트하므로, `setup`은 남은 3단계(소스·알림·스케줄)만 다룬다.
- **"활성 설치가 없는 상태" 감지 방식이 바뀜.** 예전엔 레지스트리가 비어 있는지(`resolve_install.py`의 `none`)로 판단했지만, `data_path`엔 항상 기본값(`./articles-os`)이 있어 이 신호로 못 쓴다. 대신 "그 경로에 `config.yaml`이 있는지"로 판단한다 — 애초에 온보딩 완료 여부는 항상 이 파일의 존재·내용으로 판별해왔으므로 실질적으로 달라지는 건 없다.

## secrets

웹훅 시크릿을 `${CLAUDE_PLUGIN_DATA}/secrets.json`(Claude Code가 관리하는 플러그인 영구 데이터 디렉토리)에 저장하기로 한 결정의 전체 배경.

**왜 `userConfig`로 못 넣나:** `userConfig`의 `sensitive: true` 필드는 스킬·에이전트 콘텐츠에 절대 치환되지 않는다(실측 확인 — 값을 설정해도 항상 "not available in skill content"만 반환됨). 우리 알림 발송(`notify.py`)은 hook이 아니라 **스킬 지침이 시키는 일반 Bash 호출**이라, `userConfig`가 시크릿을 전달할 수 있는 유일한 경로(hook 프로세스의 `CLAUDE_PLUGIN_OPTION_<KEY>` 환경변수)를 애초에 타지 못한다. 그래서 시크릿만은 별도 저장이 필요하다.

**위협 모델:** Slack Incoming Webhook URL은 "URL을 아는 사람이 그 채널에 글을 쓸 수 있는" bearer 시크릿이나 심각도는 낮다(한 채널 쓰기 한정, 유출 시 Slack에서 즉시 폐기·재발급 가능).

**검토한 옵션과 결정:**

- **우리 소유의 홈 디렉토리(예 `~/.articles-os/secrets.json`):** 동작은 하지만 "새 관리 포인트를 늘리고 싶지 않다"는 요구와 어긋난다 — 우리가 만들고 우리가 지워야 하는 디렉토리가 하나 더 생긴다.
- **OS 키체인(macOS `security` / Linux `libsecret`) 직접 호출:** 디렉토리 자체는 없앨 수 있지만, macOS/Linux 이원화 구현과 헤드리스 실행 시 키체인 잠금 프롬프트 리스크를 새로 짊어져야 한다. 남는 이득 대비 구현 비용이 안 맞는다.
- **`${CLAUDE_PLUGIN_DATA}/secrets.json` (채택, 단 전달 방식에 주의):** 새 디렉토리를 만들지 않는다 — Claude Code가 이미 관리하는 `~/.claude/plugins/data/<plugin-id>/` 트리 밑에 얹는다. 처음엔 스크립트가 이 경로를 `os.environ`으로 직접 읽도록 구현했다가, 종단 테스트에서 다른 플러그인의 hook이 남긴 값과 섞여 그 플러그인의 실제 시크릿을 덮어쓰는 사고를 겪었다([#storage-location](#storage-location)). 수정: 스크립트는 이 경로를 **인자로만** 받고, 호출하는 SKILL.md가 `${CLAUDE_PLUGIN_DATA}` 플레이스홀더를 그대로 커맨드에 적어 넘긴다 — 이 치환은 Claude Code가 스킬 소속 플러그인 기준으로 정확히 스코프하므로 안전하다. 캐치: 플러그인을 마지막 스코프에서 제거하면 이 디렉토리도 함께 삭제된다 — 다만 위협 모델상 웹훅은 낮은 심각도·즉시 재발급 가능이라 이 트레이드오프를 받아들였다(다른 사용자 데이터 — 소스·수집 이력·메모 — 는 이 디렉토리에 두지 않으므로 영향 없음).
- **`.gitignore` 대비 우위(참고, 기존 판단 유지):** gitignore는 git만 커버하고(동기화·zip 못 막음), 올바른 설정에 의존하며, 한 번 커밋되면 히스토리에 영구 잔존한다. 시크릿을 애초에 프로젝트 데이터 폴더에 두지 않는 구조적 방어가 gitignore보다 낫다는 판단은 그대로 유지된다.
