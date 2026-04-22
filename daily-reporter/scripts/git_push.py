#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git_push.py
在**主工作区**（调用本脚本的 git checkout）中把 daily-reporter/reports/
下新生成的 HTML 报告 commit 到 main 分支并 push 到 GitHub。

设计要点：
  - 不再使用嵌套 clone / repo/ 目录——daily-reporter 本身已经位于主仓库
    工作区内，直接在这个工作区里操作即可
  - 只 stage `daily-reporter/reports/**`，绝不触碰用户的其它改动
  - 严格的安全门禁（any check fails → 中止，保留报告文件给下次运行）：
      · 当前分支必须是 main
      · 工作区在 daily-reporter/reports/ 以外不能有未提交改动
      · 本地 main 不能领先 origin/main（防止把用户未推送的 dev commit
        一起推出去）
  - 若 origin/main 领先本地，先 `git merge --ff-only`（纯本地，非 rebase）
  - 最终 `git push origin main`
依赖：git（系统自带）、已配置好 SSH key（或 HTTPS token）
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

SCRIPTS_DIR = Path(__file__).resolve().parent    # huigu-reporter/scripts/
BASE_DIR    = SCRIPTS_DIR.parent                 # huigu-reporter/
REPORT_DIR  = BASE_DIR / "reports"
LOG_DIR     = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 确保 scripts/ 在 path 中（get_t_day 依赖 generate_report）
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

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
REPORTS_PATHSPEC = "daily-reporter/reports"     # 相对主仓库根的路径
ROOT_INDEX_FILE  = "index.html"                  # GitHub Pages 首页

# 自动生成、允许被本脚本 commit 的根目录文件（只接受精确匹配的文件名）
AUTO_ROOT_FILES  = (ROOT_INDEX_FILE,)

# 其它项目的目录——忽略它们的 dirty 状态，不 commit 也不因它们拒绝
IGNORED_PATHSPECS = ("A-Stock-Analysis/", "StockAnalysis/")

# ── 命令超时（秒） ─────────────────────────────────────────
# 本地 git 命令 60s 足够。
# 网络命令（fetch/push）——历史上出现过 `git push` 180s 完全无输出
# 卡死的情况（根因：stale SSH ControlMaster socket / 死 TCP 连接）。
# 策略：每次 60s 快速失败，配合 killpg 清掉孤儿 ssh 子进程 + 重试。
LOCAL_TIMEOUT   = 60
NET_TIMEOUT     = 60                         # 每次网络尝试的超时
NET_MAX_ATTEMPTS = 4                          # 网络命令最多尝试次数
NET_BACKOFF     = (2, 4, 8, 16)               # 重试之间的等待秒数

# 网络命令的 SSH 环境变量：
#   - ControlMaster=no / ControlPath=none  强制每次新建 SSH 连接，避免
#     launchd 无 TTY 场景下 stale 多路复用 socket 让第二次连接挂死
#   - ServerAliveInterval=10 / ServerAliveCountMax=6  60 秒内对端无响应
#     即主动断开（否则 TCP 层死连接会让 ssh 傻等到天荒地老）
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
    """用 Popen 启动子进程并给一个独立 process group；超时则用 killpg
    把整个 group（包括 git fork 出的 ssh / ssh fork 出的 ssh-askpass 等）
    一锅端，避免孤儿进程继续握住 stale 网络 socket。"""
    p = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,      # 新 session → 独立 process group
    )
    try:
        stdout, stderr = p.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, p.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        # 杀整组，清理 git 及其 fork 出的 ssh
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
        # 再给 5 秒抽干残余输出
        try:
            stdout, stderr = p.communicate(timeout=5)
        except Exception:
            stdout, stderr = "", ""
        raise subprocess.TimeoutExpired(
            cmd, timeout, output=stdout, stderr=stderr
        )


def run(cmd: list, cwd=None, check=True,
        timeout: int = LOCAL_TIMEOUT,
        extra_env: dict = None) -> subprocess.CompletedProcess:
    """执行子进程。带 process-group 超时清理、日志、non-zero 异常抛出。"""
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
        # 把 stderr 一并塞进错误消息，便于上层 run_net 根据关键词判定是否
        # 为 transient 网络错误（"connection refused" 等）
        err_detail = (result.stderr or result.stdout or "").strip()
        detail = f" | {err_detail[:200]}" if err_detail else ""
        raise RuntimeError(
            f"命令失败 (code={result.returncode}): "
            f"{' '.join(str(c) for c in cmd)}{detail}"
        )
    return result


