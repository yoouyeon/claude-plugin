#!/usr/bin/env python3
"""풀이 파일의 맨 위 회차를 풀이 문서의 날짜 섹션으로 옮긴다 (stdlib only).

Usage:
    python3 write_doc.py <풀이 파일 경로> --fence <펜스 태그> [옵션]

옵션:
    --doc <경로>        문서 경로를 직접 지정한다. 없으면 풀이 파일 경로에서 유도한다.
    --title <값>        헤더에서 못 읽은 메타를 대신 넘긴다. 번호가 빠져 있으면 파일명에서 읽어 `<번호>. <제목>`으로 맞춘다.
    --difficulty <값>
    --url <값>
    --tags <값>         쉼표로 구분. 빈 문자열이면 태그 없음.
    --now "<ISO>"       기준 시각. 없으면 현재 시각.

동작:
    1. 풀이 파일에서 맨 위 `ANCHOR YYYY.MM.DD [HH:MM] 풀이` 줄을 찾는다.
    2. 그 줄 다음부터 다음 ANCHOR 줄 직전까지를 이번 회차 코드로 잘라낸다.
    3. 문서가 없으면 frontmatter와 빈 칸 주석을 갖춘 문서를 새로 만들고, 있으면 첫 `## ` 섹션 바로 위에 날짜 섹션을 끼워 넣고 `updated`를 갱신한다.

    기존 섹션과 사용자가 쓴 본문은 고치지 않는다. frontmatter는 `updated`만 고친다.

stdout:
    exit 0 — 문서를 만들었거나 섹션을 추가했다
        <문서 경로>
        + ## YYYY-MM-DD (새 문서 | 섹션 추가)
        ! <헤더와 frontmatter가 어긋난 항목>   (있을 때만)
    exit 1 — 그 외 (파일 열기 실패, ANCHOR 없음, 코드 비어 있음, 헤더 메타 부족 등)
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ANCHOR = re.compile(r"ANCHOR\s+(\d{4})\.(\d{2})\.(\d{2})(?:\s+\d{2}:\d{2})?\s+풀이")
HEADER_PROBLEM = re.compile(r"문제\s*:\s*(.+?)\s*-\s*(.+?)\s*$")
HEADER_DIFFICULTY = re.compile(r"난이도\s*:\s*(.+?)\s*$")
HEADER_URL = re.compile(r"링크\s*:\s*(\S+)")
HEADER_TAGS = re.compile(r"태그\s*:\s*(.+?)\s*$")
FRONTMATTER_FIELD = re.compile(r"^([A-Za-z_]+):\s*(.*?)\s*$")
NOTES_PLACEHOLDER = "<!-- Write your notes here -->"


def read_text(path: Path) -> tuple[list[str], str]:
    """파일을 줄 목록과 줄바꿈 문자로 읽는다. 줄바꿈을 변환하지 않고 원본대로 본다."""
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines, newline


def trim_blank(lines: list[str]) -> list[str]:
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def parse_tags(raw: str) -> list[str]:
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


def ensure_number(title: str, number: str) -> str:
    """제목 앞에 문제 번호가 없으면 붙인다. `commit`이 여기서 번호를 읽는다."""
    stripped = title.strip()
    tail = stripped[len(number) : len(number) + 1]
    if stripped.startswith(number) and not tail.isdigit():
        return stripped
    return f"{number}. {stripped}"


def format_tags(tags: list[str]) -> str:
    return f"[{', '.join(tags)}]"


def read_header(lines: list[str], limit: int) -> dict:
    """풀이 파일 맨 위 ANCHOR 위쪽에서 메타를 읽는다."""
    meta = {}
    for line in lines[:limit]:
        problem = HEADER_PROBLEM.search(line)
        if problem and "title" not in meta:
            number, title = problem.groups()
            meta["title"] = f"{number}. {title}"
            continue
        difficulty = HEADER_DIFFICULTY.search(line)
        if difficulty and "difficulty" not in meta:
            meta["difficulty"] = difficulty.group(1)
            continue
        url = HEADER_URL.search(line)
        if url and "url" not in meta:
            meta["url"] = url.group(1)
            continue
        tags = HEADER_TAGS.search(line)
        if tags and "tags" not in meta:
            meta["tags"] = parse_tags(tags.group(1))
    return meta


def find_frontmatter(lines: list[str]) -> tuple[int, int] | None:
    """frontmatter 본문의 시작 인덱스와 닫는 `---`의 인덱스를 돌려준다."""
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return 1, i
    return None


def build_section(date: str, fence: str, code: list[str]) -> list[str]:
    marker = "```"
    while any(marker in line for line in code):
        marker += "`"
    return [f"## {date}", "", f"{marker}{fence}", *code, marker]


def build_document(
    date: str, fence: str, code: list[str], meta: dict, stamp: str
) -> list[str]:
    return [
        "---",
        f"title: {meta['title']}",
        f"created: {stamp}",
        f"updated: {stamp}",
        f"difficulty: {meta['difficulty']}",
        f"tags: {format_tags(meta['tags'])}",
        f"url: {meta['url']}",
        "---",
        "",
        NOTES_PLACEHOLDER,
        "",
        *build_section(date, fence, code),
        "",
    ]


def merge_document(
    lines: list[str], date: str, fence: str, code: list[str], meta: dict, stamp: str
) -> tuple[list[str], list[str]]:
    """기존 문서에 날짜 섹션을 끼워 넣고 `updated`를 갱신한다."""
    bounds = find_frontmatter(lines)
    if bounds is None:
        raise ValueError("문서에 frontmatter가 없습니다")
    body_start, closing = bounds

    merged = list(lines)
    existing = {}
    updated_at = None
    for i in range(body_start, closing):
        field = FRONTMATTER_FIELD.match(lines[i])
        if not field:
            continue
        key, value = field.groups()
        existing[key] = value
        if key == "updated":
            updated_at = i
    if updated_at is None:
        raise ValueError("문서 frontmatter에 updated 항목이 없습니다")
    merged[updated_at] = f"updated: {stamp}"

    mismatches = []
    for key in ("title", "difficulty", "url"):
        if key in existing and existing[key] != meta[key]:
            mismatches.append(f"{key}: 헤더 `{meta[key]}` / 문서 `{existing[key]}`")
    header_tags = format_tags(meta["tags"])
    if "tags" in existing and existing["tags"] != header_tags:
        mismatches.append(f"tags: 헤더 `{header_tags}` / 문서 `{existing['tags']}`")

    section = build_section(date, fence, code)
    for i in range(closing + 1, len(merged)):
        if merged[i].startswith("## "):
            merged[i:i] = [*section, ""]
            return merged, mismatches

    tail = [*section, ""]
    if merged and merged[-1].strip():
        tail.insert(0, "")
    merged.extend(tail)
    return merged, mismatches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--fence", required=True, help="마크다운 코드 펜스 태그")
    parser.add_argument("--doc", help="문서 경로. 없으면 풀이 파일 경로에서 유도")
    parser.add_argument("--title")
    parser.add_argument("--difficulty")
    parser.add_argument("--url")
    parser.add_argument("--tags", help="쉼표로 구분. 빈 문자열이면 태그 없음")
    parser.add_argument("--now", help="기준 시각 (ISO 8601). 없으면 현재 시각")
    args = parser.parse_args()

    if args.now:
        try:
            stamp = datetime.fromisoformat(args.now).replace(microsecond=0).isoformat()
        except ValueError:
            print(f"--now 형식이 올바르지 않습니다: {args.now}")
            return 1
    else:
        stamp = datetime.now().astimezone().replace(microsecond=0).isoformat()

    solution = Path(args.path)
    try:
        lines, _ = read_text(solution)
    except OSError as e:
        print(f"파일을 열 수 없습니다: {solution} ({e.strerror})")
        return 1

    hits = [i for i, line in enumerate(lines) if ANCHOR.search(line)]
    if not hits:
        print(f"ANCHOR가 없습니다: {solution}")
        return 1

    top = hits[0]
    year, month, day = ANCHOR.search(lines[top]).groups()
    date = f"{year}-{month}-{day}"

    end = hits[1] if len(hits) > 1 else len(lines)
    code = trim_blank(lines[top + 1 : end])
    if not code:
        print(f"맨 위 회차에 코드가 없습니다: {solution}:{top + 1}")
        return 1

    meta = read_header(lines, top)
    if args.title:
        meta["title"] = args.title
    if args.difficulty:
        meta["difficulty"] = args.difficulty
    if args.url:
        meta["url"] = args.url
    if args.tags is not None:
        meta["tags"] = parse_tags(args.tags)
    meta.setdefault("tags", [])

    number = re.match(r"(\d+)_", solution.stem)
    if number and "title" in meta:
        meta["title"] = ensure_number(meta["title"], number.group(1))

    missing = [key for key in ("title", "difficulty", "url") if key not in meta]
    if missing:
        print(f"헤더에서 읽지 못한 항목이 있습니다: {', '.join(missing)}")
        print("--title, --difficulty, --url 로 넘겨 다시 실행하세요.")
        return 1

    if args.doc:
        doc = Path(args.doc)
    else:
        try:
            doc = solution.resolve().parents[2] / "docs" / f"{solution.stem}.md"
        except IndexError:
            print(f"문서 경로를 유도할 수 없습니다: {solution}. --doc 으로 지정하세요.")
            return 1

    if doc.exists():
        try:
            doc_lines, newline = read_text(doc)
        except OSError as e:
            print(f"문서를 열 수 없습니다: {doc} ({e.strerror})")
            return 1
        try:
            merged, mismatches = merge_document(
                doc_lines, date, args.fence, code, meta, stamp
            )
        except ValueError as e:
            print(f"{doc}: {e}")
            return 1
        note = "섹션 추가"
    else:
        merged = build_document(date, args.fence, code, meta, stamp)
        mismatches, newline = [], "\n"
        note = "새 문서"
        doc.parent.mkdir(parents=True, exist_ok=True)

    doc.write_text(newline.join(merged) + newline, encoding="utf-8")

    print(doc)
    print(f"+ ## {date} ({note})")
    for mismatch in mismatches:
        print(f"! {mismatch}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
