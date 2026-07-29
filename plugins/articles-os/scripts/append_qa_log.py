#!/usr/bin/env python3
"""아티클의 qa_log에 Q&A 한 건 추가 (stdlib only).

Usage:
    python3 append_qa_log.py <url>
    (stdin: {"question": "<사용자 질문 원문>", "answer_digest": "<답변 핵심 2-3문장>"})

동작:
    1. articles.json에서 url이 일치하는 아티클을 찾는다.
    2. {"asked_at": "<현재 ISO8601 UTC>", "question": ..., "answer_digest": ...}를 그 아티클의 qa_log에 append한다.
    3. articles.json을 저장한다.

stdout (JSON):
    성공: {"ok": true, "asked_at": "..."}
    실패: {"ok": false, "error": "..."}  (exit code 1)
"""
import json
import os
import sys
from datetime import datetime, timezone
from typing import NoReturn

import paths


def fail(msg) -> NoReturn:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def run(url):
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        fail("stdin must be a JSON object")

    question = payload.get("question")
    answer_digest = payload.get("answer_digest")
    if not isinstance(question, str) or not question.strip():
        fail("stdin JSON must have a non-empty string 'question'")
    if not isinstance(answer_digest, str) or not answer_digest.strip():
        fail("stdin JSON must have a non-empty string 'answer_digest'")

    articles_path = os.path.join(paths.data_root(), "articles.json")
    if not os.path.exists(articles_path):
        fail(f"articles.json not found: {articles_path}")
    with open(articles_path, encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, dict):
        fail("articles.json must be a JSON object")
    articles = doc.get("articles", [])
    if not isinstance(articles, list):
        fail("articles.json: 'articles' must be an array")

    target = next(
        (a for a in articles if isinstance(a, dict) and a.get("url") == url), None
    )
    if target is None:
        fail(f"article not found for url: {url}")

    qa_log = target.get("qa_log")
    if not isinstance(qa_log, list):
        qa_log = []
        target["qa_log"] = qa_log

    asked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    qa_log.append({
        "asked_at": asked_at,
        "question": question,
        "answer_digest": answer_digest,
    })

    with open(articles_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(json.dumps({"ok": True, "asked_at": asked_at}, ensure_ascii=False))


def main():
    if len(sys.argv) != 2:
        fail("usage: append_qa_log.py <url>")
    try:
        run(sys.argv[1])
    except (OSError, ValueError) as e:
        fail(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
