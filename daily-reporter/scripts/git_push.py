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

import sys
import subprocess
import datetime
import logging
import re
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

TARGET_BRANCH   = "main"
REPORTS_PATHSPEC = "daily-reporter/reports"     # 相对主仓库根的路径

# 命令超时（秒）：
#   本地操作 60s 足够；网络操作（fetch/push）放宽到 180s，避免 SSH
#   handshake / keychain 偶发慢响应打崩定时任务。
LOCAL_TIMEOUT = 60
NET_TIMEOUT   = 180

def run(cmd: list, cwd=None, check=True,
        timeout: int = LOCAL_TIMEOUT) -> subprocess.CompletedProcess:
    log.info("$ " + " ".join(str(c) for c in cmd))
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )
    if result.stdout.strip():
        log.info(result.stdout.strip())
    if result.stderr.strip():
        log.info(result.stderr.strip())
    if check and result.returncode != 0:
        raise RuntimeError(
            f"命令失败 (code={result.returncode}): "
            f"{' '.join(str(c) for c in cmd)}"
        )
    return result


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

    # 2) 工作区在 daily-reporter/reports/ 以外不能有未提交改动
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
        if not path.startswith(REPORTS_PATHSPEC):
            unrelated.append(path)
    if unrelated:
        preview = ", ".join(unrelated[:3])
        more = f" (+{len(unrelated)-3} more)" if len(unrelated) > 3 else ""
        raise RuntimeError(
            f"工作区存在 {REPORTS_PATHSPEC}/ 以外的未提交改动：{preview}{more}，"
            f"为避免误提交拒绝自动提交"
        )

    # 3) fetch origin main，了解 local / origin 的先后关系
    run(
        ["git", "fetch", "origin", TARGET_BRANCH],
        cwd=repo_root, timeout=NET_TIMEOUT,
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
    """在主工作区中 stage + commit + push `daily-reporter/reports/`。"""
    # Stage 所有 reports 下的变化（新建/修改/删除）
    run(
        ["git", "add", "-A", "--", REPORTS_PATHSPEC],
        cwd=repo_root,
    )

    # 查看 staged 内容；为空就直接返回（本次没有新报告）
    staged = run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo_root,
    ).stdout.strip().splitlines()

    if not staged:
        log.info("没有新报告变动，跳过 commit")
        return

    # 安全兜底：确认所有 staged 都在 reports 路径下
    bad = [p for p in staged if not p.startswith(REPORTS_PATHSPEC)]
    if bad:
        # 撤销 stage，避免污染用户工作区
        run(
            ["git", "reset", "HEAD", "--", REPORTS_PATHSPEC],
            cwd=repo_root, check=False,
        )
        raise RuntimeError(
            f"staged 中发现非 reports 路径：{bad[:3]}，已 reset 回工作区"
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

    # git push —— 显式推到 origin/main
    run(
        ["git", "push", "origin", TARGET_BRANCH],
        cwd=repo_root, timeout=NET_TIMEOUT,
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
