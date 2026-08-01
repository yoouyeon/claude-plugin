#!/usr/bin/env python3
"""fetch_feed.py의 소스별 결과를 병합해 state.json·articles.json에 반영 (stdlib only).

Usage:
    python3 apply_collection_results.py <run_ts>
    (stdin: fetch_feed.py 출력 배열 JSON)

stdin (JSON 배열, fetch_feed.py 출력):
    [
      {"ok": true,  "source_name": "...", "source_url": "...", "entries": [
          {"title": "...", "url": "...", "summary": "...", "published_at": "ISO8601 | null"}]},
      {"ok": false, "source_name": "...", "source_url": "...", "error": "..."}
    ]

동작:
    1. state.json 소스별 상태 갱신 (성공: 카운터 리셋 / 실패: +1, FAILURE_THRESHOLD 도달 시 경고 1회).
    2. 성공한 소스의 entries에서 신규만 추린다 — last_run 이후 발행분, url 기준 dedup.
       last_run이 없으면 최초 실행으로 보고 오늘 발행분만. published_at이 없거나 파싱 불가면 신규 취급.
    3. 신규를 articles.json에 append하고, 하나라도 성공했으면 last_run을 갱신한다(전부 실패면 유지).

    run_ts·결과 배열·상태 파일이 형식에 맞지 않으면 아무것도 저장하지 않고 중단한다.

stdout (JSON):
    {"new_articles": [{"title","source","url"}, ...], "new_count": N,
     "failure_warnings": [{"name","url"}, ...], "success_sources": N, "fail_sources": N}
    실패 시: {"ok": false, "error": "..."}  (exit code 1)
"""
import json
import os
import sys
from datetime import datetime, timezone
from typing import NoReturn

import paths

FAILURE_THRESHOLD = 3  # 연속 실패가 이 횟수에 도달하면 "죽은 소스" 경고 1회


def die(msg) -> NoReturn:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def load_json(path, default):
    """없으면 default, 손상됐으면 die."""
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


def save_json(path, obj):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError as e:
        die(f"cannot write {os.path.basename(path)}: {type(e).__name__}: {e}")


def parse_iso(s):
    if not s:
        return None
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (AttributeError, TypeError, ValueError):
        return None


def is_new_by_date(published_at, last_run_dt, today_local_date):
    """published_at 하나가 신규 후보인지 날짜만으로 판정 (dedup은 별도)."""
    if not published_at:
        return True
    pub_dt = parse_iso(published_at)
    if pub_dt is None:
        return True
    if last_run_dt is None:
        return pub_dt.astimezone().date() == today_local_date
    return pub_dt > last_run_dt


def main():
    if len(sys.argv) != 2:
        die("usage: apply_collection_results.py <run_ts>")
    data_path = paths.data_root()
    run_ts = sys.argv[1]
    if parse_iso(run_ts) is None:
        die(f"run_ts must be an ISO8601 timestamp: {run_ts!r}")

    try:
        results = json.load(sys.stdin)
    except (OSError, ValueError) as e:
        die(f"invalid stdin JSON: {e}")
    if not isinstance(results, list):
        die("stdin must be a JSON array of fetch results")

    articles_path = os.path.join(data_path, "articles.json")
    state_path = os.path.join(data_path, "state.json")

    articles_doc = load_json(articles_path, {"articles": []})
    state_doc = load_json(state_path, {"last_run": None, "sources": {}})
    articles = articles_doc.setdefault("articles", [])
    sources_state = state_doc.setdefault("sources", {})
    if not isinstance(articles, list):
        die("articles.json: 'articles' must be an array")
    if not isinstance(sources_state, dict):
        die("state.json: 'sources' must be an object")

    seen_urls = {a["url"] for a in articles if isinstance(a, dict) and isinstance(a.get("url"), str)}
    last_run_dt = parse_iso(state_doc.get("last_run"))
    today_local_date = datetime.now().astimezone().date()

    new_articles = []
    failure_warnings = []
    success_count = 0
    fail_count = 0

    for result in results:
        if not isinstance(result, dict):
            die("each fetch result must be a JSON object")
        source_url = result.get("source_url")  # state.json의 키
        if not isinstance(source_url, str) or not source_url.strip():
            die(f"fetch result missing source_url: {json.dumps(result, ensure_ascii=False)[:120]}")
        if not isinstance(result.get("ok"), bool):
            die(f"fetch result missing boolean 'ok' for source: {source_url}")
        raw_name = result.get("source_name")
        source_name = raw_name if isinstance(raw_name, str) and raw_name else source_url

        entry = sources_state.get(source_url)
        if not isinstance(entry, dict):
            entry = {"consecutive_failures": 0, "last_success_at": None, "alerted": False}
            sources_state[source_url] = entry

        if result["ok"]:
            success_count += 1
            entry["consecutive_failures"] = 0
            entry["last_success_at"] = run_ts
            entry["alerted"] = False

            entries = result.get("entries") or []
            if not isinstance(entries, list):
                die(f"entries must be an array for source: {source_url}")
            for item in entries:
                if not isinstance(item, dict):
                    die(f"each entry must be a JSON object for source: {source_url}")
                url = item.get("url")
                if not isinstance(url, str) or not url or url in seen_urls:
                    continue
                if not is_new_by_date(item.get("published_at"), last_run_dt, today_local_date):
                    continue
                seen_urls.add(url)
                new_articles.append({
                    "url": url,
                    "title": item.get("title", ""),
                    "source": source_name,
                    "published_at": item.get("published_at"),
                    "collected_at": run_ts,
                    "summary": item.get("summary", ""),
                    "qa_log": [],
                    "note_path": None,
                })
        else:
            fail_count += 1
            before = entry.get("consecutive_failures")
            before = before if isinstance(before, int) else 0
            entry["consecutive_failures"] = before + 1
            if before + 1 == FAILURE_THRESHOLD and not entry.get("alerted"):
                failure_warnings.append({"name": source_name, "url": source_url})
                entry["alerted"] = True

    articles.extend(new_articles)
    if success_count > 0:
        state_doc["last_run"] = run_ts

    save_json(articles_path, articles_doc)
    save_json(state_path, state_doc)

    print(json.dumps({
        "new_articles": [
            {"title": a["title"], "source": a["source"], "url": a["url"]}
            for a in new_articles
        ],
        "new_count": len(new_articles),
        "failure_warnings": failure_warnings,
        "success_sources": success_count,
        "fail_sources": fail_count,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
