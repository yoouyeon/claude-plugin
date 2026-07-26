#!/usr/bin/env python3
"""fetch-source 에이전트들의 결과를 병합해 state.json·articles.json에 반영 (stdlib only).

Usage:
    python3 apply_collection_results.py <data-path> <run_ts>
    (stdin: fetch-source 에이전트 결과 배열 JSON)

stdin (JSON 배열, fetch_feed.py 출력 형식과 동일 — source_name/source_url 포함):
    [
      {"ok": true,  "source_name": "...", "source_url": "...", "entries": [
          {"title": "...", "url": "...", "summary": "...", "published_at": "ISO8601 UTC | null"}]},
      {"ok": false, "source_name": "...", "source_url": "...", "error": "..."}
    ]

동작:
    1. state.json 소스별 상태 갱신 — 성공: consecutive_failures=0/last_success_at=<run_ts>/alerted=false,
       실패: consecutive_failures += 1. 이번 실행에서 처음 3에 도달(직전 2→3)하고 alerted==false인
       소스만 실패 경고 대상으로 기록 후 alerted=true로 갱신.
    2. 성공한 소스의 entries만 대상으로 신규 판정:
       - published_at이 없으면 항상 신규 취급.
       - state.json.last_run이 없으면(최초 실행) published_at의 로컬 날짜가 오늘인 것만.
       - 있으면 published_at > last_run인 것만.
       - articles.json 기존 url + 이번 배치 내부 중복은 제외 (url 기준).
    3. 신규 아티클을 articles.json에 append (collected_at=<run_ts>).
    4. 소스가 하나라도 성공했으면 state.json.last_run을 <run_ts>로 갱신 (전부 실패면 유지).
    5. state.json, articles.json 저장.

stdout (JSON):
    {"new_articles": [{"title","source","summary","url"}, ...], "new_count": N,
     "failure_warnings": [{"name","url"}, ...], "success_sources": N, "fail_sources": N}
    실패 시: {"ok": false, "error": "..."}  (exit code 1)
"""
import json
import os
import sys
from datetime import datetime, timezone


def die(msg):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def parse_iso(s):
    if not s:
        return None
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def is_new_by_date(published_at, last_run_dt, today_local_date):
    """published_at 하나가 신규 후보인지 날짜만으로 판정 (dedup은 별도)."""
    if not published_at:
        return True  # published_at 없으면 항상 신규 취급
    pub_dt = parse_iso(published_at)
    if pub_dt is None:
        return True  # 파싱 불가 시에도 유실보다 포함이 안전
    if last_run_dt is None:
        return pub_dt.astimezone().date() == today_local_date
    return pub_dt > last_run_dt


def main():
    if len(sys.argv) != 3:
        die("usage: apply_collection_results.py <data-path> <run_ts>")
    data_path = os.path.expanduser(sys.argv[1])
    run_ts = sys.argv[2]

    try:
        results = json.load(sys.stdin)
    except Exception as e:
        die(f"invalid stdin JSON: {e}")
    if not isinstance(results, list):
        die("stdin must be a JSON array of fetch results")

    articles_path = os.path.join(data_path, "data", "articles.json")
    state_path = os.path.join(data_path, "data", "state.json")

    articles_doc = load_json(articles_path, {"articles": []})
    state_doc = load_json(state_path, {"last_run": None, "sources": {}})
    articles = articles_doc.setdefault("articles", [])
    sources_state = state_doc.setdefault("sources", {})

    seen_urls = {a["url"] for a in articles if "url" in a}
    last_run_dt = parse_iso(state_doc.get("last_run"))
    today_local_date = datetime.now().astimezone().date()

    new_articles = []
    failure_warnings = []
    success_count = 0
    fail_count = 0

    for result in results:
        source_url = result.get("source_url")
        source_name = result.get("source_name") or source_url
        entry = sources_state.setdefault(
            source_url, {"consecutive_failures": 0, "last_success_at": None, "alerted": False}
        )

        if result.get("ok"):
            success_count += 1
            entry["consecutive_failures"] = 0
            entry["last_success_at"] = run_ts
            entry["alerted"] = False

            for item in result.get("entries", []):
                url = item.get("url")
                if not url or url in seen_urls:
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
            before = entry["consecutive_failures"]
            entry["consecutive_failures"] = before + 1
            if entry["consecutive_failures"] == 3 and before == 2 and not entry["alerted"]:
                failure_warnings.append({"name": source_name, "url": source_url})
                entry["alerted"] = True

    articles.extend(new_articles)
    if success_count > 0:
        state_doc["last_run"] = run_ts

    save_json(articles_path, articles_doc)
    save_json(state_path, state_doc)

    print(json.dumps({
        "new_articles": [
            {"title": a["title"], "source": a["source"], "summary": a["summary"], "url": a["url"]}
            for a in new_articles
        ],
        "new_count": len(new_articles),
        "failure_warnings": failure_warnings,
        "success_sources": success_count,
        "fail_sources": fail_count,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
