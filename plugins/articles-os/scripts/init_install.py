#!/usr/bin/env python3
"""신규 설치 초기화 + registry.json 관리 (stdlib only).

Usage:
    python3 init_install.py create <data-path> --label "<라벨>"
    python3 init_install.py set-scheduler-job <install_id> <job_id>

동작 (create):
    1. install_id 생성 (uuid4 hex 앞 8자리).
    2. <data-path>를 절대경로로 정규화하고 config/data/notes 하위 디렉토리와
       초기 파일(sources.yaml, notify.yaml, articles.json, state.json)을 생성한다
       (이미 있으면 건드리지 않는다).
    3. ~/.articles-os/registry.json 을 읽어(없으면 새로 만들어) 새 설치 항목을
       ({install_id, path, label, scheduler_job_id: null, created_at}) 추가하고 저장한다.
    4. ~/.articles-os/logs/ 디렉토리를 만든다.

동작 (set-scheduler-job):
    registry.json에서 <install_id> 항목을 찾아 scheduler_job_id를 갱신한다.

stdout (JSON):
    create:            {"install_id": "...", "path": "<절대경로>"}
    set-scheduler-job: 성공 {"ok": true}
                        실패 {"ok": false, "error": "..."}  (exit code 1)
"""
import argparse
import json
import os
import sys
import uuid
from datetime import datetime

HOME_DIR = os.path.expanduser("~/.articles-os")
REGISTRY = os.path.join(HOME_DIR, "registry.json")
LOGS_DIR = os.path.join(HOME_DIR, "logs")

INITIAL_FILES = {
    os.path.join("config", "sources.yaml"): "sources: []\n",
    os.path.join("config", "notify.yaml"): "backend: none\n",
    os.path.join("data", "articles.json"): '{\n  "articles": []\n}\n',
    os.path.join("data", "state.json"): '{\n  "last_run": null,\n  "sources": {}\n}\n',
}


def fail(msg):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def load_registry():
    if not os.path.exists(REGISTRY):
        return {"installs": []}
    with open(REGISTRY, encoding="utf-8") as f:
        try:
            doc = json.load(f)
        except Exception:
            doc = {}
    doc.setdefault("installs", [])
    return doc


def save_registry(doc):
    os.makedirs(HOME_DIR, exist_ok=True)
    with open(REGISTRY, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")


def cmd_create(args):
    data_path = os.path.realpath(os.path.expanduser(args.data_path))

    for sub in ("config", "data", "notes"):
        os.makedirs(os.path.join(data_path, sub), exist_ok=True)

    for rel, content in INITIAL_FILES.items():
        full = os.path.join(data_path, rel)
        if not os.path.exists(full):
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)

    install_id = uuid.uuid4().hex[:8]
    label = args.label or os.path.basename(data_path)

    os.makedirs(LOGS_DIR, exist_ok=True)

    registry = load_registry()
    registry["installs"].append({
        "install_id": install_id,
        "path": data_path,
        "label": label,
        "scheduler_job_id": None,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    })
    save_registry(registry)

    print(json.dumps({"install_id": install_id, "path": data_path}, ensure_ascii=False))


def cmd_set_scheduler_job(args):
    registry = load_registry()
    for ins in registry["installs"]:
        if ins.get("install_id") == args.install_id:
            ins["scheduler_job_id"] = args.job_id
            save_registry(registry)
            print(json.dumps({"ok": True}, ensure_ascii=False))
            return
    fail(f"install_id not found in registry: {args.install_id}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)

    p_create = sub.add_parser("create")
    p_create.add_argument("data_path")
    p_create.add_argument("--label", default=None)

    p_job = sub.add_parser("set-scheduler-job")
    p_job.add_argument("install_id")
    p_job.add_argument("job_id")

    args = parser.parse_args()
    if args.action == "create":
        cmd_create(args)
    else:
        cmd_set_scheduler_job(args)


if __name__ == "__main__":
    main()
