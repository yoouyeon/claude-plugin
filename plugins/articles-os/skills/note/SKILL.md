---
name: note
description: >
  끝낸 회상 인터뷰를 학습 메모(.md)로 남기는 스킬.
  "메모 남겨줘", "메모로 정리해줘", "노트로 저장해줘", "인터뷰한 거 정리해줘" 같은 요청이 오면 실행한다.
metadata:
  version: "0.2.0"
---

## 1. 대상 인터뷰 확정

아티클이 지정됐으면 그 url로, 아니면 진행 중인 인터뷰 목록에서 고르게 한다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interview_state.py" get --url "<아티클 url>"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interview_state.py" list
```

- `list`에 여러 건 : 제목·출처·`turns`·`remaining`을 번호 붙여 보여주고 고르게 한다
- `interviews`가 비어 있거나 `exists: false` : 아래 1-1로 간다
- `ok: false` : `error`를 보여주고 중단

`get` 결과의 `summary`, `axes`, `corrections`가 2단계의 재료다. **`dump`는 재료가 아니다.**

### 1-1. 해당하는 인터뷰가 없을 때

**REQUIRED SUB-SKILL:** Use articles-os:interview

articles-os:interview 스킬로 인터뷰를 먼저 끝낸다. 사용자가 아티클을 지정했으면 그 지정을 그대로 넘긴다. 지정이 없으면 대상 선택도 그쪽에 맡긴다.

인터뷰가 끝나면 다시 확인한다:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interview_state.py" get --url "<아티클 url>"
```

`exists: true`면 2단계로 간다. 아직 없으면 사용자가 인터뷰를 중단한 것이므로 메모를 만들지 않고 끝낸다.

## 2. 본문 조립

```
<요지 2~3문장>

<닫힌 축들을 헤딩 없이 문단으로 이어 쓴 본문>

## 아직 모르는 것

- …
```

- **요지**: `summary`를 그대로 쓴다. 비어 있으면(원문을 못 가져온 인터뷰) 이 문단을 통째로 뺀다.
- **본문**: `핵심 개념`·`판단·이견`·`적용` 축의 `evidence`만으로 쓴다. 읽기 좋은 순서로 배열하고 문단을 나눈다. H1을 넣지 않는다.
- **다듬기는 구어 정리까지.** 말버릇·망설임·중복을 거르고 문장을 끝맺는 수준. 사용자가 고른 단어·비유·강조점은 그대로 살린다. 새 주장·근거·예시를 보태지 않는다.
- **교정**: `corrections`가 있으면 그 개념을 다루는 대목에 "처음엔 X로 알았는데 실제로는 Y" 한 줄로 붙인다. 별도 섹션을 만들지 않는다.
- **아직 모르는 것**: `미해결` 축의 `evidence`를 항목으로 넣는다. `remaining`에 남은 축이 있으면 그 축도 "아직 정리 못 한 것"으로 한 줄씩 넣는다. 넣을 게 하나도 없으면 이 섹션을 뺀다.

## 3. 저장

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/save_note.py" "<아티클 url>" --title "<제목>" --source "<출처>" <<'ARTICLES_OS_NOTE'
<조립한 본문 markdown>
ARTICLES_OS_NOTE
```

제목·출처는 1단계 `get`이 준 값을 그대로 쓴다. 본문에 따옴표·백틱·`$`가 섞이므로 위 heredoc 형식을 그대로 쓴다.

`ok: false`면:

- `article not found for url: ...` : 1단계로 돌아가 url을 다시 확정하고 재시도
- `stdin body is empty` : 본문을 다시 조립해 재시도
- 그 밖 : `error`를 보여주고 중단. **아래 4단계를 실행하지 않는다.**

## 4. 정리와 마무리

목차를 갱신하고 인터뷰 파일을 지운다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_index.py"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interview_state.py" delete --url "<아티클 url>"
```

둘 중 하나가 실패해도 메모는 이미 저장돼 있다. 에러를 보여주되 저장 성공은 그대로 알린다.

`save_note.py`가 준 `full_path`를 알린다. `## 아직 모르는 것`을 넣었으면 한 줄 덧붙인다: 나중에 더 파고들 거면 그대로 두고, 필요 없으면 지우면 된다.
