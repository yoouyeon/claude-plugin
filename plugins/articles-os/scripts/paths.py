#!/usr/bin/env python3
"""articles-os의 경로를 결정하는 단일 지점 (stdlib only).

Usage (CLI):
    python3 paths.py            # {"data_root", "notes_root", "initialized"}
                                # 읽기 실패 시 같은 세 키 + "error"
    python3 paths.py --require-initialized
                                # 미초기화면 {"ok": false, "error": ".."} + exit 1,
                                # 초기화됐으면 위와 같은 출력

Usage (import):
    import paths
    paths.data_root()           # ~/.articles-os (고정)
    paths.notes_root()          # config.yaml에 기록된 노트 폴더 (없으면 None)
    paths.interviews_root()     # ~/.articles-os/interviews (진행 중인 인터뷰)
    paths.require_initialized() # 미초기화면 에러 JSON을 내고 exit 1 (데이터를 다루는 스크립트가 먼저 호출)
    paths.slugify(title)        # 제목 -> 파일명 슬러그 (메모와 인터뷰 파일이 같은 규칙을 쓴다)
    paths.quote_scalar(v)       # config.yaml에 쓸 값 감싸기 / parse_scalar(raw)는 그 역연산
                                # (config.yaml 소유자는 manage_config.py지만, 그쪽이 paths를
                                #  import하므로 순환을 피하려고 이 코덱은 여기 둔다)

경로가 두 종류로 나뉘는 이유:

    data_root  — 기계 상태(config.yaml / articles.json / state.json). 고정 경로.
                 매일 도는 수집(collect)은 OS 스케줄러가 임의의 작업 디렉토리에서 띄우므로,
                 이 경로가 세션 cwd나 사용자 설정에 의존하면 실행할 때마다 다른 폴더를 가리키게 되는 문제가 생겨 홈 밑에 고정한다.
                 `${CLAUDE_PLUGIN_DATA}`를 쓰지 않는 이유: 플러그인을 마지막 스코프에서 제거하면 그 디렉토리가 함께 삭제되어 수집 이력이 유실되고,
                 경로에 마켓플레이스 이름(`<plugin>-<marketplace>`)이 들어가 설치 출처가 바뀌면 이전 데이터를 더 이상 찾지 못한다.

    notes_root — 사용자 산출물(notes/*.md)을 저장하는 경로
                 사용자가 setup에서 고른 폴더이며 그 절대경로를 config.yaml의 `notes_path`에 기록한다.
                 대화형 스킬에서만 쓰이고 수집 파이프라인은 건드리지 않는다.

시크릿(secrets.json)은 여기서 다루지 않는다 — `${CLAUDE_PLUGIN_DATA}`에 그대로 둔다. (플러그인 제거 시 자격증명이 함께 지워지는 편이 낫다는 판단).
"""
import json
import os
import re
import sys

DATA_ROOT = "~/.articles-os"


def data_root():
    """기계 상태를 두는 고정 경로."""
    return os.path.realpath(os.path.expanduser(DATA_ROOT))


def config_path():
    return os.path.join(data_root(), "config.yaml")


def interviews_root():
    """진행 중인 인터뷰를 두는 경로. 메모로 승격되기 전까지의 기계 상태다."""
    return os.path.join(data_root(), "interviews")


# 슬러그 상한(바이트). 긴 제목이 그대로 파일명이 되면 셸·파인더에서 다루기 나빠진다.
# 한글은 UTF-8에서 글자당 3바이트라 40자쯤에서 걸린다. 원제목은 frontmatter·인터뷰 파일에 온전히 남는다.
SLUG_MAX_BYTES = 120


def slugify(title):
    """한글 유지, 공백 -> '-', 특수문자 제거, SLUG_MAX_BYTES로 자름."""
    s = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")

    encoded = s.encode("utf-8")
    if len(encoded) > SLUG_MAX_BYTES:
        # errors="ignore"가 잘린 멀티바이트 문자 조각을 떨어뜨린다.
        s = encoded[:SLUG_MAX_BYTES].decode("utf-8", "ignore").rstrip("-")
    return s or "untitled"


