#!/bin/bash
# A股报告生成并推送到GitHub
# 每天早市 08:30 / 午市 12:30 / 晚市 19:30 运行

REPORT_DIR="/Users/bermini/.openclaw/workspace/StockAnalysis"
SCRIPT="$REPORT_DIR/generate_report.py"
PERIOD="$1"  # morning / noon / evening

if [ -z "$PERIOD" ]; then
    echo "Usage: $0 <morning|noon|evening>"
    exit 1
fi

cd "$REPORT_DIR" || exit 1

# 生成报告
REPORT_DIR="$REPORT_DIR" python3 "$SCRIPT" "$PERIOD" 2>/dev/null

# 找到刚生成的文件
TODAY=$(date +%Y%m%d)
PERIOD_CN=""
case "$PERIOD" in
    morning) PERIOD_CN="早" ;;
    noon)    PERIOD_CN="午" ;;
    evening) PERIOD_CN="晚" ;;
esac
REPORT_FILE="stock_report_${TODAY}_${PERIOD_CN}.md"

if [ -f "$REPORT_FILE" ]; then
    # 提交并推送
    git add "$REPORT_FILE"
    git commit -m "chore: A股行情报告 ${TODAY} ${PERIOD_CN}市 (@ $(date '+%H:%M:%S'))"
    git push origin main 2>&1
    echo "✅ 报告已推送: $REPORT_FILE"
else
    echo "⚠️ 报告文件未生成: $REPORT_FILE"
    exit 1
fi
