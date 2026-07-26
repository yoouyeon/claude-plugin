#!/usr/bin/env python3
"""아티클의 qa_log에 Q&A 한 건 추가 (stdlib only).

Usage:
    python3 append_qa_log.py <data-path> <url>
    (stdin: {"question": "<사용자 질문 원문>", "answer_digest": "<답변 핵심 2-3문장>"})

question/answer_digest는 따옴표·줄바꿈이 섞일 수 있어 인자가 아니라 stdin JSON으로 받는다.

동작:
    1. <data-path>/data/articles.json에서 url이 일치하는 아티클을 찾는다.
    2. {"asked_at": "<현재 ISO8601 UTC>", "question": ..., "answer_digest": ...}를
       그 아티클의 qa_log에 append한다.
    3. articles.json을 저장한다.

stdout (JSON):
    성공: {"ok": true, "asked_at": "..."}
    실패: {"ok": false, "error": "..."}  (exit code 1)
"""
import json
import os
import sys
from datetime import datetime, timezone


def fail(msg):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def main():
    if len(sys.argv) != 3:
        fail("usage: append_qa_log.py <data-path> <url>")
    data_path = os.path.expanduser(sys.argv[1])
    url = sys.argv[2]

    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        fail(f"invalid stdin JSON: {e}")

    question = payload.get("question")
    answer_digest = payload.get("answer_digest")
    if not question or not answer_digest:
        fail("stdin JSON must have non-empty 'question' and 'answer_digest'")

    articles_path = os.path.join(data_path, "data", "articles.json")
    if not os.path.exists(articles_path):
        fail(f"articles.json not found: {articles_path}")
    with open(articles_path, encoding="utf-8") as f:
        doc = json.load(f)

    articles = doc.get("articles", [])
    target = next((a for a in articles if a.get("url") == url), None)
    if target is None:
        fail(f"article not found for url: {url}")

    asked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    target.setdefault("qa_log", []).append({
        "asked_at": asked_at,
        "question": question,
        "answer_digest": answer_digest,
    })

    with open(articles_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(json.dumps({"ok": True, "asked_at": asked_at}, ensure_ascii=False))


if __name__ == "__main__":
    main()