def initialized():
    """setup이 완료됐는지 — config.yaml이 파일로 존재하는지로 판단한다."""
    return os.path.isfile(config_path())


NOT_INITIALIZED = "not initialized (run /articles-os:setup)"


def require_initialized(script_name=None):
    """미초기화면 그 사실을 알리고 종료한다.

    데이터를 읽거나 쓰는 스크립트는 이것을 먼저 호출한다. 그러지 않으면 "설정이 안 됐다"와
    "설정은 됐는데 데이터가 0건이다"가 같은 출력으로 나와 호출자가 구분하지 못한다.
    """
    if initialized():
        return
    prefix = f"{script_name}: " if script_name else ""
    print(json.dumps({"ok": False, "error": prefix + NOT_INITIALIZED}, ensure_ascii=False))
    sys.exit(1)


def one_line(value):
    """개행을 공백으로 바꿔 한 줄로 만든다.

    줄 단위로 읽는 파서가 다음 줄을 값의 일부로 보지 못하므로 한 줄 스칼라에 개행이 있으면 안 된다.
    공백은 접지도 자르지도 않는다 — 연속 공백이 든 폴더 이름이 깨지기 때문이다.
    앞뒤 공백 제거가 필요한 값(URL 등)은 호출부에서 따로 한다.
    """
    return re.sub(r"[\r\n]+", " ", str(value))


def quote_scalar(value):
    """값을 한 줄짜리 YAML 작은따옴표 스칼라로 만든다.

    작은따옴표 스칼라는 이스케이프를 해석하지 않으므로 값 안의 `'`만 `''`로 중복시킨다.
    """
    return "'" + one_line(value).replace("'", "''") + "'"


def parse_scalar(raw):
    """config.yaml 한 줄의 값 부분에서 실제 값만 뽑는다 (`quote_scalar`의 역연산).

    따옴표로 감싼 값은 닫는 따옴표까지만 값으로 보고 그 뒤는 버린다.
    따옴표가 없으면 값 맨 앞이거나 공백 뒤에 오는 `#`부터를 인라인 주석으로 본다
    (경로에 그냥 포함된 `#`은 남긴다 — 예: /a/b#c/notes).
    """
    raw = raw.strip()
    quote = raw[:1]
    if quote not in ("'", '"'):
        return re.sub(r"(^|\s)#.*$", "", raw).strip()

    out = []
    i = 1
    while i < len(raw):
        if raw[i] == quote:
            if quote == "'" and raw[i + 1:i + 2] == "'":
                out.append(quote)
                i += 2
                continue
            break  # 닫는 따옴표 — 뒤에 오는 것은 주석이므로 무시
        out.append(raw[i])
        i += 1
    return "".join(out)


def notes_root():
    """config.yaml의 notes_path. 기록돼 있지 않으면 None."""
    path = config_path()
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^notes_path:\s*(.+?)\s*$", line)
            if m:
                value = parse_scalar(m.group(1))
                return os.path.realpath(os.path.expanduser(value)) if value else None
    return None


def main():
    strict = "--require-initialized" in sys.argv[1:]
    if strict:
        require_initialized()

    # 어떤 경우에도 traceback 대신 세 키를 갖춘 JSON을 낸다. 읽기 실패는 `error` 키로 덧붙인다.
    result = {"data_root": data_root(), "notes_root": None, "initialized": False}
    try:
        result["initialized"] = initialized()
        result["notes_root"] = notes_root()
    except OSError as e:
        result["error"] = f"{type(e).__name__}: {e}"
        if strict:
            print(json.dumps({"ok": False, "error": result["error"]}, ensure_ascii=False))
            sys.exit(1)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
