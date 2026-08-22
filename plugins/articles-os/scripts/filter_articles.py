#!/usr/bin/env python3
"""articles.json 시간 기반 필터·정렬 (stdlib only).

Usage:
    python3 filter_articles.py --mode latest_batch|recent_days|all [--days N]

모드:
    latest_batch: collected_at이 가장 최근인 배치(같은 실행에서 수집된 것 전체)만.
    recent_days: collected_at이 (now - N일) 이후인 것만. N 기본값 7.
    all: 전체.

recent_days 결과가 0건이면 필터를 무시하고 전체에서 published_at 최신 10건을 대신 반환한다 (widened: true로 표시).
전체가 0건이면 확장하지 않는다 (widened: false, count: 0).

정렬은 항상 published_at 내림차순(없으면 맨 뒤, collected_at으로 2차 정렬).

진행 중인 인터뷰가 있는 아티클은 `interview`에 {"turns", "remaining"}이 실린다. 없으면 null.

stdout (JSON):
    {"mode_used": "...", "days": N|null, "widened": bool, "count": N,
     "articles": [{"url","title","source","published_at","summary","interview"}, ...]}
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import NoReturn

import interview_state
import paths


def fail(msg) -> NoReturn:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def load_articles():
    """없으면 빈 목록. 손상됐으면 die. 빈 결과를 내면 "수집된 게 없다"로 오해된다."""
    path = os.path.join(paths.data_root(), "articles.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, dict):
        fail("articles.json must be a JSON object")
    articles = doc.get("articles", [])
    if not isinstance(articles, list):
        fail("articles.json: 'articles' must be an array")
    return [a for a in articles if isinstance(a, dict)]


def parse_ts(value):
    """타임존이 없으면 UTC로 본다. aware/naive가 섞이면 비교가 TypeError를 낸다."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def sort_key(article):
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    return (
        parse_ts(article.get("published_at")) or oldest,
        parse_ts(article.get("collected_at")) or oldest,
    )


def interview_index():
    """url -> {turns, remaining}. 손상된 인터뷰 파일은 건너뛴다."""
    index = {}
    for path in interview_state.interview_files():
        try:
            doc = interview_state.load(path)
            url = doc["url"]
            axes = doc["axes"]
        except (OSError, ValueError, KeyError):
            continue
        index[url] = {
            "turns": interview_state.turn_count(doc),
            "remaining": [label for key, label in interview_state.AXES.items()
                          if not axes.get(key, {}).get("closed")],
        }
    return index


def to_view(article, interviews):
    return {
        "url": article.get("url"),
        "title": article.get("title"),
        "source": article.get("source"),
        "published_at": article.get("published_at"),
        "summary": article.get("summary"),
        "interview": interviews.get(article.get("url")),
    }


def run(args):
    articles = load_articles()
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
        # 넓힐 대상이 있을 때만 확장으로 표시한다. 전체가 0건이면 확장해도 보여줄 것이 없다.
        if not selected and articles:
            widened = True
            mode_used = "all"
            selected = articles
    else:
        selected = articles

    selected = sorted(selected, key=sort_key, reverse=True)
    interviews = interview_index()

    if widened:
        selected = selected[:10]

    print(json.dumps(
        {
            "mode_used": mode_used,
            "days": args.days if args.mode == "recent_days" else None,
            "widened": widened,
            "count": len(selected),
            "articles": [to_view(a, interviews) for a in selected],
        },
        ensure_ascii=False,
    ))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["latest_batch", "recent_days", "all"], default="recent_days")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    paths.require_initialized("filter_articles.py")
    if args.days < 1:
        fail("--days must be 1 or greater")
    try:
        run(args)
    except (OSError, ValueError) as e:
        fail(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
