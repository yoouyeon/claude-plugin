#!/usr/bin/env python3
"""활성 설치 결정 (규칙: cwd 하위 → 단일 설치 → 목록).

Usage:
    python3 resolve_install.py [--cwd <path>]

stdout (JSON):
    {"reason": "cwd" | "single" | "multiple" | "none",
     "match": {install...} | null,
     "installs": [ ... 전체 목록 ... ]}

reason 의미:
    cwd      — 현재 폴더가 어떤 설치 path 하위 → match 사용
    single   — 설치가 하나뿐 → match 사용
    multiple — 후보 여러 개 → installs 를 사용자에게 제시하고 선택 받기
    none     — 설치 없음 → setup 유도
"""
import json
import os
import sys

REGISTRY = os.path.expanduser("~/.articles-os/registry.json")


def main():
    cwd = os.getcwd()
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--cwd":
        cwd = args[1]
    cwd = os.path.realpath(cwd)

    installs = []
    if os.path.exists(REGISTRY):
        try:
            with open(REGISTRY, encoding="utf-8") as f:
                installs = json.load(f).get("installs", [])
        except Exception:
            installs = []

    if not installs:
        print(json.dumps({"reason": "none", "match": None, "installs": []}, ensure_ascii=False))
        return

    for ins in installs:
        path = os.path.realpath(os.path.expanduser(ins.get("path", "")))
        if cwd == path or cwd.startswith(path + os.sep):
            print(json.dumps({"reason": "cwd", "match": ins, "installs": installs}, ensure_ascii=False))
            return

    if len(installs) == 1:
        print(json.dumps({"reason": "single", "match": installs[0], "installs": installs}, ensure_ascii=False))
        return

    print(json.dumps({"reason": "multiple", "match": None, "installs": installs}, ensure_ascii=False))


if __name__ == "__main__":
    main()
