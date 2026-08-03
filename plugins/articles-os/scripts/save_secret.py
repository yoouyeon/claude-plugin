#!/usr/bin/env python3
"""<plugin-data-dir>/secrets.json 관리: 저장(save) / 삭제(delete) (stdlib only).

secrets.json 형식 (flat, 항상 0600). 키 이름은 백엔드마다 다르다:
    { "slack_webhook_url": "https://hooks.slack.com/..." }
    { "discord_webhook_url": "https://discord.com/api/webhooks/..." }

Usage:
    python3 save_secret.py save <plugin-data-dir> --backend slack|discord --url <webhook-url>
    python3 save_secret.py delete <plugin-data-dir>

<plugin-data-dir>는 호출자(SKILL.md)가 `${CLAUDE_PLUGIN_DATA}` 플레이스홀더를 그대로 넘긴 값이어야 한다.
`os.environ`으로 다시 읽지 않는다. 다른 플러그인이 설정해둔 값이 남아 엉뚱한 디렉토리를 가리킬 수 있다.

동작:
    save: URL이 그 백엔드의 허용 접두사로 시작하는지 검증한 뒤 저장한다.
             알림 백엔드는 한 번에 하나뿐이므로 다른 백엔드의 웹훅 키는 함께 지운다.
    delete: 모든 백엔드의 웹훅 키를 제거한다(파일 자체·그 밖의 키는 유지).

stdout (JSON):
    save:   성공 {"ok": true}
            실패 {"ok": false, "error": "..."}  (exit code 1)
    delete: {"ok": true}
"""
import argparse
import json
import os
import stat
import sys
from typing import NoReturn

import notify_backends


def fail(msg) -> NoReturn:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def load_secrets(path):
    """없거나 읽을 수 없거나 객체가 아니면 빈 dict. 호출자에게 항상 dict를 보장한다."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_secrets(path, secrets):
    """항상 0600으로 쓴다."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(secrets, f, indent=2, ensure_ascii=False)
        f.write("\n")
    # O_CREAT 모드는 새로 만들 때만 적용되므로, 기존 파일은 여기서 좁힌다.
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def run(args):
    path = os.path.join(args.plugin_data_dir, "secrets.json")
    secrets = load_secrets(path)

    if args.action == "delete":
        removed = [secrets.pop(key, None) for key in notify_backends.SECRET_KEYS]
        if any(v is not None for v in removed):
            write_secrets(path, secrets)
        print(json.dumps({"ok": True}, ensure_ascii=False))
        return

    # save
    if not args.backend:
        fail("save requires --backend")
    spec = notify_backends.BACKENDS.get(args.backend)
    if spec is None:
        fail(f"unknown backend: {args.backend}")

    url = (args.url or "").strip()
    if not url:
        fail("save requires --url")
    if not url.startswith(spec["url_prefixes"]):
        allowed = " 또는 ".join(spec["url_prefixes"])
        fail(f"invalid webhook url (must start with {allowed})")

    for key in notify_backends.SECRET_KEYS:
        secrets.pop(key, None)
    secrets[spec["secret_key"]] = url
    os.makedirs(args.plugin_data_dir, exist_ok=True)
    write_secrets(path, secrets)
    print(json.dumps({"ok": True}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["save", "delete"])
    parser.add_argument("plugin_data_dir")
    parser.add_argument("--backend", choices=sorted(notify_backends.BACKENDS))
    parser.add_argument("--url")
    args = parser.parse_args()
    try:
        run(args)
    except OSError as e:
        fail(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
