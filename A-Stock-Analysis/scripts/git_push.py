#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git_push.py
将 A-Stock-Analysis/reports/ 下的报告推送到 GitHub。
使用 GitPython 直接操作，无须 shell。
"""

import subprocess
import sys
import datetime
import logging
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPTS_DIR.parent

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def run_git(*args, cwd=None):
    result = subprocess.run(["git"] + list(args), cwd=cwd or BASE_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        log.warning(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def main(session=None):
    log.info("=" * 60)
    log.info("GitHub 推送 启动")

    repo = BASE_DIR.parent  # Huigu-AI repo root

    # Configure Git if needed
    run_git("config", "user.name", "Huigu-AI Bot", cwd=repo)
    run_git("config", "user.email", "bot@huigu.ai", cwd=repo)

    # Add new/changed files
    result = run_git("add", f"A-Stock-Analysis/reports/", cwd=repo)
    result = run_git("status", "--porcelain", cwd=repo)
    staged = [l for l in result.stdout.splitlines() if l.startswith(("A", "M", "?", "D")))]
    log.info(f"变更文件: {staged}")

    if not staged:
        log.info("无变更，跳过提交")
        return

    # Commit
    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"chore(A-Stock-Analysis): 自动存档报告 · {t}"
    run_git("commit", "-m", msg, cwd=repo)

    # Push
    result = run_git("push", "origin", "main", cwd=repo)
    if result.returncode == 0:
        log.info(f"✅ 推送成功: {msg}")
    else:
        log.error(f"⚠ 推送失败: {result.stderr}")


if __name__ == "__main__":
    main()
