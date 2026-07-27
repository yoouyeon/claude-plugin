---
name: browse
description: >
  This skill should be used when the user asks to "show collected articles", "아티클 목록",
  "뭐 새로 왔어", "최근 수집된 글 보여줘", "이번 주 아티클", or wants to re-view articles
  that were collected — the permanent pull surface for ephemeral notifications.
metadata:
  version: "0.1.0"
---

# 아티클 브라우징 (pull 표면)

새로 만드는 것 없이 `articles.json`을 읽어 렌더만 한다. 공통 규칙은 `${CLAUDE_PLUGIN_ROOT}/docs/conventions.md` 참조. 시간 필터·정렬·자동 확장 판정은 `scripts/filter_articles.py`가 전담한다 — 그 출력을 해석·렌더만 한다.

`<DATA>` = `${user_config.data_path}`.

## 절차

1. **데이터 폴더 확인**: `<DATA>/config.yaml`이 없으면 setup 유도, `sources`가 비었으면 add-source 유도.
2. **필터 결정 → 스크립트 호출**: 사용자가 명시한 범위를 아래 매핑으로 옮겨 실행한다.
   - "이번 수집분" → `--mode latest_batch`
   - "최근 N일" → `--mode recent_days --days N`
   - "전체" → `--mode all`
   - 명시 없으면 → `--mode recent_days` (기본 `--days 7`)

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/filter_articles.py" <DATA> --mode <모드> [--days N]
   ```

   응답의 `widened: true`는 요청한 범위에 0건이라 스크립트가 전체에서 최신 10건으로 자동 확장했다는 뜻 — 렌더 시 "결과가 없어 전체에서 최신 10건을 보여줍니다"로 알린다.
3. **렌더** — 스크립트가 반환한 `articles`(이미 최신순 정렬됨)를 순수 마크다운 텍스트 목록으로, 번호 부여:

```
### 최근 7일 · 3건

1. **제목** · 출처 · 2026-07-14
   summary 한 줄
   https://...
```

4. **후속 행동 안내**: 목록 끝에 한 줄 — "본문은 N번에 질문(Q&A), N번 메모 남기기(회상 인터뷰)". 사용자가 번호로 지시하면 해당 아티클의 `url`을 들고 qa / note 스킬 플로우로 넘어간다.

## 금지

- `read_at` 같은 읽음 상태를 만들거나 관리하지 않는다.
- summary를 새로 생성하지 않는다 — 저장된 값 그대로.
