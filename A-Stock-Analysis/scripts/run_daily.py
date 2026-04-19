#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_daily.py
定时任务入口脚本（由 launchd/macOS 调用，也可手动运行）。
流程：判断报告场次 → 确定最近交易日 T → 生成 T 日报告 → 推送到 GitHub

每日三次触发：
  08:30 → morning（早市盘前参考）
  12:30 → noon（午市午盘总结）
  19:30 → evening（晚市收盘复盘）
"""

import sys
import datetime
import logging
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPTS_DIR.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"run_{datetime.date.today()}.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)


def main():
    log.info("=" * 60)
    log.info("A-Stock-Analysis 每日任务 启动")

    from generate_report import (
        get_bj_now, is_trading_day, get_t_day,
        parse_session_arg, SESSIONS,
        main as gen_main,
    )

    session = parse_session_arg(sys.argv)
    meta = SESSIONS[session]
    log.info(f"场次 = {session}（{meta['title']} · {meta['slot']}）")

    today = get_bj_now().date()
    t_day = get_t_day()

    if is_trading_day(today):
        log.info(f"今日 {today} 是交易日，T = {t_day}")
    else:
        log.info(f"今日 {today} 非交易日，按最近交易日 T = {t_day} 生成报告")

    try:
        html_path = gen_main(session=session)
        log.info(f"✅ 报告生成完成: {html_path}")
    except Exception as e:
        log.error(f"报告生成失败: {e}")
        import traceback
        log.error(traceback.format_exc())
        sys.exit(2)

    log.info("✅ 全部完成")


if __name__ == "__main__":
    main()
