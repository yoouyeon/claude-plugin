#!/usr/bin/env python3
"""articles.json 시간 기반 필터·정렬 (stdlib only).

Usage:
    python3 filter_articles.py <data-path> --mode latest_batch|recent_days|all [--days N]

모드:
    latest_batch — collected_at이 가장 최근인 배치(같은 실행에서 수집된 것 전체)만.
    recent_days  — collected_at이 (now - N일) 이후인 것만. N 기본값 7.
    all          — 전체.

recent_days 결과가 0건이면 필터를 무시하고 전체에서 published_at 최신 10건을 대신 반환한다
(widened: true로 표시).

정렬은 항상 published_at 내림차순(없으면 맨 뒤, collected_at으로 2차 정렬).

stdout (JSON):
    {"mode_used": "...", "days": N|null, "widened": bool, "count": N,
     "articles": [{"url","title","source","published_at","summary"}, ...]}
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone


def load_articles(data_path):
    path = os.path.join(os.path.expanduser(data_path), "articles.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("articles", [])


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def sort_key(article):
    ts = parse_ts(article.get("published_at"))
    # published_at 없으면 맨 뒤로 (아주 오래된 값 취급)
    return ts or datetime.min.replace(tzinfo=timezone.utc)


def to_view(article):
    return {
        "url": article.get("url"),
        "title": article.get("title"),
        "source": article.get("source"),
        "published_at": article.get("published_at"),
        "summary": article.get("summary"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_path")
    parser.add_argument("--mode", choices=["latest_batch", "recent_days", "all"], default="recent_days")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    articles = load_articles(args.data_path)
    mode_used = args.mode
    widened = False

    if args.mode == "latest_batch":
        collected_ts = [parse_ts(a.get("collected_at")) for a in articles]
        collected_ts = [t for t in collected_ts if t is not None]
        if collected_ts:
            latest = max(collected_ts)
            selected = [a for a in articles if parse_ts(a.get("collected_at")) == latest]
        else:
            selected = []
    elif args.mode == "recent_days":
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
        selected = [a for a in articles if (parse_ts(a.get("collected_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
        if not selected:
            widened = True
            mode_used = "all"
            selected = articles
    else:
        selected = articles

    selected = sorted(selected, key=sort_key, reverse=True)

    if widened:
        selected = selected[:10]

    print(json.dumps(
        {
            "mode_used": mode_used,
            "days": args.days if args.mode == "recent_days" else None,
            "widened": widened,
            "count": len(selected),
            "articles": [to_view(a) for a in selected],
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
