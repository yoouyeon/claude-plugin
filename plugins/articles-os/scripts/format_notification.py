#!/usr/bin/env python3
"""수집 결과 요약 JSON을 평문 알림 메시지로 조립한다 (백엔드 공통).

Usage:
    echo '<apply_collection_results.py 요약 JSON>' | python3 format_notification.py

입력(stdin) JSON 필드:
    new_count (int), new_articles (list of {title, source, url}),
    failure_warnings (list of {name, url})
    `ok: false`가 있으면 수집 실패 요약으로 보고 `error`만 실어 한 줄로 낸다.

필드가 비거나 없어도 있는 것만으로 조립한다 — 알림 하나 때문에 수집 파이프라인을 세우지 않는다.

알림은 목록이 아니라 트리거다. 제목·출처와 링크만 싣고 MAX_LISTED 건까지만 나열한 뒤
나머지는 browse로 넘긴다. 백엔드별 텍스트 상한은 여기서 보지 않는다 — notify.py가 쥔다.

stdout: 조립된 메시지 텍스트 (notify.py로 그대로 파이프)
exit code: 0 성공, 1 stdin이 JSON 객체가 아님
"""
import json
import sys
from typing import NoReturn

from apply_collection_results import FAILURE_THRESHOLD

MAX_LISTED = 8


def die(msg) -> NoReturn:
    print(f"format_notification.py error: {msg}", file=sys.stderr)
    sys.exit(1)


def text(value):
    return str(value) if value not in (None, "") else ""


def build_message(data):
    # 수집 실패 요약(`ok: false`)은 신규 0건과 구분해서 낸다.
    if data.get("ok") is False:
        return f"⚠️ articles-os — 수집 실패: {text(data.get('error')) or '알 수 없는 오류'}"

    new_articles = [a for a in data.get("new_articles") or [] if isinstance(a, dict)]
    failure_warnings = [w for w in data.get("failure_warnings") or [] if isinstance(w, dict)]
    # 목록보다 적게 보고하지 않는다 — 그러면 있는 아티클이 메시지에서 사라진다.
    new_count = data.get("new_count")
    if not isinstance(new_count, int) or new_count < len(new_articles):
        new_count = len(new_articles)

    lines = []
    if new_count > 0:
        lines.append(f"📚 articles-os — 신규 아티클 {new_count}건")
        listed = new_articles[:MAX_LISTED]
        for a in listed:
            head = " — ".join(p for p in (text(a.get("title")), text(a.get("source"))) if p)
            lines.append(f"• {head}" if head else "•")
            url = text(a.get("url"))
            if url:
                lines.append(f"  {url}")
        remaining = new_count - len(listed)
        if remaining > 0:
            lines.append(f"외 {remaining}건 — /articles-os:browse 로 전체 보기")
    else:
        lines.append("📭 articles-os — 신규 아티클 없음")

    for w in failure_warnings:
        name = text(w.get("name")) or text(w.get("url")) or "(이름 없음)"
        url = text(w.get("url"))
        suffix = f" ({url})" if url else ""
        lines.append(f"⚠️ 소스 경고: {name} — 연속 {FAILURE_THRESHOLD}회 fetch 실패{suffix}")

    return "\n".join(lines)


def main():
    try:
        data = json.loads(sys.stdin.read())
    except ValueError as e:
        die(f"invalid stdin JSON: {e}")
    if not isinstance(data, dict):
        die("stdin must be a JSON object")
    print(build_message(data))


if __name__ == "__main__":
    main()
