#!/usr/bin/env python3
"""sources.yaml 관리: list / add / remove (stdlib only, dedup은 url 기준).

Usage:
    python3 manage_sources.py list <data-path>
    python3 manage_sources.py add <data-path> --name "<name>" --url "<url>"
    python3 manage_sources.py remove <data-path> --url "<url>"

sources.yaml 형식(고정 — 이 형식 외 스타일은 지원하지 않음):
    sources:
      - name: <name>
        url: <url>

stdout (JSON):
    list:   {"sources": [{"name": "...", "url": "..."}, ...]}
    add:    성공 {"ok": true, "sources": [...]}
            실패 {"ok": false, "error": "duplicate url"}          (exit code 1)
    remove: 성공 {"ok": true, "sources": [...]}
            실패 {"ok": false, "error": "url not found"}          (exit code 1)
"""
import argparse
import json
import os
import re
import sys


def sources_path(data_path):
    return os.path.join(os.path.expanduser(data_path), "config", "sources.yaml")


def load_sources(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        text = f.read()

    sources = []
    pending_name = None
    for line in text.splitlines():
        m_name = re.match(r"^\s*-\s*name:\s*(.+?)\s*$", line)
        m_url = re.match(r"^\s*url:\s*(.+?)\s*$", line)
        if m_name:
            pending_name = m_name.group(1).strip().strip("\"'")
        elif m_url and pending_name is not None:
            sources.append({"name": pending_name, "url": m_url.group(1).strip().strip("\"'")})
            pending_name = None
    return sources


def save_sources(path, sources):
    lines = ["sources:"]
    for s in sources:
        lines.append(f"  - name: {s['name']}")
        lines.append(f"    url: {s['url']}")
    lines.append("")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def fail(msg):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["list", "add", "remove"])
    parser.add_argument("data_path")
    parser.add_argument("--name")
    parser.add_argument("--url")
    args = parser.parse_args()

    path = sources_path(args.data_path)
    sources = load_sources(path)

    if args.action == "list":
        print(json.dumps({"sources": sources}, ensure_ascii=False))
        return

    if args.action == "add":
        if not args.name or not args.url:
            fail("add requires --name and --url")
        if any(s["url"] == args.url for s in sources):
            fail("duplicate url")
        sources.append({"name": args.name, "url": args.url})
        save_sources(path, sources)
        print(json.dumps({"ok": True, "sources": sources}, ensure_ascii=False))
        return

    if args.action == "remove":
        if not args.url:
            fail("remove requires --url")
        new_sources = [s for s in sources if s["url"] != args.url]
        if len(new_sources) == len(sources):
            fail("url not found")
        save_sources(path, new_sources)
        print(json.dumps({"ok": True, "sources": new_sources}, ensure_ascii=False))
        return


if __name__ == "__main__":
    main()
