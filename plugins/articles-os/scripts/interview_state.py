#!/usr/bin/env python3
"""진행 중인 회상 인터뷰 파일의 소유자 (stdlib only).

인터뷰 파일은 `interview` 스킬과 `note` 스킬 사이의 유일한 통로다.
메모 조립에 필요한 모든 것이 이 파일에 있어야 한다.
대화 컨텍스트에만 남는 것은 `note` 스킬에게 존재하지 않는다.

Usage:
    python3 interview_state.py start --url U --title T --source S   # stdin: 덤프 원문
    python3 interview_state.py turn --url U                         # stdin: 턴 JSON (아래)
    python3 interview_state.py reopen --url U --axis concept,judgment
    python3 interview_state.py summary --url U                      # stdin: 요지 텍스트 (300자 이내)
    python3 interview_state.py get --url U
    python3 interview_state.py list
    python3 interview_state.py delete --url U

경로는 인자로 받지 않는다. `paths.interviews_root()`에서 스스로 찾는다.
파일명은 아티클 제목 슬러그(`paths.slugify`)이며, 다른 url이 같은 슬러그를 쓰면 `-2`, `-3`을 붙인다.

`turn`의 stdin JSON:
    {"closed": {"<축>": ["그 축을 닫은 사용자 발화", ...], ...},
     "corrections": [{"misunderstood": "처음에 알던 것", "actual": "실제"}, ...]}
    두 키 모두 선택. `closed`에 이미 닫힌 축을 다시 넣으면 발화만 덧붙는다.

`start`/`turn`/`summary`/`get`의 성공 출력은 모두 같은 진행 상태다:
    {"ok": true, "url", "title", "source", "turns", "limit", "limit_reached",
     "closed": [...], "remaining": [...], "all_closed": bool, "resumed": bool}
`get`은 여기에 `exists: true`와 조립 재료(`dump`, `axes`, `corrections`, `summary`)를 더한다.
진행 중인 인터뷰가 없으면 오류가 아니라 {"ok": true, "exists": false, "url": ...}를 낸다.
`list`는 {"ok": true, "interviews": [{"url","title","source","turns","remaining","updated_at"}, ...]}.

exit code는 성공 0 / 실패 1. 실패 출력은 {"ok": false, "error": "..."}.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import NoReturn

import paths

# 축은 "노트에 있어야 할 것"의 목록이다. 질문 템플릿이 아니다.
AXES = {
    "concept": "핵심 개념",
    "judgment": "판단·이견",
    "apply": "적용",
    "unresolved": "미해결",
}

# 사용자에게 계속할지 물어보는 지점. 종료 기준이 아니라 안전장치다.
TURN_LIMIT = 6

# 요지 상한(자). 넘으면 메모에서 요지가 본문보다 길어져 사용자 발화가 주인이라는 구조가 흔들린다.
SUMMARY_MAX_CHARS = 300


def fail(msg) -> NoReturn:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def interview_files():
    root = paths.interviews_root()
    if not os.path.isdir(root):
        return []
    return sorted(
        os.path.join(root, f) for f in os.listdir(root) if f.endswith(".json")
    )


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_by_url(url):
    """url이 일치하는 인터뷰 파일 경로. 없으면 None. 파일명은 제목 슬러그라 url로 역산할 수 없으므로 훑는다."""
    for path in interview_files():
        try:
            if load(path).get("url") == url:
                return path
        except ValueError:
            continue  # 손상된 파일이 다른 인터뷰의 조회를 막지 않는다
    return None


def new_path(title, url):
    """제목 슬러그로 파일 경로를 정한다. 다른 url이 이미 그 슬러그를 쓰면 접미사를 붙인다."""
    root = paths.interviews_root()
    base = paths.slugify(title)
    candidate = os.path.join(root, f"{base}.json")
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(root, f"{base}-{n}.json")
        n += 1
    return candidate


def progress(doc, resumed=False):
    closed = [k for k in AXES if doc["axes"][k]["closed"]]
    remaining = [k for k in AXES if not doc["axes"][k]["closed"]]
    return {
        "ok": True,
        "url": doc["url"],
        "title": doc["title"],
        "source": doc["source"],
        "turns": doc["turns"],
        "limit": TURN_LIMIT,
        "limit_reached": doc["turns"] >= TURN_LIMIT,
        "closed": [AXES[k] for k in closed],
        "remaining": [AXES[k] for k in remaining],
        "all_closed": not remaining,
        "resumed": resumed,
    }


def emit(payload):
    print(json.dumps(payload, ensure_ascii=False))


def save(path, doc):
    doc["updated_at"] = now()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")


def cmd_start(args, stdin):
    existing = find_by_url(args.url)
    if existing:
        # 같은 아티클로 다시 부르면 이어서 진행한다. 덤프를 덮어쓰지 않는다.
        emit(progress(load(existing), resumed=True))
        return

    if not stdin.strip():
        fail("stdin dump is empty")

    doc = {
        "url": args.url,
        "title": args.title,
        "source": args.source,
        "created_at": now(),
        "updated_at": now(),
        "turns": 0,
        "dump": stdin.strip(),
        "axes": {k: {"closed": False, "evidence": []} for k in AXES},
        "corrections": [],
        "summary": "",
    }
    save(new_path(args.title, args.url), doc)
    emit(progress(doc))


def cmd_turn(args, stdin):
    path = require_path(args.url)
    doc = load(path)

    try:
        payload = json.loads(stdin) if stdin.strip() else {}
    except ValueError as e:
        fail(f"stdin is not valid JSON: {e}")
    if not isinstance(payload, dict):
        fail("stdin JSON must be an object")

    closed = payload.get("closed") or {}
    if not isinstance(closed, dict):
        fail("`closed` must be an object of {axis: [evidence, ...]}")
    for axis, evidence in closed.items():
        if axis not in AXES:
            fail(f"unknown axis: {axis} (expected one of {', '.join(AXES)})")
        if isinstance(evidence, str):
            evidence = [evidence]
        if not isinstance(evidence, list) or not [e for e in evidence if str(e).strip()]:
            fail(f"axis `{axis}` needs at least one non-empty evidence utterance")
        doc["axes"][axis]["closed"] = True
        doc["axes"][axis]["evidence"].extend(str(e).strip() for e in evidence if str(e).strip())

    corrections = payload.get("corrections") or []
    if not isinstance(corrections, list):
        fail("`corrections` must be a list")
    for item in corrections:
        if not isinstance(item, dict) or not str(item.get("misunderstood", "")).strip() \
                or not str(item.get("actual", "")).strip():
            fail("each correction needs non-empty `misunderstood` and `actual`")
        doc["corrections"].append(
            {"misunderstood": str(item["misunderstood"]).strip(),
             "actual": str(item["actual"]).strip()}
        )

    doc["turns"] += 1
    save(path, doc)
    emit(progress(doc))


def cmd_reopen(args, _stdin):
    path = require_path(args.url)
    doc = load(path)

    axes = [a.strip() for a in (args.axis or "").split(",") if a.strip()]
    if not axes:
        fail("reopen requires --axis (comma-separated)")
    for axis in axes:
        if axis not in AXES:
            fail(f"unknown axis: {axis} (expected one of {', '.join(AXES)})")
        doc["axes"][axis]["closed"] = False

    save(path, doc)
    emit(progress(doc))


def cmd_summary(args, stdin):
    path = require_path(args.url)
    summary = stdin.strip()
    if not summary:
        fail("stdin summary is empty")
    if len(summary) > SUMMARY_MAX_CHARS:
        fail(f"summary is {len(summary)} chars, max {SUMMARY_MAX_CHARS} (2~3 sentences)")
    doc = load(path)
    doc["summary"] = summary
    save(path, doc)
    emit(progress(doc))


def cmd_get(args, _stdin):
    path = find_by_url(args.url)
    if path is None:
        emit({"ok": True, "exists": False, "url": args.url})
        return

    doc = load(path)
    result = progress(doc)
    result.update({
        "exists": True,
        "dump": doc["dump"],
        "axes": {AXES[k]: v for k, v in doc["axes"].items()},
        "corrections": doc["corrections"],
        "summary": doc["summary"],
    })
    emit(result)


def cmd_list(_args, _stdin):
    interviews = []
    for path in interview_files():
        try:
            doc = load(path)
            interviews.append({
                "url": doc["url"],
                "title": doc["title"],
                "source": doc["source"],
                "turns": doc["turns"],
                "remaining": [AXES[k] for k in AXES if not doc["axes"][k]["closed"]],
                "updated_at": doc.get("updated_at", ""),
            })
        except (ValueError, KeyError):
            continue  # 손상된 파일은 목록에서 빼고 나머지를 보여준다
    interviews.sort(key=lambda i: i["updated_at"], reverse=True)
    emit({"ok": True, "interviews": interviews})


def cmd_delete(args, _stdin):
    path = require_path(args.url)
    os.remove(path)
    emit({"ok": True, "deleted": os.path.basename(path)})


def require_path(url):
    path = find_by_url(url)
    if path is None:
        fail(f"interview not found for url: {url}")
    return path


COMMANDS = {
    "start": cmd_start,
    "turn": cmd_turn,
    "reopen": cmd_reopen,
    "summary": cmd_summary,
    "get": cmd_get,
    "list": cmd_list,
    "delete": cmd_delete,
}

NEEDS_URL = ("start", "turn", "reopen", "summary", "get", "delete")
READS_STDIN = ("start", "turn", "summary")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("--url")
    parser.add_argument("--title")
    parser.add_argument("--source")
    parser.add_argument("--axis")
    args = parser.parse_args()

    paths.require_initialized("interview_state.py")

    if args.command in NEEDS_URL and not args.url:
        fail(f"{args.command} requires --url")
    if args.command == "start" and not (args.title and args.source):
        fail("start requires --title and --source")

    stdin = sys.stdin.read() if args.command in READS_STDIN and not sys.stdin.isatty() else ""

    try:
        COMMANDS[args.command](args, stdin)
    except OSError as e:
        fail(f"{type(e).__name__}: {e}")
    except ValueError as e:
        # 인터뷰 파일이 깨진 JSON (JSONDecodeError는 ValueError 하위)
        fail(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
