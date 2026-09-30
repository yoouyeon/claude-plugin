#!/usr/bin/env python3
"""LeetCode GraphQL에서 문제 메타를 받아 JSON으로 출력한다 (stdlib only).

Usage:
    python3 fetch_question.py <slug> [--lang <langSlug> | --no-snippets]

옵션:
    --lang <langSlug>   codeSnippets를 그 언어 하나로 줄인다.
                        일치하는 언어가 없으면 codeSnippets를 빈 배열로 두고
                        availableLangs에 응답에 있는 langSlug 목록을 담는다.
    --no-snippets       codeSnippets를 출력에서 뺀다 (힌트만 필요할 때).

stdout:
    exit 0 — 응답을 받음. `{"question": {...}}` 또는 `{"question": null}`(없는 slug)
    exit 1 — 응답을 받지 못함 (네트워크 오류, HTTP 오류, JSON이 아닌 응답)
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

URL = "https://leetcode.com/graphql/"
QUERY = """
query question($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId
    title
    difficulty
    topicTags { name }
    codeSnippets { langSlug code }
    hints
  }
}
"""


def fetch(slug: str) -> dict:
    body = json.dumps({"query": QUERY, "variables": {"titleSlug": slug}}).encode("utf-8")
    request = urllib.request.Request(
        URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Referer": f"https://leetcode.com/problems/{slug}/",
            "User-Agent": "Mozilla/5.0 (leetlog)",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--lang", help="남길 codeSnippets의 langSlug")
    group.add_argument("--no-snippets", action="store_true", help="codeSnippets를 출력에서 뺀다")
    args = parser.parse_args()

    try:
        payload = fetch(args.slug)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as error:
        print(f"LeetCode 조회 실패: {error}", file=sys.stderr)
        return 1

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict) or "question" not in data:
        print(f"LeetCode 조회 실패: 예상하지 못한 응답 {json.dumps(payload, ensure_ascii=False)[:200]}", file=sys.stderr)
        return 1

    question = data["question"]
    if question and args.no_snippets:
        question.pop("codeSnippets", None)
    elif question and args.lang:
        snippets = question.get("codeSnippets") or []
        matched = [s for s in snippets if s.get("langSlug") == args.lang]
        question["codeSnippets"] = matched
        if not matched:
            question["availableLangs"] = [s.get("langSlug") for s in snippets]

    print(json.dumps({"question": question}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
