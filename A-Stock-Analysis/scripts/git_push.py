#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git_push.py (A-Stock-Analysis)
在主工作区中把 A-Stock-Analysis/reports/ + 根 index.html commit 到 main
并 push 到 GitHub。

安全机制移植自 daily-reporter/scripts/git_push.py：
  - Popen(start_new_session) + killpg 杀整组（含 ssh 孤儿）
  - GIT_SSH_COMMAND 禁 ControlMaster + 启 keepalive
  - 网络命令（fetch/push）最多 4 次尝试，backoff 2/4/8/16s
  - 3 道安全门禁：分支=main / 无不相关脏文件 / 本地不领先 origin
"""

import os
import signal
import sys
import subprocess
import datetime
import logging
import re
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
BASE_DIR    = SCRIPTS_DIR.parent                 # A-Stock-Analysis/
LOG_DIR     = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"{datetime.date.today()}.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

TARGET_BRANCH    = "main"
REPORTS_PATHSPEC = "A-Stock-Analysis/reports"
ROOT_INDEX_FILE  = "index.html"
AUTO_ROOT_FILES  = (ROOT_INDEX_FILE,)

# 其它项目的目录——忽略它们的 dirty 状态，不 commit 也不因它们拒绝
IGNORED_PATHSPECS = ("daily-reporter/", "StockAnalysis/")

LOCAL_TIMEOUT    = 60
NET_TIMEOUT      = 60
NET_MAX_ATTEMPTS = 4
NET_BACKOFF      = (2, 4, 8, 16)

NET_SSH_ENV = {
    "GIT_SSH_COMMAND": (
        "ssh "
        "-o ControlMaster=no "
        "-o ControlPath=none "
        "-o ServerAliveInterval=10 "
        "-o ServerAliveCountMax=6"
    ),
}


def _popen_with_session(cmd, cwd, env, timeout):
    p = subprocess.Popen(
        cmd, cwd=cwd, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = p.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, p.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
        try:
            stdout, stderr = p.communicate(timeout=5)
        except Exception:
            stdout, stderr = "", ""
        raise subprocess.TimeoutExpired(cmd, timeout, output=stdout, stderr=stderr)


def run(cmd, cwd=None, check=True, timeout=LOCAL_TIMEOUT, extra_env=None):
    log.info("$ " + " ".join(str(c) for c in cmd))
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    result = _popen_with_session(cmd, cwd=cwd, env=env, timeout=timeout)
    if result.stdout and result.stdout.strip():
        log.info(result.stdout.strip())
    if result.stderr and result.stderr.strip():
        log.info(result.stderr.strip())
    if check and result.returncode != 0:
        err_detail = (result.stderr or result.stdout or "").strip()
        detail = f" | {err_detail[:200]}" if err_detail else ""
        raise RuntimeError(
            f"命令失败 (code={result.returncode}): "
            f"{' '.join(str(c) for c in cmd)}{detail}"
        )
    return result


def run_net(cmd, cwd=None, check=True, timeout=NET_TIMEOUT,
            max_attempts=NET_MAX_ATTEMPTS, backoff=NET_BACKOFF):
    last_err = None
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            log.info(f"🔁 第 {attempt}/{max_attempts} 次尝试: {' '.join(str(c) for c in cmd)}")
        try:
            return run(cmd, cwd=cwd, check=check, timeout=timeout, extra_env=NET_SSH_ENV)
        except subprocess.TimeoutExpired as e:
            last_err = e
            if attempt < max_attempts:
                wait = backoff[min(attempt - 1, len(backoff) - 1)]
                log.info(f"⏱  第 {attempt}/{max_attempts} 次超时 ({timeout}s)，已 killpg 清理，{wait}s 后重试")
                time.sleep(wait)
            else:
                log.error(f"❌ 网络命令重试 {max_attempts} 次仍超时")
        except RuntimeError as e:
            last_err = e
            msg_low = str(e).lower()
            transient = any(k in msg_low for k in (
                "could not resolve", "connection", "network", "early eof",
                "unable to access", "the remote end hung up", "broken pipe",
                "ssh: connect to host", "timed out",
            ))
            if transient and attempt < max_attempts:
                wait = backoff[min(attempt - 1, len(backoff) - 1)]
                log.info(f"⚠  第 {attempt}/{max_attempts} 次失败：{str(e)[:100]}，{wait}s 后重试")
                time.sleep(wait)
            else:
                raise
    raise last_err if last_err else RuntimeError("网络命令重试耗尽")


def find_repo_root():
    r = run(["git", "rev-parse", "--show-toplevel"], cwd=SCRIPTS_DIR)
    root = Path(r.stdout.strip())
    if not root.is_dir() or not (root / ".git").exists():
        raise RuntimeError(f"无法找到主仓库根：{root}")
    return root


def ensure_on_main_clean(repo_root):
    branch = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root,
    ).stdout.strip()
    if branch != TARGET_BRANCH:
        raise RuntimeError(
            f"当前分支 = {branch!r}，不是 {TARGET_BRANCH}，拒绝自动提交"
        )

    status = run(["git", "status", "--porcelain"], cwd=repo_root).stdout
    unrelated = []
    for line in status.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        if path.startswith(REPORTS_PATHSPEC):
            continue
        if path in AUTO_ROOT_FILES:
            continue
        if any(path.startswith(p) for p in IGNORED_PATHSPECS):
            continue
        unrelated.append(path)
    if unrelated:
        preview = ", ".join(unrelated[:3])
        more = f" (+{len(unrelated)-3} more)" if len(unrelated) > 3 else ""
        raise RuntimeError(
            f"工作区存在不相关的未提交改动：{preview}{more}，拒绝自动提交"
        )

    run_net(["git", "fetch", "origin", TARGET_BRANCH], cwd=repo_root)

    ahead = int(run(
        ["git", "rev-list", "--count", f"origin/{TARGET_BRANCH}..HEAD"],
        cwd=repo_root,
    ).stdout.strip() or 0)
    behind = int(run(
        ["git", "rev-list", "--count", f"HEAD..origin/{TARGET_BRANCH}"],
        cwd=repo_root,
    ).stdout.strip() or 0)

    if ahead > 0:
        raise RuntimeError(
            f"本地 {TARGET_BRANCH} 领先 origin 共 {ahead} 个 commit，"
            f"拒绝自动提交（先手动 push 或 reset）"
        )
    if behind > 0:
        log.info(f"本地落后 origin {behind} 个 commit，快进合并 ...")
        run(["git", "merge", "--ff-only", f"origin/{TARGET_BRANCH}"], cwd=repo_root)


def git_commit_push(repo_root, session=None):
    pathspecs = [REPORTS_PATHSPEC]
    if (repo_root / ROOT_INDEX_FILE).exists():
        pathspecs.append(ROOT_INDEX_FILE)

    run(["git", "add", "-A", "--", *pathspecs], cwd=repo_root)

    staged = run(
        ["git", "diff", "--cached", "--name-only"], cwd=repo_root,
    ).stdout.strip().splitlines()

    if not staged:
        log.info("没有新报告 / 索引变动，跳过 commit")
        return

    def _is_allowed(p):
        return p.startswith(REPORTS_PATHSPEC) or p in AUTO_ROOT_FILES
    bad = [p for p in staged if not _is_allowed(p)]
    if bad:
        run(["git", "reset", "HEAD", "--", *pathspecs], cwd=repo_root, check=False)
        raise RuntimeError(f"staged 中发现白名单以外的路径：{bad[:3]}，已 reset")

    log.info(f"staged {len(staged)} 个文件：")
    for p in staged[:8]:
        log.info(f"  - {p}")

    run(["git", "config", "user.email", "huigu-ai@auto.bot"], cwd=repo_root, check=False)
    run(["git", "config", "user.name",  "Huigu-AI"],          cwd=repo_root, check=False)

    hh_mm_list = []
    for p in staged:
        m = re.search(r"_(\d{2})(\d{2})\.html$", p)
        if m:
            hh_mm_list.append(f"{m.group(1)}:{m.group(2)}")
    hh_mm_tag = " / ".join(sorted(set(hh_mm_list))) if hh_mm_list else ""

    t = datetime.datetime.now().strftime("%Y-%m-%d")
    suffix = f" {hh_mm_tag}" if hh_mm_tag else ""
    msg = f"📊 A-Stock-Analysis 报告{suffix} · {t} [自动存档]"

    run(["git", "commit", "-m", msg], cwd=repo_root)

    cur = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root,
    ).stdout.strip()
    if cur != TARGET_BRANCH:
        raise RuntimeError(f"当前分支 {cur!r}，拒绝推送（期望 {TARGET_BRANCH}）")

    run_net(["git", "push", "origin", TARGET_BRANCH], cwd=repo_root)
    log.info(f"✅ 成功推送到 GitHub (origin/{TARGET_BRANCH})")


def main(session=None):
    log.info("=" * 60)
    log.info("A-Stock-Analysis git_push 启动")
    try:
        repo_root = find_repo_root()
        log.info(f"主仓库根 = {repo_root}")
        ensure_on_main_clean(repo_root)
        git_commit_push(repo_root, session=session)
    except Exception as e:
        log.error(f"❌ 失败: {e}")
        import traceback
        log.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
