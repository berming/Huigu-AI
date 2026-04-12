# Huigu-AI · A股日报自动存档系统

每日 **12:00（午间报告）** 与 **17:00（每日收盘报告）**（北京时间）各自动生成一份 A股动态报告，推送至 GitHub 仓库 `daily-reporter/reports/` 目录。报告文件名带"实际生成时刻"时分后缀（`astock_YYYYMMDD_HHMM.html`，例如 `astock_20260413_1201.html` / `astock_20260413_1702.html`），午间与每日场次互不覆盖。

## 项目结构

```
daily-reporter/
├── scripts/
│   ├── generate_report.py   # 核心：指数/个股/图表/股吧 → 生成 HTML
│   ├── fetch_guba.py        # 东财股吧大V帖子抓取与提炼
│   ├── git_push.py          # 报告 commit & push 到 GitHub
│   └── run_daily.py         # 定时任务入口（launchd 调用）
├── config/
│   └── cookie.txt           # 东财 Cookie（本地填写，不提交真实值）
├── reports/                 # 自动生成的 HTML 报告存档
├── logs/                    # 运行日志
├── com.huigu.astock-daily.plist  # macOS launchd 定时任务
├── setup.sh                 # 一键安装脚本
└── README.md
```

## 功能概览

| 模块 | 内容 |
|---|---|
| 指数行情 | 上证/深证/创业板/科创50/上证50 |
| 个股行情 | 比亚迪/华天科技/三六零/中航光电/科大讯飞 |
| 图表快照 | 分时图 + 日K线（base64 离线内嵌，git 可存档） |
| 主力资金追踪 | 近 10 日主力净流入 SVG 柱状图 + 当日 5 档拆解（超大/大/中/小单）+ 5/10 日合计（东方财富 fflow 接口，与同花顺 /funds/ 页面同源） |
| 股吧洞察 | 延安路老猫K、马上钧看市 帖子提炼（情绪/价位/个股关联） |
| 要闻摘要 | 新浪财经当日滚动要闻 |

## 一键安装

```bash
cd daily-reporter
bash setup.sh
```

## 首次配置 Cookie

股吧数据需要东财登录态：

1. Chrome 打开 `https://i.eastmoney.com/1141175439727114`
2. F12 → Network → 刷新页面
3. 点任意一条 `i.eastmoney.com` 请求 → Request Headers → Cookie
4. 复制完整 Cookie 值，替换 `config/cookie.txt` 中的 `YOUR_COOKIE_HERE`

Cookie 有效期约数天到数周，失效后重复上述步骤更新即可。

## 手动运行

```bash
# 立即生成今日（或最近交易日）报告并推送
# 未指定 --session 时按当前北京时间自动判断：<15:00 → 午间，否则 → 每日收盘
python3 scripts/run_daily.py

# 明确指定场次（文件名 HHMM 仍按当前实际时刻）
python3 scripts/run_daily.py --session noon     # 午间报告
python3 scripts/run_daily.py --session daily    # 每日收盘报告

# 只生成报告（不推送）
python3 scripts/generate_report.py --session noon
python3 scripts/generate_report.py --session daily

# 强制重新生成
python3 scripts/generate_report.py --session daily --force

# 只测试股吧抓取
python3 scripts/fetch_guba.py

# 查看所有帖子（不过滤关注个股）
python3 scripts/fetch_guba.py --all --days=3
```

## 定时任务管理

```bash
# 手动触发
launchctl start com.huigu.astock-daily

# 查看日志
tail -f logs/launchd_stderr.log

# 卸载
launchctl unload ~/Library/LaunchAgents/com.huigu.astock-daily.plist
```

## 关注个股池

| 股票 | 代码 | 赛道 |
|---|---|---|
| 比亚迪 | 002594 | 新能源汽车 + 自动驾驶 |
| 华天科技 | 002185 | 先进封装 / AI算力 |
| 三六零 | 601360 | AI应用 / 安全大模型 |
| 中航光电 | 002179 | 连接器 / 液冷 / CPO |
| 科大讯飞 | 002230 | AI大模型 / 语音 |

## 数据来源

| 数据 | 来源 |
|---|---|
| 指数实时行情 | 新浪财经 `hq.sinajs.cn` |
| 个股 T 日涨跌幅 | 同花顺 `stockpage.10jqka.com.cn` |
| 分时图 / 日K线 | 新浪财经图片接口（base64 内嵌 HTML） |
| 主力资金流向（日线） | 东方财富 `push2his.eastmoney.com/api/qt/stock/fflow/kline/get`（与同花顺 `/funds/` 同源算法） |
| 股吧帖子 | 东方财富 `i.eastmoney.com/api/guba/postCenterList` |
| 当日要闻 | 新浪财经滚动新闻 |

## 年度节假日更新

每年年初从上交所官网获取最新休市安排：
```
https://www.sse.com.cn/disclosure/dealinstruc/closed/
```
更新 `generate_report.py` 中的 `SSE_HOLIDAYS_20XX` 字典。

---

> ⚠️ 本系统仅供个人存档与学习参考，不构成投资建议。
