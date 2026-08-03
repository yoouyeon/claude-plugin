#!/usr/bin/env python3
"""소스 헬스체크 집계·분류 (stdlib only, 네트워크 재확인 없음).

Usage:
    python3 source_healthcheck.py

고정 경로(`paths.data_root()`)의 config.yaml(sources 섹션), articles.json, state.json 을 읽어 소스별로 최신 published_at·수집 건수·연속 실패 상태를 집계하고 고정 기준으로 분류한 뒤 JSON으로 출력한다.

판정 우선순위: dead > quiet > uncollected > normal.

stdout (JSON):
    {"sources": [
        {"name": "...", "url": "...", "latest_published_at": "ISO8601 | null",
         "article_count": N, "consecutive_failures": N, "last_success_at": "ISO8601 | null",
         "alerted": bool, "status": "dead" | "quiet" | "uncollected" | "normal"}
    ]}

분류 기준:
    dead: consecutive_failures >= FAILURE_THRESHOLD (apply_collection_results와 공유)
    quiet: consecutive_failures == 0 이고 latest_published_at 이 QUIET_THRESHOLD_DAYS 이상 전 (fetch는 성공하지만 오래 무발행이라 연속 실패 알림의 사각지대)
    uncollected: 등록됐지만 article_count == 0
    normal: 나머지
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import NoReturn

import manage_config
import paths
from apply_collection_results import FAILURE_THRESHOLD

QUIET_THRESHOLD_DAYS = 60


def die(msg) -> NoReturn:
    print(f"source_healthcheck.py error: {msg}", file=sys.stderr)
    sys.exit(1)


def read_sources():
    """config.yaml의 sources. 파싱은 manage_config에 위임한다(파서 중복 방지)."""
    conf = paths.config_path()
    if not os.path.exists(conf):
        die(f"config.yaml not found: {conf}")
    try:
        return manage_config.load_config(conf)["sources"]
    except OSError as e:
        die(f"cannot read config.yaml: {type(e).__name__}: {e}")


def read_json(path, default):
    """없으면 default. 손상됐으면 die. 조용히 default로 넘어가면 진단 결과가 거짓이 된다."""
    if not os.path.exists(path):
        return default
    name = os.path.basename(path)
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError) as e:
        die(f"cannot read {name}: {type(e).__name__}: {e}")
    if not isinstance(doc, dict):
        die(f"{name} must be a JSON object")
    return doc


def parse_iso(ts):
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (AttributeError, TypeError, ValueError):
        return None


def main():
    if len(sys.argv) != 1:
        die("usage: source_healthcheck.py")
    paths.require_initialized("source_healthcheck.py")
    data_path = paths.data_root()

    sources = read_sources()
    articles = read_json(os.path.join(data_path, "articles.json"), {}).get("articles", [])
    state = read_json(os.path.join(data_path, "state.json"), {}).get("sources", {})
    if not isinstance(articles, list):
        die("articles.json: 'articles' must be an array")
    if not isinstance(state, dict):
        die("state.json: 'sources' must be an object")

    # articles.json의 "source"는 config.yaml의 sources[].name과 대응한다
    latest_by_name = {}
    count_by_name = {}
    for a in articles:
        if not isinstance(a, dict):
            continue
        name = a.get("source")
        if not isinstance(name, str):  # 집계 키로 쓰므로 문자열만
            continue
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
        if not isinstance(st, dict):
            st = {}
        consecutive_failures = st.get("consecutive_failures")
        consecutive_failures = consecutive_failures if isinstance(consecutive_failures, int) else 0
        last_success_at = st.get("last_success_at")
        alerted = bool(st.get("alerted"))
        article_count = count_by_name.get(name, 0)
        latest_dt = latest_by_name.get(name)
        latest_published_at = latest_dt.isoformat().replace("+00:00", "Z") if latest_dt else None

        if consecutive_failures >= FAILURE_THRESHOLD:
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
