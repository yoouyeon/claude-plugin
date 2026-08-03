---
name: interview
description: >
  아티클을 읽고 나서 회상 인터뷰로 기억을 끌어내는 스킬.
  "인터뷰 하자", "이 아티클 읽었어", "생각 정리하고 싶어", "회상 인터뷰" 같은 요청이 오면 실행한다.
metadata:
  version: "0.1.0"
---

## 0. 데이터 경로 확인

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/paths.py" --require-initialized` 실행.
`ok: false`면 `error`를 보여주고 끝낸다. 성공하면 `data_root`를 1단계에서 쓴다.

## 1. 대상 확정과 준비

1. `data_root`의 `articles.json`에서 대상 아티클을 특정한다 (번호/URL/제목). 같은 아티클의 `qa_log`도 읽어둔다.
2. 이 세션에서 fetch한 적 없으면 WebFetch(실패 시 `curl -sL`)로 원문 본문을 가져온다. **`articles.json`에 저장하지 않는다.**
   둘 다 실패하거나 본문이 사실상 비어 있으면(자리표시자만 남는 등) 원문을 못 가져왔다고 알리고 그대로 진행할지 묻는다. `summary`는 잘려 있으므로 원문 대신 쓰지 않는다.
   원문 없이 진행하면 교정을 하지 않고 5단계의 요지 적재도 건너뛴다.
3. 진행 중인 인터뷰를 확인한다.

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interview_state.py" get --url "<아티클 url>"
   ```

   - `exists: true` : `turns`·`remaining`을 알리고 **2단계를 건너뛰어** 3단계로
   - `exists: false` : 2단계로
   - `ok: false` : `error`를 보여주고 중단

## 2. 자유 덤프

**질문으로 시작하지 않는다.** "이 아티클 읽고 든 생각·의문·좋았던 점·동의 안 되는 점, 뭐든 자유롭게 쏟아내 줘."로 열고 끊지 않는다.

받은 덤프를 그대로 적재한다:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interview_state.py" start \
  --url "<아티클 url>" --title "<아티클 제목>" --source "<출처>" <<'ARTICLES_OS_DUMP'
<덤프 원문>
ARTICLES_OS_DUMP
```

`ok: false`면 `error`를 보여주고 중단한다.

## 3. 회상 인터뷰

템플릿 채우기·플래시카드가 아니라 대화로 끌어낸다. 고정 질문 세트를 쓰지 않는다.
질문은 원문 + 덤프 + `qa_log`를 읽고 그 자리에서 만든다.

**네 축을 채운다.** 
각 축의 닫힘 기준은 하나: **그 대목을 사용자가 한 말만으로 쓸 수 있는가.** AI가 보충해야 채워지면 아직 열린 것이다.

- `concept` 핵심 개념: 아티클이 말하는 것을 자기 언어로 말했다
- `judgment` 판단·이견: 동의/반박과 그 근거를 말했다
- `apply` 적용: 자기 상황·코드·일에 어떻게 쓸지 말했다
- `unresolved` 미해결: 아직 모르는 것 / 다음에 볼 것을 짚었다

질문 규칙:

- **갭 채우기**: 덜 건드린 축을 메운다. 덤프가 의견에 쏠렸으면 개념을, 개념에 쏠렸으면 "그래서 어떻게 생각해?" 쪽으로.
- **`qa_log` 우선**: 사용자가 직접 물었던 지점을 먼저 되묻는다. 반복이 아니라 "아까 물어봤던 X, 이제 네 말로 설명해봐" 형태로.
- **톤**: 채점·퀴즈가 아니라 "네 말로 다시 설명해봐". 암기 시험 금지.
- **교정**: 잘못 기억·이해한 게 있으면 부드럽게 바로잡는다.

답변마다 아래를 실행한다. 닫힌 축이 없어도 실행한다. 턴은 그래도 센다.
**덤프에 이미 어떤 축을 닫을 발화가 들어 있으면 첫 턴에 함께 넣는다.** 이미 말한 것을 다시 묻지 않는다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interview_state.py" turn --url "<아티클 url>" <<'ARTICLES_OS_TURN'
{"closed": {"<축 키>": ["<그 축을 닫은 사용자 발화>"]},
 "corrections": [{"misunderstood": "<처음에 알던 것>", "actual": "<실제>"}]}
ARTICLES_OS_TURN
```

발화는 사용자가 실제로 한 말을 옮긴다. 요약하거나 다듬지 않는다. 교정이 없으면 `corrections`는 생략한다.
`axis ... needs at least one non-empty evidence utterance`가 나오면 그 축은 아직 닫힌 게 아니다.

반환값으로 갈라진다:

- `all_closed: true` : 4단계로
- `limit_reached: true` : "더 파고들래, 아니면 여기서 정리할까?"를 묻는다. 정리하면 **4단계를 건너뛰어** 5단계로. 계속하면 이어가되 **이 질문을 다시 하지 않는다.**
- 그 밖 : `remaining`의 축을 겨냥해 다음 질문을 만든다

사용자가 멈추자고 하면 그 자리에서 5단계로 간다.

## 4. 종료 직전 검수

`articles-os:interview-check`를 소환한다. 아티클 url과 `${CLAUDE_PLUGIN_ROOT}`의 실제 값을 넘긴다.

- **통과** : 5단계로
- **미달** : 지목된 축을 다시 연 뒤 3단계로. 검수 결과를 그대로 옮기지 말고 그 축을 묻는 질문으로 잇는다.

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interview_state.py" reopen --url "<아티클 url>" --axis "<축 키[,축 키]>"
  ```

`limit_reached: true`가 된 뒤에는 이 단계를 실행하지 않는다.

## 5. 요지와 마무리

원문을 근거로 "이 글은 무슨 주장을 하는가"를 2~3문장으로 써서 적재한다. 사용자 발화가 아니라 아티클 요약이다.
**300자를 넘으면 스크립트가 거부한다.** 아티클 요약문이 아니라 주장 한 줄로 좁힌다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interview_state.py" summary --url "<아티클 url>" <<'ARTICLES_OS_SUMMARY'
<요지 2~3문장>
ARTICLES_OS_SUMMARY
```

닫힌 축과 남은 축을 한 줄로 알리고, 메모로 남기려면 `/articles-os:note`를 실행하라고 안내한다. **메모를 여기서 쓰지 않는다.**
