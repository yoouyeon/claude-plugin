#!/usr/bin/env python3
"""소스 헬스체크 집계·분류 (stdlib only, 네트워크 재확인 없음).

Usage:
    python3 source_healthcheck.py <data-path>

<data-path>/config.yaml(sources 섹션), articles.json, state.json 을 읽어
소스별로 최신 published_at·수집 건수·연속 실패 상태를 집계하고 고정 기준으로
분류한 뒤 JSON으로 출력한다. 판정 우선순위: dead > quiet > uncollected > normal.

stdout (JSON):
    {"sources": [
        {"name": "...", "url": "...", "latest_published_at": "ISO8601 | null",
         "article_count": N, "consecutive_failures": N, "last_success_at": "ISO8601 | null",
         "alerted": bool, "status": "dead" | "quiet" | "uncollected" | "normal"}
    ]}

분류 기준:
    dead        — consecutive_failures >= 3
    quiet       — consecutive_failures == 0 이고 latest_published_at 이 60일 이상 전
                  (fetch는 성공하지만 오래 무발행 — 연속 실패 알림의 사각지대)
    uncollected — 등록됐지만 article_count == 0
    normal      — 나머지
"""
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

QUIET_THRESHOLD_DAYS = 60


def die(msg):
    print(f"source_healthcheck.py error: {msg}", file=sys.stderr)
    sys.exit(1)


def read_sources(data_path):
    """config.yaml의 sources 섹션 파싱 (PyYAML 미의존 — 고정 포맷 전제)."""
    path = os.path.join(data_path, "config.yaml")
    if not os.path.exists(path):
        die(f"config.yaml not found: {path}")
    sources = []
    current = None
    in_sources = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if re.match(r"^sources:\s*$", line):
                in_sources = True
                continue
            if re.match(r"^notify:\s*$", line):
                in_sources = False
                continue
            if not in_sources:
                continue
            m_name = re.match(r"^\s*-\s*name:\s*(.+?)\s*$", line)
            if m_name:
                if current:
                    sources.append(current)
                current = {"name": m_name.group(1).strip("\"'"), "url": None}
                continue
            m_url = re.match(r"^\s*url:\s*(.+?)\s*$", line)
            if m_url and current is not None:
                current["url"] = m_url.group(1).strip("\"'")
    if current:
        sources.append(current)
    return sources


def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return default


def parse_iso(ts):
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def main():
    if len(sys.argv) != 2:
        die("usage: source_healthcheck.py <data-path>")
    data_path = os.path.expanduser(sys.argv[1])

    sources = read_sources(data_path)
    articles = read_json(os.path.join(data_path, "articles.json"), {}).get("articles", [])
    state = read_json(os.path.join(data_path, "state.json"), {}).get("sources", {})

    # articles.json의 "source"는 config.yaml의 sources[].name과 대응한다(docs/conventions.md 스키마 참고).
    latest_by_name = {}
    count_by_name = {}
    for a in articles:
        name = a.get("source")
        count_by_name[name] = count_by_name.get(name, 0) + 1
        pub = parse_iso(a.get("published_at"))
        if pub and (name not in latest_by_name or pub > latest_by_name[name]):
            latest_by_name[name] = pub

    now = datetime.now(timezone.utc)
    result = []
    for src in sources:
        name = src["name"]
        url = src["url"]
        st = state.get(url, {})
        consecutive_failures = st.get("consecutive_failures", 0)
        last_success_at = st.get("last_success_at")
        alerted = st.get("alerted", False)
        article_count = count_by_name.get(name, 0)
        latest_dt = latest_by_name.get(name)
        latest_published_at = latest_dt.isoformat().replace("+00:00", "Z") if latest_dt else None

        if consecutive_failures >= 3:
            status = "dead"
        elif consecutive_failures == 0 and latest_dt is not None and (now - latest_dt) >= timedelta(days=QUIET_THRESHOLD_DAYS):
            status = "quiet"
        elif article_count == 0:
            status = "uncollected"
        else:
            status = "normal"

        result.append({
            "name": name,
            "url": url,
            "latest_published_at": latest_published_at,
            "article_count": article_count,
            "consecutive_failures": consecutive_failures,
            "last_success_at": last_success_at,
            "alerted": alerted,
            "status": status,
        })

    print(json.dumps({"sources": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
