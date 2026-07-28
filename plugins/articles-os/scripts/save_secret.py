#!/usr/bin/env python3
"""<plugin-data-dir>/secrets.json 관리: 존재 확인(has) / 저장(save) / 삭제(delete) (stdlib only).

Usage:
    python3 save_secret.py has <plugin-data-dir>
    python3 save_secret.py save <plugin-data-dir> --url <webhook-url>
    python3 save_secret.py delete <plugin-data-dir>

<plugin-data-dir>는 호출자(SKILL.md)가 `${CLAUDE_PLUGIN_DATA}` 플레이스홀더를 그대로
넘긴 값이어야 한다 — Claude Code가 스킬 콘텐츠 안의 이 플레이스홀더를 articles-os 자신의
영구 데이터 디렉토리로 정확히 치환해준다. 스크립트 내부에서 `os.environ`으로 다시 읽지
않는다 — 세션에 다른 플러그인의 hook이 `CLAUDE_PLUGIN_DATA`를 설정해두면 그 값이 hook
프로세스 스코프를 넘어 일반 Bash 호출에도 남아 있어, 엉뚱한 플러그인의 디렉토리를
가리킬 수 있음을 실측으로 확인했다(다른 플러그인의 secrets.json을 덮어쓰는 사고 발생).

동작:
    has    — secrets.json에 slack_webhook_url이 있는지만 확인한다(값 자체는 출력하지 않는다).
    save   — URL이 https://hooks.slack.com/ 로 시작하는지 검증한 뒤 저장하고 chmod 600을
             적용한다.
    delete — slack_webhook_url 키만 제거한다(파일 자체·다른 키는 유지).

stdout (JSON):
    has:    {"exists": true | false}
    save:   성공 {"ok": true}
            실패 {"ok": false, "error": "..."}  (exit code 1)
    delete: {"ok": true}
"""
import argparse
import json
import os
import stat
import sys

WEBHOOK_PREFIX = "https://hooks.slack.com/"


def fail(msg):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def load_secrets(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["has", "save", "delete"])
    parser.add_argument("plugin_data_dir")
    parser.add_argument("--url")
    args = parser.parse_args()

    path = os.path.join(args.plugin_data_dir, "secrets.json")
    secrets = load_secrets(path)

    if args.action == "has":
        print(json.dumps({"exists": bool(secrets.get("slack_webhook_url"))}, ensure_ascii=False))
        return

    if args.action == "delete":
        if secrets.pop("slack_webhook_url", None) is not None:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(secrets, f, indent=2, ensure_ascii=False)
                f.write("\n")
        print(json.dumps({"ok": True}, ensure_ascii=False))
        return

    # save
    if not args.url:
        fail("save requires --url")
    if not args.url.startswith(WEBHOOK_PREFIX):
        fail(f"invalid webhook url (must start with {WEBHOOK_PREFIX})")

    secrets["slack_webhook_url"] = args.url
    os.makedirs(args.plugin_data_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(secrets, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 600

    print(json.dumps({"ok": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
