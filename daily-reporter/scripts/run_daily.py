#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_daily.py
定时任务入口脚本（由 macOS launchd 调用，也可手动运行）。
流程：判断报告场次 → 确定最近交易日 T → 生成 T 日报告 → push 到 GitHub

说明：
  - 每日 12:00 / 17:00 两次触发，分别生成「午间」和「每日」报告
  - 场次识别：--session noon|daily 优先；未指定则按当前 BJ 时间自动判断
    （< 15:00 记为 noon，否则 daily）
  - 无论今日是否为交易日，都以「最近交易日 T」为基准生成报告
  - 若当日当场次报告已存在，跳过生成，直接推送（可用 --force 强制重生成）
"""

import sys
import datetime
import logging
from pathlib import Path

# resolve() 确保拿到绝对路径，避免相对路径 parent 链出错
SCRIPTS_DIR = Path(__file__).resolve().parent   # huigu-reporter/scripts/
BASE_DIR    = SCRIPTS_DIR.parent                # huigu-reporter/
LOG_DIR     = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 将 scripts/ 加入 sys.path，使 generate_report / git_push 可被直接 import
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            LOG_DIR / f"run_{datetime.date.today()}.log",
            encoding="utf-8"
        ),
    ]
)
log = logging.getLogger(__name__)


def main():
    log.info("=" * 60)
    log.info("Huigu-AI 每日任务 启动")

    # 1. 导入核心模块
    from generate_report import (
        get_today_bj, is_trading_day, get_t_day,
        parse_session_arg, SESSIONS,
        main as gen_main,
    )
    from git_push import main as push_main

    # 2. 判定场次（CLI 优先，否则按当前 BJ 时间自动识别）
    session = parse_session_arg(sys.argv)
    meta = SESSIONS[session]
    log.info(f"报告场次 = {session}（{meta['title']} · 文件后缀 _{meta['hhmm']}）")

    # 3. 确定最近交易日 T（无论今日是否交易日都继续）
    today = get_today_bj()
    t_day = get_t_day()

    if is_trading_day(today):
        log.info(f"今日 {today} 是交易日，T = {t_day}")
    else:
        log.info(f"今日 {today} 非交易日，按最近交易日 T = {t_day} 生成报告")

    # 4. 生成报告
    try:
        gen_main(session=session)
    except SystemExit as e:
        if e.code == 0:
            log.info("报告已存在，跳过生成，继续推送...")
        else:
            log.error(f"报告生成异常退出: code={e.code}")
            raise
    except Exception as e:
        log.error(f"报告生成失败: {e}")
        import traceback
        log.error(traceback.format_exc())
        sys.exit(2)

    # 5. Push 到 GitHub
    try:
        push_main(session=session)
    except Exception as e:
        log.error(f"GitHub 推送失败: {e}")
        import traceback
        log.error(traceback.format_exc())
        sys.exit(3)

    log.info("✅ 全部完成")


if __name__ == "__main__":
    main()
