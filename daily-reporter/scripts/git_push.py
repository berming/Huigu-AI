#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git_push.py
将新生成的报告 commit 并 push 到 GitHub 仓库。
依赖：git（系统自带）、已配置好 SSH key（或 HTTPS token）
"""

import os
import sys
import subprocess
import datetime
import logging
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent   # huigu-reporter/scripts/
BASE_DIR    = SCRIPTS_DIR.parent                # huigu-reporter/
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

REPO_URL    = "git@github.com:berming/Huigu-AI.git"
REPO_DIR    = BASE_DIR / "repo"          # 本地 clone 目录
REPORTS_SUB = "astock-reports"          # 仓库内子目录

def run(cmd: list, cwd=None, check=True) -> subprocess.CompletedProcess:
    log.info("$ " + " ".join(str(c) for c in cmd))
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=60
    )
    if result.stdout.strip():
        log.info(result.stdout.strip())
    if result.stderr.strip():
        log.info(result.stderr.strip())
    if check and result.returncode != 0:
        raise RuntimeError(f"命令失败 (code={result.returncode}): {' '.join(str(c) for c in cmd)}")
    return result

def ensure_repo():
    """确保本地 clone 存在并最新"""
    if not REPO_DIR.exists():
        log.info(f"首次 clone 仓库: {REPO_URL}")
        run(["git", "clone", REPO_URL, str(REPO_DIR)])
    else:
        log.info("拉取最新代码...")
        run(["git", "pull", "--rebase"], cwd=REPO_DIR)

def copy_reports() -> list[Path]:
    """将 reports/ 下的新报告复制到 repo 子目录，返回复制的文件列表"""
    dest = REPO_DIR / REPORTS_SUB
    dest.mkdir(exist_ok=True)

    copied = []
    for f in sorted(REPORT_DIR.glob("astock_*.html")):
        target = dest / f.name
        if not target.exists() or f.stat().st_mtime > target.stat().st_mtime:
            import shutil
            shutil.copy2(f, target)
            copied.append(target)
            log.info(f"复制: {f.name} → {REPORTS_SUB}/")
    return copied

def git_commit_push(files: list[Path], t_day: datetime.date):
    """将文件 add + commit + push"""
    if not files:
        log.info("没有新文件需要提交")
        return

    # 配置 git 身份（首次运行时）
    run(["git", "config", "user.email", "huigu-ai@auto.bot"], cwd=REPO_DIR, check=False)
    run(["git", "config", "user.name",  "Huigu-AI"],         cwd=REPO_DIR, check=False)

    # git add
    for f in files:
        run(["git", "add", str(f.relative_to(REPO_DIR))], cwd=REPO_DIR)

    # git status
    status = run(["git", "status", "--porcelain"], cwd=REPO_DIR)
    if not status.stdout.strip():
        log.info("工作区无变更，跳过 commit")
        return

    # git commit
    date_cn  = t_day.strftime("%Y年%-m月%-d日")
    weekday  = ["周一","周二","周三","周四","周五","周六","周日"][t_day.weekday()]
    msg      = f"📊 A股日报 {date_cn}（{weekday}）[自动存档]"
    run(["git", "commit", "-m", msg], cwd=REPO_DIR)

    # git push
    run(["git", "push", "origin", "HEAD"], cwd=REPO_DIR)
    log.info(f"✅ 成功推送到 GitHub: {REPO_URL}")

def get_t_day() -> datetime.date:
    """复用 generate_report 的交易日判断"""
    sys.path.insert(0, str(Path(__file__).parent))
    from generate_report import get_t_day as _get_t_day
    return _get_t_day()

def main():
    log.info("=" * 60)
    log.info("Huigu-AI git_push 启动")
    try:
        t_day = get_t_day()
        log.info(f"T日 = {t_day}")
        ensure_repo()
        copied = copy_reports()
        git_commit_push(copied, t_day)
    except Exception as e:
        log.error(f"❌ 失败: {e}")
        import traceback
        log.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
