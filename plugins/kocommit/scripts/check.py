#!/usr/bin/env python3
"""커밋 메시지 한 개를 기계적으로 검사한다 (stdlib only).

Usage:
    python3 check.py < message.txt

검사 항목:
    type      feat, fix, docs, style, refactor, test, chore, revert 중 하나
    길이      "<type>: <description>" 전체 50자 이하
    마침표    title과 body 줄 끝에 마침표 없음
    종결어미  title과 body 줄이 "-다", "-요"로 끝나지 않음
    금지어    "및", "박아 넣다"
    빈 줄     title과 body 사이에 빈 줄 하나
    bullet    body가 2줄 이상이면 전부 bullet, 1줄이면 bullet 없음

    인라인 코드는 금지어·종결어미 검사에서 세지 않는다.

stdout:
    exit 0: 걸린 것 없음
        문제 없음
    exit 1: 걸린 것 있음. 한 줄에 하나씩
        <줄 번호>\t<항목>\t<내용>
    exit 2: 메시지가 비어 있음
"""
import re
import sys

TYPES = ("feat", "fix", "docs", "style", "refactor", "test", "chore", "revert")
TITLE_LIMIT = 50
TITLE = re.compile(r"^([a-z]+)(\([^)]*\))?!?: \S")
BULLET = re.compile(r"^\s*[-*] ")
INLINE_CODE = re.compile(r"`[^`\n]*`")
BANNED = [
    (re.compile(r"(?<![가-힣])및(?![가-힣])"), "및"),
    (re.compile(r"박아\s?넣"), "박아 넣다"),
]
YO_NOUNS = ("필요", "중요", "주요", "수요", "개요")


def ending_problem(text: str) -> str | None:
    words = re.findall(r"[가-힣]+", text)
    if not words:
        return None
    word = words[-1]
    if word.endswith("다"):
        return f"-다로 끝남: {word}"
    if word.endswith("요") and not word.endswith(YO_NOUNS):
        return f"-요로 끝남: {word}"
    return None


def check_line(no: int, line: str) -> list[str]:
    problems = []
    plain = INLINE_CODE.sub(" ", line)
    for pattern, label in BANNED:
        if pattern.search(plain):
            problems.append(f"{no}\t금지어\t{label}")
    stripped = plain.rstrip()
    if stripped.endswith("."):
        problems.append(f"{no}\t마침표\t줄 끝 마침표")
    ending = ending_problem(stripped)
    if ending:
        problems.append(f"{no}\t종결어미\t{ending}")
    return problems


def check(message: str) -> list[str]:
    lines = [line for line in message.splitlines() if not line.startswith("#")]
    while lines and not lines[-1].strip():
        lines.pop()
    title = lines[0]
    problems = []

    match = TITLE.match(title)
    if not match:
        problems.append("1\ttype\t<type>: <description> 형식이 아님")
    elif match.group(1) not in TYPES:
        problems.append(f"1\ttype\t허용되지 않는 type: {match.group(1)}")
    if len(title) > TITLE_LIMIT:
        problems.append(f"1\t길이\t{len(title)}자 (최대 {TITLE_LIMIT}자)")
    problems += check_line(1, title)

    if len(lines) == 1:
        return problems
    if lines[1].strip():
        problems.append("2\t빈 줄\ttitle 다음 줄이 비어 있지 않음")
    body = [(i + 1, line) for i, line in enumerate(lines[1:], start=1) if line.strip()]
    if len(body) >= 2:
        for no, line in body:
            if not BULLET.match(line):
                problems.append(f"{no}\tbullet\t항목이 2개 이상인데 bullet이 아님")
    elif len(body) == 1 and BULLET.match(body[0][1]):
        problems.append(f"{body[0][0]}\tbullet\t항목이 1개인데 bullet을 씀")
    for no, line in body:
        problems += check_line(no, line)
    return problems


def main() -> int:
    message = sys.stdin.read()
    if not message.strip():
        print("메시지가 비어 있음")
        return 2
    problems = check(message)
    if not problems:
        print("문제 없음")
        return 0
    print("\n".join(problems))
    return 1


if __name__ == "__main__":
    sys.exit(main())
