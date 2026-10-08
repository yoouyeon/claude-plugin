#!/usr/bin/env python3
"""임시 파일 경로를 만들고, 다 쓴 임시 파일을 최종 위치로 옮긴다 (stdlib only).

Usage:
    python3 draft.py new <작업 디렉토리> <종류>
    python3 draft.py move <임시 파일> <최종 경로> [--force]

new:
    <작업 디렉토리>/.devdocs/를 만들고 임시 파일 경로를 출력한다. 파일은 만들지 않는다.
    이름은 <YYYYMMDD-HHMM>-<종류>.md이고, 이미 있으면 -2, -3을 붙인다.
    <종류>: spec, memo, pr, issue, readme
    exit 0: <임시 파일 절대 경로>
    exit 2: 인자 오류

move:
    필요하면 상위 디렉토리를 만들고 옮긴다.
    exit 0: <최종 경로 절대 경로>
    exit 2: 인자 오류, 임시 파일 없음, 옮기기 실패
    exit 3: 최종 경로에 파일이 이미 있음. --force가 있으면 덮어쓴다.
"""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

TYPES = ("spec", "memo", "pr", "issue", "readme")


def new(root: Path, doc_type: str) -> int:
    directory = root.resolve() / ".devdocs"
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{datetime.now():%Y%m%d-%H%M}-{doc_type}"
    path = directory / f"{stem}.md"
    suffix = 2
    while path.exists():
        path = directory / f"{stem}-{suffix}.md"
        suffix += 1
    print(path)
    return 0


def move(source: Path, destination: Path, force: bool) -> int:
    if not source.is_file():
        print(f"{source}이 없습니다", file=sys.stderr)
        return 2
    destination = destination.resolve()
    if destination.exists() and not force:
        print(f"{destination}에 파일이 이미 있습니다", file=sys.stderr)
        return 3
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
    except OSError as error:
        print(f"옮기지 못했습니다: {error}", file=sys.stderr)
        return 2
    print(destination)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    new_parser = commands.add_parser("new")
    new_parser.add_argument("root")
    new_parser.add_argument("type", choices=TYPES)
    move_parser = commands.add_parser("move")
    move_parser.add_argument("source")
    move_parser.add_argument("destination")
    move_parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.command == "new":
        return new(Path(args.root), args.type)
    return move(Path(args.source), Path(args.destination), args.force)


if __name__ == "__main__":
    sys.exit(main())
