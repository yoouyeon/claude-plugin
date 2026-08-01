#!/usr/bin/env python3
"""config.yaml 관리: sources(list/add/remove) + notify(get/set) (stdlib only, dedup은 url 기준).

Usage:
    python3 manage_config.py sources list
    python3 manage_config.py sources add --name "<name>" --url "<url>"
    python3 manage_config.py sources remove --url "<url>"
    python3 manage_config.py notify get
    python3 manage_config.py notify set --backend slack|discord|none

config.yaml 형식(고정 — 이 형식 외 스타일은 지원하지 않음). 경로는 `paths.config_path()`:
    notes_path: '<노트 폴더 절대경로>'
    sources:
      - name: '토스 기술블로그'
        url: 'https://toss.tech/rss.xml'
    notify:
      backend: slack        # slack | discord | none

    - `notes_path`는 setup(`init_data_folder.py`)만 쓴다. 읽기는 `paths.notes_root()`.
    - `sources[].name`은 표시용, `url`이 fetch 대상. `articles.json`의 `source`가 이 `name`과 대응한다.

stdout (JSON):
    sources list:   {"sources": [{"name": "...", "url": "..."}, ...]}
    sources add:    성공 {"ok": true, "sources": [...]}
                    실패 {"ok": false, "error": "duplicate url"}      (exit code 1)
    sources remove: 성공 {"ok": true, "sources": [...]}
                    실패 {"ok": false, "error": "url not found"}      (exit code 1)
    notify get:     {"backend": "slack" | "discord" | "none"}
    notify set:     {"ok": true, "backend": "..."}
    I/O 실패 시:    {"ok": false, "error": "config.yaml I/O failed: ..."}  (exit code 1)
"""
import argparse
import json
import os
import re
import sys
from typing import NoReturn

import notify_backends
import paths

DEFAULT_BACKEND = notify_backends.NONE


def config_path():
    return paths.config_path()


def load_config(path):
    """config.yaml을 dict로 읽는다.

    `backend_set`은 `notify.backend` 키가 실제로 있었는지다 — 없으면 `backend`가
    DEFAULT_BACKEND로 채워지므로, "명시적으로 none"과 "키가 없음"을 구분하려면 이 값을 본다.
    """
    if not os.path.exists(path):
        return {"sources": [], "backend": DEFAULT_BACKEND, "backend_set": False, "notes_path": None}

    sources = []
    backend = None
    notes_path = None
    section = None
    pending_name = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            m_notes = re.match(r"^notes_path:\s*(.*?)\s*$", line)
            if m_notes:
                notes_path = paths.parse_scalar(m_notes.group(1)) or None
                continue
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
                    pending_name = paths.parse_scalar(m_name.group(1))
                elif m_url and pending_name is not None:
                    sources.append({"name": pending_name, "url": paths.parse_scalar(m_url.group(1))})
                    pending_name = None
            elif section == "notify":
                m_backend = re.match(r"^\s*backend\s*:\s*([\w-]+)", line)
                if m_backend:
                    backend = m_backend.group(1).lower()

    return {
        "sources": sources,
        "backend": backend or DEFAULT_BACKEND,
        "backend_set": backend is not None,
        "notes_path": notes_path,
    }


def save_config(path, config):
    """`notify` 블록은 `backend_set`이 true일 때만 쓴다 — 블록이 없는 상태가 "설정한 적 없음"이다."""
    lines = []
    if config.get("notes_path"):
        lines.append(f"notes_path: {paths.quote_scalar(config['notes_path'])}")
    lines.append("sources:")
    for s in config["sources"]:
        lines.append(f"  - name: {paths.quote_scalar(s['name'])}")
        lines.append(f"    url: {paths.quote_scalar(s['url'])}")
    if config.get("backend_set"):
        lines.append("notify:")
        lines.append(f"  backend: {config['backend']}")
    lines.append("")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def fail(msg) -> NoReturn:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def run(args):
    path = config_path()
    config = load_config(path)

    if args.target == "sources":
        if args.action == "list":
            print(json.dumps({"sources": config["sources"]}, ensure_ascii=False))
            return
        if args.action == "add":
            name = paths.one_line(args.name or "").strip()
            url = paths.one_line(args.url or "").strip()
            if not name or not url:
                fail("add requires --name and --url")
            if any(s["url"] == url for s in config["sources"]):
                fail("duplicate url")
            config["sources"].append({"name": name, "url": url})
            save_config(path, config)
            print(json.dumps({"ok": True, "sources": config["sources"]}, ensure_ascii=False))
            return
        if args.action == "remove":
            url = paths.one_line(args.url or "").strip()
            if not url:
                fail("remove requires --url")
            new_sources = [s for s in config["sources"] if s["url"] != url]
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
            config["backend_set"] = True
            save_config(path, config)
            print(json.dumps({"ok": True, "backend": config["backend"]}, ensure_ascii=False))
            return


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="target", required=True)

    p_sources = sub.add_parser("sources")
    p_sources.add_argument("action", choices=["list", "add", "remove"])
    p_sources.add_argument("--name")
    p_sources.add_argument("--url")

    p_notify = sub.add_parser("notify")
    p_notify.add_argument("action", choices=["get", "set"])
    p_notify.add_argument("--backend", choices=notify_backends.CHOICES)

    args = parser.parse_args()
    try:
        run(args)
    except OSError as e:
        fail(f"config.yaml I/O failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
