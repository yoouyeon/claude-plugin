---
name: add-source
description: >
  This skill should be used when the user asks to "add an RSS source", "소스 추가",
  "RSS 등록", "피드 추가", "소스 삭제", "소스 목록 보여줘", or wants to manage the
  RSS feeds that articles-os collects from. Standalone re-entry point; also reused
  by the setup onboarding.
metadata:
  version: "0.1.0"
---

## 권한 근거

피드 검증(`fetch_feed.py`, 외부 fetch)을 메인 스레드에서 직접 호출한다 — 단일 URL을 그 자리에서 검증해 사용자에게 바로 보여줘야 하는 동기적 상호작용이라, 서브에이전트로 위임하면 대화 왕복만 늘고 이득이 없다.

# RSS 소스 추가/삭제

`config.yaml`의 `sources` 섹션 관리. 공통 규칙은 `${CLAUDE_PLUGIN_ROOT}/docs/conventions.md` 참조. dedup·읽기·쓰기는 `scripts/manage_config.py`가 전담한다 — 그 출력을 해석·표시만 한다.

`<DATA>` = `${user_config.data_path}`.

## 절차

1. **데이터 폴더 확인**: `<DATA>/config.yaml`이 없으면 "먼저 `/articles-os:setup`을 실행하세요" 안내 후 종료(자동 실행 금지).
2. **현재 목록 표시**: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" sources list <DATA>` 실행, `sources`를 `이름 · URL` 목록으로 보여준다.
3. **추가**: 사용자에게 RSS URL(들)을 받는다.
   - **검증 필수**: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fetch_feed.py" "<url>"` 실행. `ok: false`면 에러를 보여주고 저장하지 않는다. 사용자가 블로그 홈 URL만 줬으면 일반 관례(`/rss.xml`, `/feed`, `/atom.xml`, `/rss`)를 시도해 피드 URL을 찾아본다.
   - `name`은 검증 결과의 `feed_title`을 기본 제안, 사용자가 바꿀 수 있다.
   - `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" sources add <DATA> --name "<name>" --url "<url>"` 실행. `ok: false`(`error: "duplicate url"`)면 중복임을 알리고 중단한다.
4. **삭제**: 번호나 이름으로 지정받아 해당 URL을 확인한 뒤 `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" sources remove <DATA> --url "<url>"` 실행. `articles.json`의 수집된 아티클은 그대로 둔다 — 건드리지 않는다.
5. **마무리**: `add`/`remove`가 반환한 갱신된 `sources`로 목록을 보여주고, 추가 시엔 검증 fetch에서 나온 최신 글 제목 1–2개도 함께 보여줘 "제대로 연결됐다"는 확신을 준다.
