#!/usr/bin/env python3
"""notes/index.md 목차 재생성 (결정적, 에이전트 불필요).

Usage:
    python3 update_index.py

노트 폴더는 config.yaml의 `notes_path`에서 읽는다(`paths.notes_root()`).
그 폴더의 *.md (index.md 제외)를 스캔해 frontmatter(title/url/source/date)를 읽고 날짜 내림차순 목차를 index.md 로 덮어쓴다.
frontmatter 없으면 파일명·첫 H1 로 대체.
"""
import os
import re
import sys
from typing import NoReturn

import paths


def die(msg) -> NoReturn:
    print(f"update_index.py error: {msg}", file=sys.stderr)
    sys.exit(1)


def md_text(value):
    """링크 텍스트로 안전하게. 홀로 있는 `[`·`]`가 링크를 끊는다."""
    return value.replace("[", r"\[").replace("]", r"\]")


def md_url(value):
    """링크 대상으로 안전하게. 괄호·공백이 든 URL은 `<...>`로 감싸 끝을 정확히 잡는다.

    `<`·`>`는 감싸기 전에 퍼센트 인코딩한다. 그대로 두면 감싼 괄호가 그 자리에서 닫혀버린다.
    """
    safe = value.replace("<", "%3C").replace(">", "%3E")
    return f"<{safe}>" if any(c in safe for c in "() ") else safe


def parse_note(path):
    meta = {}
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, ValueError):
        # 이 노트만 메타데이터 없이 넘어간다. 하나 때문에 목차 생성을 멈추지 않는다.
        return meta
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, flags=re.S)
    if m:
        for line in m.group(1).splitlines():
            kv = re.match(r"^([\w-]+)\s*:\s*(.+?)\s*$", line)
            if kv:
                # save_note.py가 quote_scalar로 쓴 값을 같은 코덱으로 되읽는다.
                meta[kv.group(1).lower()] = paths.parse_scalar(kv.group(2))
    if "title" not in meta:
        h1 = re.search(r"^#\s+(.+)$", text, flags=re.M)
        if h1:
            meta["title"] = h1.group(1).strip()
    return meta


def run():
    notes_dir = paths.notes_root()
    if not notes_dir:
        die("notes_path not configured (run /articles-os:setup)")
    if not os.path.isdir(notes_dir):
        die(f"notes dir not found: {notes_dir}")

    rows = []
    for fname in os.listdir(notes_dir):
        lowered = fname.lower()
        if not lowered.endswith(".md") or lowered == "index.md":
            continue
        full = os.path.join(notes_dir, fname)
        if not os.path.isfile(full):
            continue
        meta = parse_note(full)
        date = meta.get("date")
        if not date:
            m = re.match(r"^(\d{4}-\d{2}-\d{2})", fname)
            date = m.group(1) if m else ""
        title = meta.get("title") or os.path.splitext(fname)[0]
        rows.append({
            "date": date,
            "title": title,
            "source": meta.get("source", ""),
            "url": meta.get("url", ""),
            "file": fname,
        })

    rows.sort(key=lambda r: (r["date"], r["file"]), reverse=True)

    lines = ["# 학습 메모 목차", "", f"총 {len(rows)}개", ""]
    for r in rows:
        line = f"- {r['date']} · [{md_text(r['title'])}]({md_url(r['file'])})"
        if r["source"]:
            line += f" · {md_text(r['source'])}"
        if r["url"]:
            line += f" · [원문]({md_url(r['url'])})"
        lines.append(line)
    lines.append("")

    index_path = os.path.join(notes_dir, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"updated {index_path} ({len(rows)} notes)")


def main():
    try:
        run()
    except OSError as e:
        die(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
