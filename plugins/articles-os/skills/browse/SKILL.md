---
name: browse
description: >
  수집된 아티클 목록을 보여줄 때 쓰는 스킬.
  "아티클 목록", "뭐 새로 왔어", "최근 수집된 글 보여줘", "이번 주 아티클", "수집된 거 다시 보여줘" 같은 요청이 오면 이 스킬을 실행한다.
metadata:
  version: "0.1.0"
---

## 1. 필터 결정

사용자가 명시한 범위를 아래 매핑으로 옮긴다:

- "이번 수집분" → `--mode latest_batch`
- "최근 N일" → `--mode recent_days --days N` (N은 1 이상. 1 미만이면 되묻는다)
- "전체" → `--mode all`
- 명시 없으면 → `--mode recent_days` (기본 `--days 7`)

## 2. 목록 조회

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/filter_articles.py" --mode <모드> [--days N]
```

실행 결과가 :

- `ok: false`면 목록을 읽지 못한 것이다. `error`를 그대로 보여주고 **중단**한다 — 수집된 글이 없는 것과 구분한다.
- `count`가 0이면 아래를 실행해 소스 등록 여부를 확인하고, `sources`가 비어 있으면 `/articles-os:add-source`를 안내한다. 소스가 있으면 아직 수집된 글이 없다고만 알린다.

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage_config.py" sources list
  ```

- 그 밖의 경우 다음 3단계로 이어 진행한다.

`widened: true`는 요청한 범위에 0건이라 스크립트가 전체에서 최신 10건으로 자동 확장했다는 뜻이다 — 렌더 시 "결과가 없어 전체에서 최신 10건을 보여줍니다"로 함께 알린다.

## 3. 렌더

스크립트가 반환한 `articles`(이미 최신순 정렬됨)를 순수 마크다운 텍스트 목록으로, 번호를 부여해 보여준다. 
`summary`는 저장된 값 그대로 싣는다 — 다시 쓰거나 요약하지 않는다. 
헤딩에는 사용자가 요청한 범위와 `count`를 쓴다:

```
### 최근 7일 · 3건

1. **제목** · 출처 · 2026-07-14
   summary 한 줄
   https://...
```

## 4. 후속 행동 안내

목록 끝에 한 줄 안내한다 — 번호를 지정하면 그 아티클에 질문(Q&A)하거나 메모(회상 인터뷰)를 남길 수 있다고 알린다.
사용자가 번호로 지시하면 해당 아티클의 `url`을 들고 qa / note 스킬 플로우로 넘어간다.
