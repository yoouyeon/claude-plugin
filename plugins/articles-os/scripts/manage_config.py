#!/usr/bin/env python3
"""config.yaml 관리: sources(list/add/remove) + notify(get/set) (stdlib only, dedup은 url 기준).

Usage:
    python3 manage_config.py sources list <data-path>
    python3 manage_config.py sources add <data-path> --name "<name>" --url "<url>"
    python3 manage_config.py sources remove <data-path> --url "<url>"
    python3 manage_config.py notify get <data-path>
    python3 manage_config.py notify set <data-path> --backend slack|none

config.yaml 형식(고정 — 이 형식 외 스타일은 지원하지 않음):
    sources:
      - name: <name>
        url: <url>
    notify:
      backend: <slack|none>

stdout (JSON):
    sources list:   {"sources": [{"name": "...", "url": "..."}, ...]}
    sources add:    성공 {"ok": true, "sources": [...]}
                    실패 {"ok": false, "error": "duplicate url"}      (exit code 1)
    sources remove: 성공 {"ok": true, "sources": [...]}
                    실패 {"ok": false, "error": "url not found"}      (exit code 1)
    notify get:     {"backend": "slack" | "none"}
    notify set:     {"ok": true, "backend": "..."}
"""
import argparse
import json
import os
import re
import sys

DEFAULT_BACKEND = "none"


def config_path(data_path):
    return os.path.join(os.path.expanduser(data_path), "config.yaml")


def load_config(path):
    if not os.path.exists(path):
        return {"sources": [], "backend": DEFAULT_BACKEND}

    sources = []
    backend = DEFAULT_BACKEND
    section = None
    pending_name = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if re.match(r"^sources:\s*$", line):
                section = "sources"
                continue
            if re.match(r"^notify:\s*$", line):
                section = "notify"
                continue
            if section == "sources":
                m_name = re.match(r"^\s*-\s*name:\s*(.+?)\s*$", line)
                m_url = re.match(r"^\s*url:\s*(.+?)\s*$", line)
                if m_name:
                    pending_name = m_name.group(1).strip().strip("\"'")
                elif m_url and pending_name is not None:
                    sources.append({"name": pending_name, "url": m_url.group(1).strip().strip("\"'")})
                    pending_name = None
            elif section == "notify":
                m_backend = re.match(r"^\s*backend\s*:\s*([\w-]+)", line)
                if m_backend:
                    backend = m_backend.group(1).lower()

    return {"sources": sources, "backend": backend}


def save_config(path, config):
    lines = ["sources:"]
    for s in config["sources"]:
        lines.append(f"  - name: {s['name']}")
        lines.append(f"    url: {s['url']}")
    lines.append("notify:")
    lines.append(f"  backend: {config['backend']}")
    lines.append("")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def fail(msg):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="target", required=True)

    p_sources = sub.add_parser("sources")
    p_sources.add_argument("action", choices=["list", "add", "remove"])
    p_sources.add_argument("data_path")
    p_sources.add_argument("--name")
    p_sources.add_argument("--url")

    p_notify = sub.add_parser("notify")
    p_notify.add_argument("action", choices=["get", "set"])
    p_notify.add_argument("data_path")
    p_notify.add_argument("--backend", choices=["slack", "none"])

    args = parser.parse_args()
    path = config_path(args.data_path)
    config = load_config(path)

    if args.target == "sources":
        if args.action == "list":
            print(json.dumps({"sources": config["sources"]}, ensure_ascii=False))
            return
        if args.action == "add":
            if not args.name or not args.url:
                fail("add requires --name and --url")
            if any(s["url"] == args.url for s in config["sources"]):
                fail("duplicate url")
            config["sources"].append({"name": args.name, "url": args.url})
            save_config(path, config)
            print(json.dumps({"ok": True, "sources": config["sources"]}, ensure_ascii=False))
            return
        if args.action == "remove":
            if not args.url:
                fail("remove requires --url")
            new_sources = [s for s in config["sources"] if s["url"] != args.url]
            if len(new_sources) == len(config["sources"]):
                fail("url not found")
            config["sources"] = new_sources
            save_config(path, config)
            print(json.dumps({"ok": True, "sources": config["sources"]}, ensure_ascii=False))
            return

    if args.target == "notify":
        if args.action == "get":
            print(json.dumps({"backend": config["backend"]}, ensure_ascii=False))
            return
        if args.action == "set":
            if not args.backend:
                fail("set requires --backend")
            config["backend"] = args.backend
            save_config(path, config)
            print(json.dumps({"ok": True, "backend": config["backend"]}, ensure_ascii=False))
            return


if __name__ == "__main__":
    main()
