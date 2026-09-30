#!/usr/bin/env python3
"""Print the configured solution directory as an absolute path."""

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("사용법: solution_dir.py <저장소 루트>", file=sys.stderr)
        return 1

    root = Path(sys.argv[1]).resolve()
    config_path = root / ".leetlog.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    except (OSError, json.JSONDecodeError) as error:
        print(f"{config_path}을 읽을 수 없습니다: {error}", file=sys.stderr)
        return 1

    if not isinstance(config, dict):
        print(f"{config_path}: JSON 객체여야 합니다", file=sys.stderr)
        return 1

    directory = config.get("solutions_dir", "solutions")
    if (
        not isinstance(directory, str)
        or not directory.strip()
        or Path(directory).is_absolute()
        or ".." in Path(directory).parts
        or Path(directory) == Path(".")
    ):
        print(f"{config_path}: solutions_dir는 저장소 안의 상대 경로여야 합니다", file=sys.stderr)
        return 1

    path = (root / directory).resolve()
    if path == root or not path.is_relative_to(root):
        print(f"{config_path}: solutions_dir는 저장소 안의 하위 디렉토리여야 합니다", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
