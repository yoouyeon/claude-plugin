#!/usr/bin/env python3
"""데이터 폴더 초기화 (stdlib only).

Usage:
    python3 init_data_folder.py <data-path>

동작:
    <data-path>를 절대경로로 정규화하고 config.yaml / articles.json / state.json /
    notes/ 를 생성한다 (이미 있으면 건드리지 않는다).

stdout (JSON): {"path": "<절대경로>"}
"""
import json
import os
import sys

INITIAL_FILES = {
    "config.yaml": "sources:\nnotify:\n  backend: none\n",
    "articles.json": '{\n  "articles": []\n}\n',
    "state.json": '{\n  "last_run": null,\n  "sources": {}\n}\n',
}


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"ok": False, "error": "usage: init_data_folder.py <data-path>"}, ensure_ascii=False))
        sys.exit(1)

    data_path = os.path.realpath(os.path.expanduser(sys.argv[1]))
    os.makedirs(data_path, exist_ok=True)
    os.makedirs(os.path.join(data_path, "notes"), exist_ok=True)

    for rel, content in INITIAL_FILES.items():
        full = os.path.join(data_path, rel)
        if not os.path.exists(full):
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)

    print(json.dumps({"path": data_path}, ensure_ascii=False))


if __name__ == "__main__":
    main()
