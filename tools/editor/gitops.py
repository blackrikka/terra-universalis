"""편집기의 GitHub 패널: git 명령을 대신 돌린다 (받기·커밋·업로드·브랜치).

로그인은 git 의 자격 증명 관리자(Git Credential Manager)가 처음 업로드할 때 창을 띄워 받는다.
터미널 입력은 막아 둔다 (창 없는 실행기에서 멈추지 않도록).
"""

import glob
import os
import re
import shutil
import subprocess
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
BRANCH_RE = re.compile(r"^(?!/)(?!.*\.\.)(?!.*//)[A-Za-z0-9._/-]{1,100}(?<![/.])$")


def git_exe():
    hit = shutil.which("git")
    if hit:
        return hit
    cands = [r"C:\Program Files\Git\cmd\git.exe", r"C:\Program Files (x86)\Git\cmd\git.exe"]
    local = os.environ.get("LOCALAPPDATA", "")
    if local:   # GitHub Desktop 에 들어 있는 git
        cands += sorted(glob.glob(os.path.join(local, "GitHubDesktop", "app-*", "resources", "app", "git", "cmd", "git.exe")), reverse=True)
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


class GitError(Exception):
    pass


def run(repo, *args, timeout=60, check=True, raw=False):
    exe = git_exe()
    if not exe:
        raise GitError("git 을 찾을 수 없습니다. Git for Windows 또는 GitHub Desktop 을 설치해 주세요.")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C", LANG="C")
    try:
        r = subprocess.run([exe, "-c", "core.quotepath=false", *args], cwd=repo, env=env,
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout,
                           creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise GitError("git %s: 시간 초과 (%d초). 로그인 창이 떠 있다면 마치고 다시 눌러 주세요." % (args[0], timeout))
    out = (r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")).strip()
    if check and r.returncode != 0:
        raise GitError(explain(out) or "git %s 실패" % args[0])
    if raw:     # 앞 공백이 뜻을 갖는 출력 (status --porcelain)
        return r.stdout.decode("utf-8", "replace"), r.returncode
    return out, r.returncode


def explain(out):
    """자주 나오는 git 오류에 한국어 설명을 붙인다."""
    low = out.lower()
    tip = ""
    if "403" in low or "permission to" in low or "denied to" in low:
        tip = ("업로드 권한이 없습니다. 저장소 주인이 Settings → Collaborators 에서 이 GitHub 계정을 추가하고, "
               "메일로 온 초대를 수락해야 합니다.")
    elif "could not read username" in low or "authentication failed" in low:
        tip = "GitHub 로그인이 안 되어 있습니다. 다시 눌러서 뜨는 로그인 창에서 로그인해 주세요."
    elif "non-fast-forward" in low or "fetch first" in low or "rejected" in low:
        tip = "GitHub 쪽에 새 커밋이 있습니다. '최신 받기'를 먼저 누른 뒤 다시 업로드해 주세요."
    elif "not possible to fast-forward" in low or "diverging" in low or "divergent" in low:
        tip = "내 커밋과 GitHub 의 새 커밋이 갈라졌습니다. 새 브랜치로 업로드한 뒤 PR 로 합치는 것이 안전합니다."
    elif "would be overwritten" in low:
        tip = "아직 커밋하지 않은 고친 파일이 받을 내용과 겹칩니다. 먼저 커밋한 뒤 다시 받아 주세요."
    elif "could not resolve host" in low or "unable to access" in low:
        tip = "GitHub 에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요."
    elif "nothing to commit" in low or "no changes added" in low:
        tip = "커밋할 변경이 없습니다."
    return (tip + "\n\n" + out).strip() if tip else out


def remote_web(repo):
    out, rc = run(repo, "remote", "get-url", "origin", check=False)
    m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", out.strip()) if rc == 0 else None
    return "https://github.com/%s/%s" % (m.group(1), m.group(2)) if m else None


def status(repo, fetch=False):
    note = ""
    if fetch:
        try:
            run(repo, "fetch", "--prune", "origin", timeout=120)
        except GitError as e:
            note = str(e)
    branch = run(repo, "rev-parse", "--abbrev-ref", "HEAD")[0].strip()
    up, rc = run(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False)
    upstream = up.strip() if rc == 0 else None
    ahead = behind = 0
    if upstream:
        ab = run(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}")[0].split()
        ahead, behind = int(ab[0]), int(ab[1])
    raw, _ = run(repo, "status", "--porcelain=v1", "-z", "-uall", raw=True)
    files = []
    parts = raw.split("\0")
    i = 0
    while i < len(parts):
        p = parts[i]
        i += 1
        if len(p) < 4:
            continue
        code, path = p[:2], p[3:]
        if code[0] in "RC":     # 이름 바뀜: 다음 칸이 원래 이름
            i += 1
        files.append({"path": path, "code": code, "label": code_label(code)})
    branches = [b for b in run(repo, "branch", "--format=%(refname:short)")[0].splitlines() if b]
    log = run(repo, "log", "-8", "--format=%h\x1f%an\x1f%ar\x1f%s")[0].splitlines()
    commits = [dict(zip(("hash", "author", "when", "subject"), l.split("\x1f"))) for l in log if l]
    name = run(repo, "config", "user.name", check=False)[0].strip()
    return {"branch": branch, "upstream": upstream, "ahead": ahead, "behind": behind, "files": files,
            "branches": branches, "commits": commits, "user": name, "web": remote_web(repo), "note": note}


def code_label(code):
    if code == "??":
        return "새 파일"
    c = code.strip()[:1]
    return {"M": "수정", "A": "추가", "D": "삭제", "R": "이름 바뀜", "C": "복사", "U": "충돌"}.get(c, code.strip())


def diff(repo, path):
    out, rc = run(repo, "diff", "HEAD", "--", path, check=False)
    if out.strip():
        return out[:200000]
    p = (Path(repo) / path)
    if p.is_file():     # 아직 git 에 없는 새 파일
        try:
            return "(새 파일)\n\n" + p.read_text(encoding="utf-8-sig", errors="replace")[:60000]
        except OSError as e:
            return str(e)
    return "(차이 없음)"


def check_paths(repo, paths):
    root = Path(repo).resolve()
    for p in paths:
        q = (root / p).resolve()
        if q != root and root not in q.parents:
            raise GitError("저장소 밖 경로: %s" % p)


def pull(repo):
    out, _ = run(repo, "pull", "--ff-only", "origin", timeout=180)
    return out or "최신 상태입니다."


def switch(repo, branch, create=False):
    if not BRANCH_RE.match(branch or ""):
        raise GitError("브랜치 이름에는 영문·숫자·- _ . / 만 쓸 수 있습니다.")
    args = ("switch", "-c", branch) if create else ("switch", branch)
    out, _ = run(repo, *args)
    return out


def commit(repo, paths, message):
    if not paths:
        raise GitError("커밋할 파일을 하나 이상 고르세요.")
    if not (message or "").strip():
        raise GitError("커밋 메시지를 적어 주세요.")
    check_paths(repo, paths)
    run(repo, "add", "-A", "--", *paths)
    out, _ = run(repo, "commit", "-m", message.strip(), "--", *paths)
    return out


def push(repo):
    branch = run(repo, "rev-parse", "--abbrev-ref", "HEAD")[0].strip()
    out, _ = run(repo, "push", "-u", "origin", branch, timeout=600)
    web = remote_web(repo)
    pr = None
    if web and branch not in ("main", "master"):
        pr = "%s/compare/main...%s?expand=1" % (web, branch)
    return {"output": out or "업로드했습니다.", "branch": branch, "pr": pr}
