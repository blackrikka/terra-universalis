"""Terra Universalis 편집기 실행기 (TerraEditor.exe 의 본체).

편집기 서버를 안에서 켜고, Edge(없으면 Chrome)를 주소창 없는 앱 창으로 띄운다.
창을 닫으면 서버도 같이 꺼진다. 저장소 위치는 exe 근처에서 찾고, 못 찾으면 폴더를 물어본 뒤 기억한다.

    python -I tools/editor/app.py [저장소 폴더]
"""

import ctypes
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path

import server

APP = "Terra Universalis 편집기"
DATA = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "TerraUniversalisEditor"
CONFIG = DATA / "config.json"
LOG = DATA / "editor.log"


def message(text, error=False):
    try:
        ctypes.windll.user32.MessageBoxW(None, text, APP, 0x10 if error else 0x40)
    except Exception:       # noqa: BLE001
        print(text)


def log(text):
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + text + "\n")
    except OSError:
        pass


def load_config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def find_repo(argv):
    if len(argv) > 1 and server.looks_like_repo(argv[1]):
        return Path(argv[1])
    start = Path(sys.executable if server.FROZEN else __file__).resolve().parent
    for base in (start, Path.cwd()):
        for p in (base, *base.parents):
            if server.looks_like_repo(p):
                return p
    cfg = load_config()
    if cfg.get("repo") and server.looks_like_repo(cfg["repo"]):
        return Path(cfg["repo"])
    return ask_repo()


def ask_repo():
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return None
    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    while True:
        d = filedialog.askdirectory(title="terra-universalis 저장소 폴더를 골라 주세요 (terra_universalis 폴더가 들어 있는 곳)")
        if not d:
            root.destroy()
            return None
        if server.looks_like_repo(d):
            root.destroy()
            return Path(d)
        message("이 폴더에는 terra_universalis/descriptor.mod 가 없습니다. 저장소 맨 위 폴더를 골라 주세요.", True)


def browser():
    """앱 창으로 띄울 브라우저 (Edge 우선)."""
    cands = []
    for env in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        base = os.environ.get(env)
        if base:
            cands += [Path(base) / "Microsoft/Edge/Application/msedge.exe",
                      Path(base) / "Google/Chrome/Application/chrome.exe"]
    for c in cands:
        if c.is_file():
            return str(c)
    return shutil.which("msedge") or shutil.which("chrome")


def free_port(prefer):
    for port in (prefer, 0):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", port))
            return s.getsockname()[1]
        except OSError:
            continue
        finally:
            s.close()
    raise RuntimeError("빈 포트를 찾을 수 없습니다")


def main(argv):
    repo = find_repo(argv)
    if not repo:
        message("저장소 폴더를 고르지 않아서 끝냅니다.")
        return 1
    cfg = load_config()
    cfg["repo"] = str(repo)
    save_config(cfg)
    server.set_repo(repo)
    log("start repo=%s" % repo)

    port = free_port(8766)
    srv = ThreadingHTTPServer(("127.0.0.1", port), server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d/" % port

    exe = browser()
    if exe:
        prof = DATA / "window"
        subprocess.Popen([exe, "--app=" + url, "--user-data-dir=" + str(prof), "--no-first-run",
                          "--no-default-browser-check", "--window-size=1500,950"],
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        webbrowser.open(url)

    # 화면마다 5초에 한 번 /api/ping 을 보내고, 닫힐 때 /api/bye 를 보낸다.
    # 열린 화면이 하나도 없는 채로 몇 초 지나면(새로고침이 아니면) 끈다.
    # 창을 내려 두면 브라우저가 타이머를 1분에 한 번까지 늦추므로, 소식만 끊긴 화면은 5분까지 살아 있다고 본다.
    started = time.time()
    seen = False
    empty_since = None
    while True:
        time.sleep(1)
        while server.EVENTS:
            log(server.EVENTS.pop(0))
        now = time.time()
        live = [c for c, t in list(server.CLIENTS.items()) if now - t < 300]
        if live:
            seen, empty_since = True, None
            continue
        if not seen:
            if now - started > 90:
                message("편집기 창이 열리지 않았습니다. 브라우저에서 %s 를 직접 열어 보세요." % url, True)
                return 1
            continue
        empty_since = empty_since or now
        if now - empty_since > 6:
            break
    srv.shutdown()
    log("stop")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:       # noqa: BLE001
        tb = traceback.format_exc()
        log(tb)
        message("편집기를 켜다가 오류가 났습니다.\n\n%s\n\n기록: %s" % (tb[-1500:], LOG), True)
        sys.exit(1)
