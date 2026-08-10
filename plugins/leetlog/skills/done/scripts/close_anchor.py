#!/usr/bin/env python3
"""풀이 파일의 미마감 ANCHOR를 찾아 소요 시간을 기록한다 (stdlib only).

Usage:
    python3 close_anchor.py <풀이 파일 경로> [--now "YYYY.MM.DD HH:MM"]

동작:
    1. 파일에서 `ANCHOR YYYY.MM.DD HH:MM 풀이` 형태의 줄을 찾는다.
    2. 정확히 하나면 시작 시각과 현재 시각의 차이를 분으로 계산한다.
    3. 그 줄의 `HH:MM`을 지우고 `(N분 소요)` 또는 `(N시간 M분 소요)`를 붙여 파일에 쓴다.

    줄 주석 문법과 줄 안의 나머지 내용은 건드리지 않는다. 다른 줄도 고치지 않는다.

stdout:
    exit 0 — 마감함
        <경로>:<줄번호>
        - <바꾸기 전 줄>
        + <바꾼 뒤 줄>
    exit 2 — 미마감 ANCHOR가 없음 (이미 마감된 파일)
    exit 1 — 그 외 (파일 열기 실패, 미마감 ANCHOR 2개 이상, 날짜·시각이 올바르지 않음)
"""
import argparse
import re
import sys
from datetime import datetime

TIME_FORMAT = "%Y.%m.%d %H:%M"
ANCHOR = re.compile(r"ANCHOR\s+(\d{4}\.\d{2}\.\d{2})\s+(\d{2}:\d{2})\s+풀이")


def parse_local(text: str) -> datetime:
    """`YYYY.MM.DD HH:MM`을 로컬 타임존이 붙은 datetime으로 읽는다."""
    return datetime.strptime(text, TIME_FORMAT).astimezone()


def format_elapsed(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes}분 소요"
    hours, rest = divmod(minutes, 60)
    if rest == 0:
        return f"{hours}시간 소요"
    return f"{hours}시간 {rest}분 소요"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--now", help="기준 시각 (YYYY.MM.DD HH:MM). 없으면 현재 시각")
    args = parser.parse_args()

    if args.now:
        try:
            now = parse_local(args.now)
        except ValueError:
            print(f"--now 형식이 올바르지 않습니다: {args.now}")
            return 1
    else:
        now = datetime.now().astimezone()

    try:
        with open(args.path, encoding="utf-8", newline="") as f:
            lines = f.read().splitlines(keepends=True)
    except OSError as e:
        print(f"파일을 열 수 없습니다: {args.path} ({e.strerror})")
        return 1

    hits = []
    for i, line in enumerate(lines):
        match = ANCHOR.search(line)
        if match:
            hits.append((i, match))

    if not hits:
        print(f"미마감 ANCHOR가 없습니다: {args.path}")
        return 2

    if len(hits) > 1:
        print(f"미마감 ANCHOR가 {len(hits)}개입니다: {args.path}")
        for i, _ in hits:
            print(f"  {i + 1}: {lines[i].rstrip()}")
        return 1

    index, match = hits[0]
    started_date, started_time = match.groups()
    try:
        started = parse_local(f"{started_date} {started_time}")
    except ValueError:
        print(f"ANCHOR의 날짜·시각이 올바르지 않습니다: {match.group(0)}")
        return 1

    minutes = int((now - started).total_seconds() // 60)
    if minutes < 0:
        print(f"ANCHOR의 시작 시각이 현재 시각보다 미래입니다: {match.group(0)}")
        return 1

    before = lines[index]
    after = ANCHOR.sub(
        f"ANCHOR {started_date} 풀이 ({format_elapsed(minutes)})",
        before,
        count=1,
    )
    lines[index] = after

    with open(args.path, "w", encoding="utf-8", newline="") as f:
        f.write("".join(lines))

    print(f"{args.path}:{index + 1}")
    print(f"- {before.rstrip()}")
    print(f"+ {after.rstrip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
