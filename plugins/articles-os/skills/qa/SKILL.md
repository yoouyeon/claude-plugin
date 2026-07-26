---
name: qa
description: >
  This skill should be used when the user asks a question about a collected article,
  e.g. "N번에 질문 있어", "이 아티클에서 X가 무슨 뜻이야", "왜 저자는 ~라고 했지",
  or shares an article link with a question. Answers from the full original text
  and records the exchange in the article's qa_log.
metadata:
  version: "0.1.0"
---

## 권한 근거

본문 확보(세션 한정 지연 fetch)와 `qa_log` 저장(스크립트 호출)을 메인 스레드에서 직접 수행한다 — 질문에 바로 답해야 하는 동기적 흐름이라 서브에이전트로 위임하면 왕복만 늘고 이득이 없다(OS.md 스킬vs서브에이전트 분리표: "가볍고 사용자가 바로 봄, 격리 이득 없음"). 본문만으로 부족한 외부 조사만 조건부로 `qa-research`에 위임한다.

# 아티클 Q&A

원문 기반 답변 + `qa_log` 적재. 공통 규칙은 `${CLAUDE_PLUGIN_ROOT}/docs/conventions.md` 참조.

## 절차

1. **활성 설치 결정 + 아티클 특정**: `resolve_install.py` 규칙 → 번호/URL/제목으로 `articles.json`에서 찾기.
2. **본문 확보**: 이 세션에서 이미 fetch했으면 재사용, 아니면 WebFetch(또는 실패 시 `curl -sL`)로 원문을 가져와 본문 텍스트만 마크다운으로 추출한다(`articles.json`에 저장하지 않음 — 세션 한정). **`summary`로 답하지 않는다** — 요약은 손실 정보다. 항상 원문 전문 기준.
3. **답변**: 아티클이 실제로 말하는 내용에 근거해 답한다. 아티클의 주장과 일반적 사실을 구분해 말한다 ("저자는 ~라고 주장하는데, 일반적으로는 ~").
4. **외부 조사 (조건부)**: 아티클 본문만으로 부족하면 — 최신 수치, 아티클이 인용한 외부 개념, 반대 견해 등 — `qa-research` 에이전트(`articles-os:qa-research`)에 조사 질문을 위임하고, 반환된 결과를 출처와 함께 답변에 통합한다. 본문으로 충분하면 소환하지 않는다.
5. **qa_log 적재**: 답변 후 아래처럼 실행 — `asked_at` 생성, `qa_log` 병합, 저장을 스크립트가 전담한다:

```bash
echo '{"question": "<사용자 질문 원문>", "answer_digest": "<답변 핵심 2-3문장>"}' | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/append_qa_log.py" "<DATA>" "<url>"
```

`answer_digest`는 나중에 메모 인터뷰가 "이미 다룬 것"을 파악하는 용도 — 전체 답변을 저장하지 않는다. `ok: false`(예: url 불일치)면 사용자에게 알리지 않고 조용히 재시도하지 않는다 — 원인(아티클 특정 오류 등)을 다시 확인한다.

6. 같은 세션에서 추가 질문이 이어지면 2–5를 반복한다 (본문은 이미 이 세션에 있음 — 재fetch 불필요).

## 마무리

Q&A가 일단락되면 한 줄 제안: "이 아티클 메모 남길래? 지금 나눈 Q&A도 인터뷰에 반영돼."
