#!/usr/bin/env python3
"""메모 .md 저장 + articles.json note_path 갱신·qa_log 비우기 (stdlib only).

Usage:
    python3 save_note.py <url> --title "<제목>" --source "<출처>"
    stdin: frontmatter 아래 본문 markdown 전체 — 덤프/회상 인터뷰/정리 섹션, 이미 완성된 텍스트를 그대로 넘긴다.
    슬러그·파일명·frontmatter·JSON 갱신은 이 스크립트가 전담한다.

경로는 인자로 받지 않는다 — 노트 폴더는 config.yaml의 `notes_path`에서, articles.json은 고정 경로(`paths.data_root()`)에서 찾는다.

동작:
    1. 제목을 슬러그로 변환 (한글 유지, 공백→`-`, 특수문자 제거, SLUG_MAX_BYTES로 자름).
    2. 오늘(로컬) 날짜로 파일명 `YYYY-MM-DD-<슬러그>.md`를 조립해 노트 폴더에 쓴다.
       같은 이름이 이미 있으면 `-2`, `-3`...을 붙여 기존 메모를 덮어쓰지 않는다.
    3. frontmatter(title/url/source/date) + stdin 본문으로 파일을 쓴다.
       title·source는 따옴표로 감싸 표준 YAML 파서에서도 안전하게 읽히도록 한다.
    4. articles.json에서 <url>과 일치하는 아티클을 찾아 note_path를 노트 폴더 기준 상대경로(파일명)로 갱신하고 qa_log를 빈 배열로 비운다.
       노트 폴더를 통째로 옮기거나 복사해도 이 값이 유효하도록 파일명만 저장한다.

stdout (JSON):
    성공: {"ok": true, "note_path": "<파일명>.md", "full_path": "<절대경로>"}
    실패: {"ok": false, "error": "..."}  (exit code 1)
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import NoReturn

import paths

# 슬러그 상한(바이트). 긴 제목이 그대로 파일명이 되면 셸·파인더에서 다루기 나빠진다.
# 한글은 UTF-8에서 글자당 3바이트라 40자쯤에서 걸린다. 원제목은 frontmatter에 온전히 남는다.
SLUG_MAX_BYTES = 120


def fail(msg) -> NoReturn:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def slugify(title):
    """한글 유지, 공백 -> '-', 특수문자 제거, SLUG_MAX_BYTES로 자름."""
    s = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")

    encoded = s.encode("utf-8")
    if len(encoded) > SLUG_MAX_BYTES:
        # errors="ignore"가 잘린 멀티바이트 문자 조각을 떨어뜨린다.
        s = encoded[:SLUG_MAX_BYTES].decode("utf-8", "ignore").rstrip("-")
    return s or "untitled"


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


def run(args, body):
    notes_dir = paths.notes_root()
    if not notes_dir:
        fail("notes_path not configured (run /articles-os:setup)")
    os.makedirs(notes_dir, exist_ok=True)

    articles_path = os.path.join(paths.data_root(), "articles.json")
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

    # 자유 텍스트(title/source)는 따옴표로 감싼다 — 콜론·하이픈으로 시작하는 제목이
    # 표준 YAML 파서(Obsidian 등)에서 깨지지 않도록. url·date는 형식이 정해져 있어 그대로 둔다.
    frontmatter = (
        "---\n"
        f"title: {paths.quote_scalar(args.title)}\n"
        f"url: {args.url}\n"
        f"source: {paths.quote_scalar(args.source)}\n"
        f"date: {date_str}\n"
        "---\n\n"
    )

    note_path = os.path.join(notes_dir, filename)
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(frontmatter)
        f.write(body if body.endswith("\n") else body + "\n")

    target["note_path"] = filename
    target["qa_log"] = []

    with open(articles_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(json.dumps({"ok": True, "note_path": filename, "full_path": note_path},
                     ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--title", required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()

    body = sys.stdin.read()
    if not body.strip():
        fail("stdin body is empty")

    try:
        run(args, body)
    except OSError as e:
        # 노트 파일·articles.json 쓰기 실패 (권한, 용량, 파일명 길이 등)
        fail(f"{type(e).__name__}: {e}")
    except ValueError as e:
        # articles.json이 깨진 JSON (JSONDecodeError는 ValueError 하위)
        fail(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
