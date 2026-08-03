#!/usr/bin/env python3
"""기계 상태 폴더와 노트 폴더 초기화 (stdlib only).

Usage:
    python3 init_data_folder.py --notes-path <노트 폴더 경로>

동작:
    두 곳을 만든다.

    1. 기계 상태. `paths.data_root()`(`~/.articles-os`, 고정)에 articles.json / state.json 생성.
    2. 사용자 산출물. `<노트 폴더>/notes/` 생성하고, 그 절대경로를 config.yaml의 `notes_path`에 기록한다
                    (config.yaml은 이 단계에서 `manage_config`가 만든다, 가장 마지막에 쓰므로 중간에 실패하면 `paths.initialized()`가 false로 남는다).
                    이후 모든 스킬은 이 기록을 통해 노트 폴더를 찾는다.

    articles.json·state.json은 이미 있으면 건드리지 않는다.
    config.yaml은 매번 다시 쓰지만 기존 sources·notify는 보존하고 notes_path만 갱신한다.

    상대경로를 받으면 현재 작업 디렉토리 기준으로 절대경로를 확정한다(거부하지 않는다).

stdout (JSON):
    성공 {"ok": true, "data_root": "...", "notes_root": "..."}
    실패 {"ok": false, "error": "..."} (exit code 1)
"""
import argparse
import json
import os
import sys
from typing import NoReturn

import manage_config
import paths

INITIAL_FILES = {
    "articles.json": '{\n  "articles": []\n}\n',
    "state.json": '{\n  "last_run": null,\n  "sources": {}\n}\n',
}


def fail(msg) -> NoReturn:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes-path", required=True)
    args = parser.parse_args()

    # 빈 값을 realpath에 넘기면 조용히 cwd가 되므로 먼저 막는다.
    if not args.notes_path.strip():
        fail("notes path is empty")

    # realpath가 상대경로도 cwd 기준 절대경로로 확정한다.
    notes_base = os.path.realpath(os.path.expanduser(args.notes_path))
    data_root = paths.data_root()
    notes_root = os.path.join(notes_base, "notes")

    try:
        # 1. 기계 상태 (고정 경로)
        os.makedirs(data_root, exist_ok=True)
        for rel, content in INITIAL_FILES.items():
            full = os.path.join(data_root, rel)
            if not os.path.exists(full):
                with open(full, "w", encoding="utf-8") as f:
                    f.write(content)

        # 2. 사용자 산출물 + notes_path 기록 (config.yaml 쓰기는 항상 마지막, 순서 바꾸지 말 것)
        os.makedirs(notes_root, exist_ok=True)
        config_file = paths.config_path()
        config = manage_config.load_config(config_file)
        config["notes_path"] = notes_root
        manage_config.save_config(config_file, config)
    except OSError as e:
        fail(f"{type(e).__name__}: {e}")

    print(json.dumps({"ok": True, "data_root": data_root, "notes_root": notes_root},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
