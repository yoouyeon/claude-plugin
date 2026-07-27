#!/usr/bin/env python3
"""메모 .md 저장 + articles.json note_path 갱신·qa_log 비우기 (stdlib only).

Usage:
    python3 save_note.py <data-path> <url> --title "<제목>" --source "<출처>"
    (stdin: frontmatter 아래 본문 markdown 전체 — 덤프/회상 인터뷰/정리 섹션,
     이미 완성된 텍스트를 그대로 넘긴다. 슬러그·파일명·frontmatter·JSON 갱신은
     이 스크립트가 전담한다.)

동작:
    1. 제목을 슬러그로 변환 (한글 유지, 공백→`-`, 특수문자 제거 — docs/conventions.md
       "메모 .md 형식" 참고).
    2. 오늘(로컬) 날짜로 파일명 `notes/YYYY-MM-DD-<슬러그>.md`를 조립한다. 같은 이름이
       이미 있으면 `-2`, `-3`...을 붙여 기존 메모를 덮어쓰지 않는다.
    3. frontmatter(title/url/source/date) + stdin 본문으로 파일을 쓴다.
    4. <data-path>/articles.json에서 <url>과 일치하는 아티클을 찾아 note_path를
       상대경로(`notes/<파일명>`)로 갱신하고 qa_log를 빈 배열로 비운다.

stdout (JSON):
    성공: {"ok": true, "note_path": "notes/..."}
    실패: {"ok": false, "error": "..."}  (exit code 1)
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime


def fail(msg):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def slugify(title):
    """한글 유지, 공백 -> '-', 특수문자 제거 (docs/conventions.md 151행)."""
    s = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    return s.strip("-") or "untitled"


def unique_filename(notes_dir, base_name):
    """base_name.md가 이미 있으면 -2, -3...을 붙여 기존 메모를 보존한다."""
    candidate = f"{base_name}.md"
    if not os.path.exists(os.path.join(notes_dir, candidate)):
        return candidate
    n = 2
    while True:
        candidate = f"{base_name}-{n}.md"
        if not os.path.exists(os.path.join(notes_dir, candidate)):
            return candidate
        n += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_path")
    parser.add_argument("url")
    parser.add_argument("--title", required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()

    body = sys.stdin.read()
    if not body.strip():
        fail("stdin body is empty")

    data_path = os.path.expanduser(args.data_path)
    notes_dir = os.path.join(data_path, "notes")
    os.makedirs(notes_dir, exist_ok=True)

    articles_path = os.path.join(data_path, "articles.json")
    if not os.path.exists(articles_path):
        fail(f"articles.json not found: {articles_path}")
    with open(articles_path, encoding="utf-8") as f:
        doc = json.load(f)

    articles = doc.get("articles", [])
    target = next((a for a in articles if a.get("url") == args.url), None)
    if target is None:
        fail(f"article not found for url: {args.url}")

    date_str = datetime.now().astimezone().date().isoformat()
    slug = slugify(args.title)
    base_name = f"{date_str}-{slug}"
    filename = unique_filename(notes_dir, base_name)

    frontmatter = (
        "---\n"
        f"title: {args.title}\n"
        f"url: {args.url}\n"
        f"source: {args.source}\n"
        f"date: {date_str}\n"
        "---\n\n"
    )

    note_path = os.path.join(notes_dir, filename)
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(frontmatter)
        f.write(body if body.endswith("\n") else body + "\n")

    rel_note_path = f"notes/{filename}"
    target["note_path"] = rel_note_path
    target["qa_log"] = []

    with open(articles_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(json.dumps({"ok": True, "note_path": rel_note_path}, ensure_ascii=False))


if __name__ == "__main__":
    main()
