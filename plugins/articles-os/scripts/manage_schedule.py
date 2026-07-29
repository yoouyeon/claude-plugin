#!/usr/bin/env python3
"""macOS launchd에 헤드리스 수집 명령 등록/조회/제거 (stdlib only, macOS 전용).

Usage:
    python3 manage_schedule.py status
    python3 manage_schedule.py register --claude-bin <path> --hour <HH> --minute <MM>
    python3 manage_schedule.py remove

동작:
    `~/Library/LaunchAgents/com.articles-os.plist`에 등록한다. 등록되는 커맨드는 항상 고정이다: `<claude-bin> -p '/articles-os:collect' --allowedTools 'Bash,Task'`.

    작업 디렉토리는 지정하지 않는다 — plist의 `WorkingDirectory` 키도 쓰지 않는다.
    PATH는 `EnvironmentVariables/PATH`로 명시해 흔한 설치 경로(`/usr/local/bin`, `/opt/homebrew/bin`, `~/.local/bin`)를 항상 포함시킨다.

    register는 멱등적이다 — 다시 실행해도 중복 등록이 생기지 않는다.
    `--claude-bin`은 실행 가능한 파일이어야 하며, 절대경로로 확정해 기록한다.

    예약 실행은 user scope 설치를 전제로 한다: project/local scope로 설치하면 스케줄러가 `/articles-os:collect` 커맨드를 찾지 못한다.

stdout (JSON):
    status:   {"os": "macos", "registered": true|false, "hour": .., "minute": ..,
               "claude_cli": {"available": true|false, "path": ".."|null}}
              plist를 읽을 수 없으면 registered=false에 "error"가 함께 붙는다.
              {"os": "<기타>", "registered": false, "error": "unsupported os"}
    register: 성공 {"ok": true, "os": "macos", "hour": .., "minute": ..}
              실패 {"ok": false, "error": "..."}                       (exit code 1)
    remove:   {"ok": true, "removed": true|false}
"""
import argparse
import json
import os
import platform
import plistlib
import shlex
import shutil
import subprocess
import sys
from typing import NoReturn

LABEL = "com.articles-os"
COLLECT_ARGS = ["-p", "/articles-os:collect", "--allowedTools", "Bash,Task"]
FALLBACK_PATH_DIRS = ["/usr/local/bin", "/usr/bin", "/bin", "/opt/homebrew/bin"]


def plist_path():
    return os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")


def log_path():
    return os.path.expanduser("~/Library/Logs/articles-os.log")


def fail(msg) -> NoReturn:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def detect_os():
    system = platform.system()
    return "macos" if system == "Darwin" else system.lower()


def fallback_path():
    home_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
    return ":".join(FALLBACK_PATH_DIRS + [home_bin])


def build_collect_command(claude_bin):
    args = [claude_bin] + COLLECT_ARGS
    return " ".join(shlex.quote(a) for a in args)


def check_claude_cli():
    path = shutil.which("claude")
    return {"available": path is not None, "path": path}


# ---- macOS (launchd) ----

def macos_status():
    path = plist_path()
    if not os.path.exists(path):
        return {"os": "macos", "registered": False}
    with open(path, "rb") as f:
        plist = plistlib.load(f)
    interval = plist.get("StartCalendarInterval", {})
    return {
        "os": "macos",
        "registered": True,
        "hour": interval.get("Hour"),
        "minute": interval.get("Minute"),
    }


def macos_register(claude_bin, hour, minute):
    path = plist_path()
    if os.path.exists(path):
        subprocess.run(["launchctl", "unload", path], capture_output=True, text=True, check=False)

    plist = {
        "Label": LABEL,
        "ProgramArguments": ["/bin/bash", "-c", build_collect_command(claude_bin)],
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": log_path(),
        "StandardErrorPath": log_path(),
        "EnvironmentVariables": {"PATH": fallback_path()},
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        plistlib.dump(plist, f)

    result = subprocess.run(["launchctl", "load", path], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        fail(f"launchctl load failed: {result.stderr.strip()}")

    return {"ok": True, "os": "macos", "hour": hour, "minute": minute}


def macos_remove():
    path = plist_path()
    if not os.path.exists(path):
        return {"ok": True, "removed": False}
    subprocess.run(["launchctl", "unload", path], capture_output=True, text=True, check=False)
    os.remove(path)
    return {"ok": True, "removed": True}


# ---- dispatch ----

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("status")

    p_register = sub.add_parser("register")
    p_register.add_argument("--claude-bin", required=True)
    p_register.add_argument("--hour", type=int, required=True)
    p_register.add_argument("--minute", type=int, required=True)

    sub.add_parser("remove")

    args = parser.parse_args()
    os_name = detect_os()

    if os_name != "macos":
        if args.action == "status":
            print(json.dumps({"os": os_name, "registered": False, "error": "unsupported os"}, ensure_ascii=False))
            return
        fail(f"unsupported os: {os_name}")

    if args.action == "status":
        try:
            result = macos_status()
        except (OSError, ValueError) as e:
            # plist가 깨졌거나 읽을 수 없는 경우. registered를 false로 두어 스킬이 재등록을
            # 유도하게 한다 — register는 기존 plist를 읽지 않고 덮어쓰므로 그대로 복구된다.
            result = {"os": "macos", "registered": False, "error": f"{type(e).__name__}: {e}"}
        result["claude_cli"] = check_claude_cli()
        print(json.dumps(result, ensure_ascii=False))
        return

    if args.action == "register":
        if not (0 <= args.hour <= 23):
            fail("hour must be 0-23")
        if not (0 <= args.minute <= 59):
            fail("minute must be 0-59")
        claude_bin = args.claude_bin.strip()
        if not claude_bin:
            fail("register requires --claude-bin")
        claude_bin = os.path.abspath(os.path.expanduser(claude_bin))
        if not (os.path.isfile(claude_bin) and os.access(claude_bin, os.X_OK)):
            fail(f"not an executable file: {claude_bin}")
        try:
            result = macos_register(claude_bin, args.hour, args.minute)
        except OSError as e:
            fail(f"{type(e).__name__}: {e}")
        print(json.dumps(result, ensure_ascii=False))
        return

    if args.action == "remove":
        try:
            result = macos_remove()
        except OSError as e:
            fail(f"{type(e).__name__}: {e}")
        print(json.dumps(result, ensure_ascii=False))
        return


if __name__ == "__main__":
    main()
