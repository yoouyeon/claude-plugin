#!/usr/bin/env python3
"""개발 문서 한 편을 기계적으로 검사한다 (stdlib only).

Usage:
    python3 check.py <파일> --type {spec,memo,pr,issue,readme} [--polite]

검사 항목과 허용치:
    줄표      U+2014, U+2013, U+2015. 0개
    이모지    0개
    금지어    BANNED 표의 표현. 0개
    번역투    한 문단에 "을 통해", "에 대해(대한)", "에 있어(서)"가 합쳐 3회 이상
    종결어미  문서 버전과 맞지 않는 문장 끝

    코드 블록과 인라인 코드는 모든 항목에서 세지 않는다.
    종결어미 검사는 제목(#), 인용문(>), 따옴표 안의 글을 세지 않는다.

문서 버전:
    --polite 있음   합니다체. "-니다"가 아닌 "-다."와 "-요."를 찾는다.
    --polite 없음   -다체(spec, memo, readme)와 개조식(pr, issue). 둘 다 "-니다."와 "-요."를 찾는다.

stdout:
    exit 0: 걸린 것 없음
        문제 없음
    exit 1: 걸린 것 있음. 한 줄에 하나씩
        <줄 번호>\t<항목>\t<내용>
    exit 2: 인자 오류, 파일 읽기 실패
"""
import argparse
import re
import sys
from pathlib import Path

TYPES = ("spec", "memo", "pr", "issue", "readme")

BANNED = [
    (re.compile(r"박아\s?넣"), "박아 넣는다", "그대로 적는다, 그대로 쓴다"),
    (re.compile(r"고아"), "고아(가 된다)", '실제 결과를 그대로. 예: "이전 데이터를 더 이상 찾지 못한다"'),
]

CALQUE_LIMIT = 3
CALQUE = re.compile(r"[을를]\s?통해|에\s?대(?:해|한)|에\s?있어")
DASH = re.compile("[–—―]")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⭐⭕️]")
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`\n]*`")
QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”')
SENTENCE_END = re.compile(r"([가-힣]+)[.!?](?=\s|$|\)|\*)")
YO_NOUNS = ("필요", "중요", "주요", "수요", "개요")


def strip_code(lines: list[str]) -> list[str]:
    """코드 블록 줄은 빈 줄로, 인라인 코드는 공백으로 바꾼다. 줄 번호는 유지한다."""
    result = []
    in_fence = False
    for line in lines:
        if FENCE.match(line):
            in_fence = not in_fence
            result.append("")
        elif in_fence:
            result.append("")
        else:
            result.append(INLINE_CODE.sub(" ", line))
    return result


def has_bieup_final(char: str) -> bool:
    """한글 음절의 받침이 ㅂ인지 본다. 합니다·입니다·습니다는 맞고 아니다는 아니다."""
    code = ord(char) - 0xAC00
    return 0 <= code < 11172 and code % 28 == 17


def ending_problem(word: str, polite: bool) -> str | None:
    nida = len(word) >= 3 and word.endswith("니다") and has_bieup_final(word[-3])
    yo = word.endswith("요") and not word.endswith(YO_NOUNS)
    if polite:
        if word.endswith("다") and not nida:
            return "-다"
        if yo:
            return "-요"
        return None
    if nida:
        return "-니다"
    if yo:
        return "-요"
    return None


def check(lines: list[str], polite: bool) -> list[tuple[int, str, str]]:
    findings = []

    for number, line in enumerate(lines, 1):
        for match in DASH.finditer(line):
            findings.append((number, "줄표", match.group()))
        for match in EMOJI.finditer(line):
            findings.append((number, "이모지", match.group()))
        for pattern, phrase, instead in BANNED:
            if pattern.search(line):
                findings.append((number, "금지어", f"{phrase} → {instead}"))

        stripped = line.lstrip()
        if stripped.startswith(("#", ">")):
            continue
        for match in SENTENCE_END.finditer(QUOTED.sub(" ", line)):
            problem = ending_problem(match.group(1), polite)
            if problem:
                findings.append((number, "종결어미", f"{match.group(1)} ({problem})"))

    hits = []
    for number, line in enumerate(lines + [""], 1):
        if line.strip():
            hits.extend((number, match.group()) for match in CALQUE.finditer(line))
            continue
        if len(hits) >= CALQUE_LIMIT:
            words = ", ".join(word for _, word in hits)
            findings.append((hits[0][0], "번역투", f"문단에 {len(hits)}회: {words}"))
        hits = []

    return sorted(findings)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--type", required=True, choices=TYPES)
    parser.add_argument("--polite", action="store_true")
    args = parser.parse_args()

    try:
        text = Path(args.path).read_text(encoding="utf-8")
    except OSError as error:
        print(f"{args.path}을 읽을 수 없습니다: {error}", file=sys.stderr)
        return 2

    lines = strip_code(text.replace("\r\n", "\n").split("\n"))
    findings = check(lines, args.polite)
    if not findings:
        print("문제 없음")
        return 0
    for number, item, detail in findings:
        print(f"{number}\t{item}\t{detail}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
