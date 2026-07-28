#!/usr/bin/env python3
"""OS 네이티브 스케줄러(macOS: launchd, Linux: cron)에 헤드리스 수집 명령 등록/조회/제거
(stdlib only).

Usage:
    python3 manage_schedule.py status
    python3 manage_schedule.py register --claude-bin <path> --hour <HH> --minute <MM>
    python3 manage_schedule.py remove

동작:
    OS는 platform.system()으로 판별한다(Darwin → launchd, Linux → cron). 등록될 커맨드는
    항상 고정: `<claude-bin> -p '/articles-os:collect' --allowedTools 'Bash,Task'`.

    register는 멱등적이다 — 기존 등록이 있으면 (macOS는 launchctl unload 후 plist 덮어쓰기
    후 load, Linux는 `# articles-os` 식별 주석이 붙은 기존 crontab 줄을 제거한 뒤 새 줄을
    추가) 중복 등록을 만들지 않는다.

    macOS plist는 plistlib로 읽고 쓴다 — 경로에 특수문자가 섞여도 XML 이스케이프 문제가
    생기지 않는다.

stdout (JSON):
    status:   {"os": "macos"|"linux", "registered": true|false, "hour": .., "minute": ..}
              {"os": "windows"|.., "registered": false, "error": "unsupported os"}
    register: 성공 {"ok": true, "os": "...", "hour": .., "minute": ..}
              실패 {"ok": false, "error": "..."}                       (exit code 1)
    remove:   {"ok": true, "removed": true|false}
"""
import argparse
import json
import os
import platform
import plistlib
import subprocess
import sys

LABEL = "com.articles-os"
CRON_MARK = "# articles-os"
COLLECT_ARGS = ["-p", "/articles-os:collect", "--allowedTools", "Bash,Task"]


def plist_path():
    return os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")


def log_path():
    return os.path.expanduser("~/Library/Logs/articles-os.log")


def fail(msg):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def detect_os():
    system = platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Linux":
        return "linux"
    return system.lower()


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
        subprocess.run(["launchctl", "unload", path], capture_output=True, text=True)

    plist = {
        "Label": LABEL,
        "ProgramArguments": [claude_bin] + COLLECT_ARGS,
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": log_path(),
        "StandardErrorPath": log_path(),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        plistlib.dump(plist, f)

    result = subprocess.run(["launchctl", "load", path], capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"launchctl load failed: {result.stderr.strip()}")

    return {"ok": True, "os": "macos", "hour": hour, "minute": minute}


def macos_remove():
    path = plist_path()
    if not os.path.exists(path):
        return {"ok": True, "removed": False}
    subprocess.run(["launchctl", "unload", path], capture_output=True, text=True)
    os.remove(path)
    return {"ok": True, "removed": True}


# ---- Linux (cron) ----

def current_crontab_lines():
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def linux_status():
    for line in current_crontab_lines():
        if CRON_MARK in line:
            parts = line.split()
            # "<MM> <HH> * * * ..." 순서 고정(register가 생성하는 형식과 동일)
            minute, hour = parts[0], parts[1]
            return {"os": "linux", "registered": True, "hour": int(hour), "minute": int(minute)}
    return {"os": "linux", "registered": False}


def linux_register(claude_bin, hour, minute):
    kept = [line for line in current_crontab_lines() if CRON_MARK not in line]
    new_line = (
        f"{minute} {hour} * * * {claude_bin} -p '/articles-os:collect' "
        f"--allowedTools 'Bash,Task' >> {os.path.expanduser('~')}/.articles-os.log 2>&1 {CRON_MARK}"
    )
    kept.append(new_line)
    result = subprocess.run(
        ["crontab", "-"], input="\n".join(kept) + "\n", capture_output=True, text=True
    )
    if result.returncode != 0:
        fail(f"crontab install failed: {result.stderr.strip()}")
    return {"ok": True, "os": "linux", "hour": hour, "minute": minute}


def linux_remove():
    kept = [line for line in current_crontab_lines() if CRON_MARK not in line]
    before = len(current_crontab_lines())
    result = subprocess.run(
        ["crontab", "-"], input="\n".join(kept) + ("\n" if kept else ""), capture_output=True, text=True
    )
    if result.returncode != 0:
        fail(f"crontab install failed: {result.stderr.strip()}")
    return {"ok": True, "removed": before != len(kept)}


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

    if os_name not in ("macos", "linux"):
        if args.action == "status":
            print(json.dumps({"os": os_name, "registered": False, "error": "unsupported os"}, ensure_ascii=False))
            return
        fail(f"unsupported os: {os_name}")

    if args.action == "status":
        result = macos_status() if os_name == "macos" else linux_status()
        print(json.dumps(result, ensure_ascii=False))
        return

    if args.action == "register":
        if not (0 <= args.hour <= 23):
            fail("hour must be 0-23")
        if not (0 <= args.minute <= 59):
            fail("minute must be 0-59")
        result = (
            macos_register(args.claude_bin, args.hour, args.minute)
            if os_name == "macos"
            else linux_register(args.claude_bin, args.hour, args.minute)
        )
        print(json.dumps(result, ensure_ascii=False))
        return

    if args.action == "remove":
        result = macos_remove() if os_name == "macos" else linux_remove()
        print(json.dumps(result, ensure_ascii=False))
        return


if __name__ == "__main__":
    main()
