#!/usr/bin/env python3
"""~/.articles-os/secrets.json 관리: 존재 확인(has) / 저장(save) (stdlib only).

Usage:
    python3 save_secret.py has <install_id>
    python3 save_secret.py save <install_id> --url <webhook-url>

동작:
    has  — secrets.json에 <install_id> 키의 slack_webhook_url이 있는지만 확인한다
           (값 자체는 출력하지 않는다).
    save — URL이 https://hooks.slack.com/ 로 시작하는지 검증한 뒤, 기존 파일이 있으면
           다른 install_id의 키를 보존하며 병합해 저장하고 chmod 600을 적용한다.

stdout (JSON):
    has:  {"exists": true | false}
    save: 성공 {"ok": true}
          실패 {"ok": false, "error": "..."}  (exit code 1)
"""
import argparse
import json
import os
import stat
import sys

SECRETS = os.path.expanduser("~/.articles-os/secrets.json")
WEBHOOK_PREFIX = "https://hooks.slack.com/"


def load_secrets():
    if not os.path.exists(SECRETS):
        return {}
    with open(SECRETS, encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}


def fail(msg):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["has", "save"])
    parser.add_argument("install_id")
    parser.add_argument("--url")
    args = parser.parse_args()

    secrets = load_secrets()

    if args.action == "has":
        exists = bool(secrets.get(args.install_id, {}).get("slack_webhook_url"))
        print(json.dumps({"exists": exists}, ensure_ascii=False))
        return

    # save
    if not args.url:
        fail("save requires --url")
    if not args.url.startswith(WEBHOOK_PREFIX):
        fail(f"invalid webhook url (must start with {WEBHOOK_PREFIX})")

    secrets[args.install_id] = {"slack_webhook_url": args.url}
    os.makedirs(os.path.dirname(SECRETS), exist_ok=True)
    with open(SECRETS, "w", encoding="utf-8") as f:
        json.dump(secrets, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.chmod(SECRETS, stat.S_IRUSR | stat.S_IWUSR)  # 600

    print(json.dumps({"ok": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
