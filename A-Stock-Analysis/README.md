# A-Stock-Analysis · A股市场行情分析

每交易日 **早市（08:30） / 午市（12:30） / 晚市（19:30）** 自动生成A股大盘及个股行情报告。

## 功能特点

- **三大场次**：早市（盘前参考）、午市（午盘总结）、晚市（收盘复盘）
- **多数据源融合**：
  - Baostock：主要指数 + 自选股历史行情（均线、距高低点）
  - 新浪财经：实时指数 + 个股分时图/日K线快照（离线内嵌）
  - 东方财富：主力资金流向（5档资金拆解 + 10日柱状图）
  - 同花顺：涨跌验证
- **Markdown + HTML 双报告**：Markdown 适合存档，HTML 适合浏览（含图表快照）
- **GitHub Pages 自动索引**：根目录 `index.html` 聚合所有报告链接

## 目录结构

```
A-Stock-Analysis/
├── reports/          # 自动生成的报告（HTML + Markdown）
├── scripts/
│   ├── generate_report.py   # 报告生成核心脚本
│   ├── run_daily.py         # 定时任务入口
│   └── git_push.py          # GitHub 推送脚本
├── logs/             # 日志
└── README.md
```

## 手动触发

```bash
# 早市 / 午市 / 晚市
python3 scripts/run_daily.py --session morning
python3 scripts/run_daily.py --session noon
python3 scripts/run_daily.py --session evening
```

## 定时任务（macOS launchd）

```bash
# 安装定时任务（需要配置路径）
./scripts/setup.sh
```

> ⚠️ 数据来源 Baostock / 新浪财经 / 东方财富，仅供个人存档参考，不构成投资建议。