def run_net(cmd: list, cwd=None, check=True,
            timeout: int = NET_TIMEOUT,
            max_attempts: int = NET_MAX_ATTEMPTS,
            backoff=NET_BACKOFF) -> subprocess.CompletedProcess:
    """执行网络 git 命令（fetch / push）带自动重试。每次尝试：
    1) 以 NET_SSH_ENV 强制新建 SSH 连接 + 启用 keepalive
    2) timeout 超时 → killpg 清理 → 按 backoff 等待 → 再来一次
    3) 非超时的 transient 网络错误也会触发重试；鉴权 / 非 ff 拒绝等错误
       直接抛出不重试（重试无用）。
    """
    last_err = None
    for attempt in range(1, max_attempts + 1):
        label = f"第 {attempt}/{max_attempts} 次"
        if attempt > 1:
            log.info(f"🔁 {label}尝试网络命令: {' '.join(str(c) for c in cmd)}")
        try:
            return run(cmd, cwd=cwd, check=check, timeout=timeout,
                       extra_env=NET_SSH_ENV)
        except subprocess.TimeoutExpired as e:
            last_err = e
            if attempt < max_attempts:
                wait = backoff[min(attempt - 1, len(backoff) - 1)]
                log.info(
                    f"⏱  {label}超时 ({timeout}s)，已 killpg 清理 ssh，"
                    f"{wait}s 后重试"
                )
                time.sleep(wait)
            else:
                log.error(f"❌ 网络命令重试 {max_attempts} 次仍超时")
        except RuntimeError as e:
            last_err = e
            msg_low = str(e).lower()
            # 仅对 transient 网络错误重试；鉴权 / 非 ff 拒绝立即失败
            transient_markers = (
                "could not resolve",
                "connection",
                "network",
                "early eof",
                "unable to access",
                "the remote end hung up",
                "broken pipe",
                "ssh: connect to host",
                "timed out",
            )
            is_transient = any(k in msg_low for k in transient_markers)
            if is_transient and attempt < max_attempts:
                wait = backoff[min(attempt - 1, len(backoff) - 1)]
                log.info(
                    f"⚠  {label}失败（疑似瞬时网络错误）：{str(e)[:100]}，"
                    f"{wait}s 后重试"
                )
                time.sleep(wait)
            else:
                raise
    # 所有尝试都失败
    raise last_err if last_err else RuntimeError("网络命令重试耗尽")


def find_repo_root() -> Path:
    """从 scripts/ 目录向上解析主工作区的 git 根。"""
    r = run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=SCRIPTS_DIR,
    )
    root = Path(r.stdout.strip())
    if not root.is_dir() or not (root / ".git").exists():
        raise RuntimeError(f"无法找到主仓库根：{root}")
    return root


def ensure_on_main_clean(repo_root: Path):
    """所有安全门禁：分支 / 工作区 / 本地 - origin 关系。"""
    # 1) 分支必须是 main
    branch = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root,
    ).stdout.strip()
    if branch != TARGET_BRANCH:
        raise RuntimeError(
            f"当前分支 = {branch!r}，不是 {TARGET_BRANCH}，"
            f"拒绝自动提交（报告文件保留在 {REPORT_DIR}，"
            f"下次在 main 分支上运行时会被继续处理）"
        )

    # 2) 工作区在 "daily-reporter/reports/ + 允许的根目录自动文件" 以外
    #    不能有未提交改动
    status = run(
        ["git", "status", "--porcelain"], cwd=repo_root,
    ).stdout
    unrelated = []
    for line in status.splitlines():
        if not line:
            continue
        # porcelain 格式：前两列状态 + 1 空格 + 路径
        path = line[3:].strip()
        # rename 形式 "X  old -> new" 取 new
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        # 去掉可能的引号
        path = path.strip('"')
        # 允许：daily-reporter/reports/... 或 根目录 index.html
        if path.startswith(REPORTS_PATHSPEC):
            continue
        if path in AUTO_ROOT_FILES:
            continue
        # 忽略：其它项目的目录（它们有自己的 commit 流程）
        if any(path.startswith(p) for p in IGNORED_PATHSPECS):
            continue
        unrelated.append(path)
    if unrelated:
        preview = ", ".join(unrelated[:3])
        more = f" (+{len(unrelated)-3} more)" if len(unrelated) > 3 else ""
        raise RuntimeError(
            f"工作区存在 {REPORTS_PATHSPEC}/ 与 {list(AUTO_ROOT_FILES)} "
            f"以外的未提交改动：{preview}{more}，为避免误提交拒绝自动提交"
        )

    # 3) fetch origin main，了解 local / origin 的先后关系（带重试）
    run_net(
        ["git", "fetch", "origin", TARGET_BRANCH],
        cwd=repo_root,
    )
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
            f"本地 {TARGET_BRANCH} 领先 origin/{TARGET_BRANCH} {ahead} 个 "
            f"commit，疑似未推送的开发工作，拒绝自动提交（先手动 push 或 "
            f"reset 再重跑）"
        )

    if behind > 0:
        log.info(
            f"本地 {TARGET_BRANCH} 落后 origin/{TARGET_BRANCH} {behind} 个 "
            f"commit，快进合并 ..."
        )
        run(
            ["git", "merge", "--ff-only", f"origin/{TARGET_BRANCH}"],
            cwd=repo_root,
        )


