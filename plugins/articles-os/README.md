# articles-os

관심 있는 기술 블로그의 RSS를 등록해두면, 매일 새 글을 모아 Slack이나 Discord로 알림을 받을 수 있습니다.
새 글을 읽고 나면 원문 기반으로 질문하거나, AI와의 회상 인터뷰로 생각을 정리하고 그 결과를 학습 메모(.md)로 남길 수 있습니다.

## 실행 흐름

소스 등록 → 매일 자동 수집 → Slack·Discord로 신규 알림 → 목록에서 골라 읽기 → 궁금한 건 Q&A로 물어보기 → 회상 인터뷰 → 메모로 남기기.

인터뷰한 내용은 메모로 남길 수 있습니다. 진행 중인 인터뷰는 `/articles-os:browse` 목록에 표시됩니다.

## 필요 환경 조건

- Claude Code에서 동작합니다.
- macOS 전용입니다. Linux·Windows 환경에서는 아직 충분히 테스트되지 않았습니다.
- 아티클 자동 수집을 위해서는 플러그인을 **user scope**로 설치해야 합니다.
- Python 3가 필요합니다.
- 알림을 받기 위해서는 Slack Incoming Webhook URL 또는 Discord Webhook URL이 필요합니다.

## 시작하기

```
/plugin marketplace add yoouyeon/claude-plugin
/plugin install articles-os@yoouyeon-plugins
```

설치가 끝나면 `/articles-os:setup` 으로 온보딩을 시작합니다:

1. 학습 메모를 저장할 폴더 지정
2. 알림 연결 (Slack 또는 Discord)
3. 매일 수집할 시각 등록

온보딩을 마친 뒤 아래 `/articles-os:add-source` 스킬로 RSS 소스를 원하는 만큼 추가할 수 있습니다.
소스를 하나 이상 등록해야 수집이 시작됩니다.

## 스킬 모음

| 스킬 | 사용 시점 |
|---|---|
| `/articles-os:setup` | 처음 시작할 때 (최초 1회) |
| `/articles-os:add-source` | RSS 소스를 추가하거나 삭제할 때 |
| `/articles-os:notify-config` | 알림 방식을 바꾸거나 끄고 싶을 때 |
| `/articles-os:schedule` | 수집 시각을 바꾸거나 예약을 해제하고 싶을 때 |
| `/articles-os:collect` | 지금 바로 수집을 돌려보고 싶을 때 (평소에는 자동 실행) |
| `/articles-os:browse` | 모아둔 아티클을 다시 보고 싶을 때 |
| `/articles-os:qa` | 아티클 내용에 대해 질문하고 싶을 때 |
| `/articles-os:interview` | 읽은 내용을 회상 인터뷰로 정리하고 싶을 때 |
| `/articles-os:note` | 끝낸 인터뷰를 메모로 남기고 싶을 때 |

이 밖에:

- 여러 소스를 한 번에 빠르게 수집,
- "소스 상태 확인해줘"로 오래 조용한 소스 찾기,
- "내 메모에서 X 찾아줘"로 지난 메모 검색,
- Q&A 중 필요 시 외부 자료 조사.

## 데이터 저장 위치

- **학습 메모**는 온보딩에서 지정한 폴더에 저장됩니다.
- **소스 목록·알림 설정·수집 이력**은 플러그인이 따로 관리하는 고정 폴더(`~/.articles-os/`)에 저장됩니다.
- **진행 중인 인터뷰**도 같은 고정 폴더(`~/.articles-os/interviews/`)에 남고, 메모로 저장되면 지워집니다.

## 예약 해제

```
/articles-os:schedule remove
```
