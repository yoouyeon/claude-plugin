#!/usr/bin/env python3
"""notes/index.md 목차 재생성 (결정적 — 에이전트 불필요).

Usage:
    python3 update_index.py <data-path>

<data-path>/notes/*.md (index.md 제외)를 스캔해 frontmatter(title/url/source/date)를
읽고 날짜 내림차순 목차를 index.md 로 덮어쓴다. frontmatter 없으면 파일명·첫 H1 로 대체.
"""
import os
import re
import sys


def parse_note(path):
    meta = {}
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return meta
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, flags=re.S)
    if m:
        for line in m.group(1).splitlines():
            kv = re.match(r"^([\w-]+)\s*:\s*(.+?)\s*$", line)
            if kv:
                meta[kv.group(1).lower()] = kv.group(2).strip("\"'")
    if "title" not in meta:
        h1 = re.search(r"^#\s+(.+)$", text, flags=re.M)
        if h1:
            meta["title"] = h1.group(1).strip()
    return meta


def main():
    if len(sys.argv) != 2:
        print("usage: update_index.py <data-path>", file=sys.stderr)
        sys.exit(1)
    notes_dir = os.path.join(os.path.expanduser(sys.argv[1]), "notes")
    if not os.path.isdir(notes_dir):
        print(f"notes dir not found: {notes_dir}", file=sys.stderr)
        sys.exit(1)

    rows = []
    for fname in os.listdir(notes_dir):
        if not fname.endswith(".md") or fname == "index.md":
            continue
        meta = parse_note(os.path.join(notes_dir, fname))
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
        line = f"- {r['date']} · [{r['title']}]({r['file']})"
        if r["source"]:
            line += f" · {r['source']}"
        if r["url"]:
            line += f" · [원문]({r['url']})"
        lines.append(line)
    lines.append("")

    index_path = os.path.join(notes_dir, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"updated {index_path} ({len(rows)} notes)")


if __name__ == "__main__":
    main()