def git_commit_push(repo_root: Path, t_day: datetime.date, session: str = "daily"):
    """在主工作区中 stage + commit + push `daily-reporter/reports/` 以及
    GitHub Pages 首页 `index.html`。"""
    # 构建 pathspec 列表：永远包含 reports/，若 index.html 已存在则一起 stage
    pathspecs = [REPORTS_PATHSPEC]
    if (repo_root / ROOT_INDEX_FILE).exists():
        pathspecs.append(ROOT_INDEX_FILE)

    # Stage 所有相关路径下的变化（新建/修改/删除）
    run(
        ["git", "add", "-A", "--", *pathspecs],
        cwd=repo_root,
    )

    # 查看 staged 内容；为空就直接返回（本次没有新报告 / 索引）
    staged = run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo_root,
    ).stdout.strip().splitlines()

    if not staged:
        log.info("没有新报告 / 索引变动，跳过 commit")
        return

    # 安全兜底：确认所有 staged 都在允许白名单内（reports/ 或 index.html）
    def _is_allowed(p: str) -> bool:
        return p.startswith(REPORTS_PATHSPEC) or p in AUTO_ROOT_FILES
    bad = [p for p in staged if not _is_allowed(p)]
    if bad:
        # 撤销 stage，避免污染用户工作区
        run(
            ["git", "reset", "HEAD", "--", *pathspecs],
            cwd=repo_root, check=False,
        )
        raise RuntimeError(
            f"staged 中发现白名单以外的路径：{bad[:3]}，已 reset 回工作区"
        )

    log.info(f"staged {len(staged)} 个文件：")
    for p in staged[:8]:
        log.info(f"  - {p}")
    if len(staged) > 8:
        log.info(f"  ... (+{len(staged) - 8} more)")

    # 查场次元信息（仅用于 commit 标题：A股午报 / A股日报）
    sys.path.insert(0, str(SCRIPTS_DIR))
    from generate_report import SESSIONS
    meta       = SESSIONS.get(session, SESSIONS["daily"])
    title_name = meta["title"]

    # 从被提交文件名中解析实际生成时分（astock_YYYYMMDD_HHMM.html）
    hh_mm_list = []
    for p in staged:
        m = re.search(r"_(\d{2})(\d{2})\.html$", p)
        if m:
            hh_mm_list.append(f"{m.group(1)}:{m.group(2)}")
    hh_mm_tag = " / ".join(sorted(set(hh_mm_list))) if hh_mm_list else ""

    # 配置 git 身份（不影响全局配置）
    run(
        ["git", "config", "user.email", "huigu-ai@auto.bot"],
        cwd=repo_root, check=False,
    )
    run(
        ["git", "config", "user.name",  "Huigu-AI"],
        cwd=repo_root, check=False,
    )

    # 构造 commit 信息
    date_cn  = t_day.strftime("%Y年%-m月%-d日")
    weekday  = ["周一","周二","周三","周四","周五","周六","周日"][t_day.weekday()]
    suffix   = f" {hh_mm_tag}" if hh_mm_tag else ""
    msg      = f"📊 {title_name} {date_cn}（{weekday}{suffix}）[自动存档]"

    # 仅 commit 已 stage 的内容（不会带上用户可能存在的 unstaged 改动）
    run(["git", "commit", "-m", msg], cwd=repo_root)

    # 推送前再核对一次当前分支
    cur = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
    ).stdout.strip()
    if cur != TARGET_BRANCH:
        raise RuntimeError(
            f"当前分支为 {cur!r}，拒绝推送（期望 {TARGET_BRANCH}）"
        )

    # git push —— 显式推到 origin/main（带重试：killpg 清孤儿 ssh + backoff）
    run_net(
        ["git", "push", "origin", TARGET_BRANCH],
        cwd=repo_root,
    )
    log.info(f"✅ 成功推送到 GitHub (origin/{TARGET_BRANCH})")


def get_t_day() -> datetime.date:
    """复用 generate_report 的交易日判断"""
    sys.path.insert(0, str(SCRIPTS_DIR))
    from generate_report import get_t_day as _get_t_day
    return _get_t_day()


def main(session: str = None):
    log.info("=" * 60)
    log.info("Huigu-AI git_push 启动")
    try:
        # 若未传入场次，则复用 generate_report 的自动识别
        if session is None:
            sys.path.insert(0, str(SCRIPTS_DIR))
            from generate_report import parse_session_arg
            session = parse_session_arg(sys.argv)
        log.info(f"场次 = {session}")

        t_day = get_t_day()
        log.info(f"T日 = {t_day}")

        repo_root = find_repo_root()
        log.info(f"主仓库根 = {repo_root}")

        ensure_on_main_clean(repo_root)
        git_commit_push(repo_root, t_day, session=session)
    except Exception as e:
        log.error(f"❌ 失败: {e}")
        import traceback
        log.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
