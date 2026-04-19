#!/usr/bin/env bash
# setup.sh
# 为 A-Stock-Analysis 安装 macOS 定时任务（launchd）
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST="$DIR/com.huigu.astock-analysis.plist"

echo "=== A-Stock-Analysis 定时任务安装 ==="
echo "报告目录: $DIR"
echo ""

# 读取 WatchPaths（向上两级到 Huigu-AI repo root）
REPO_DIR="$(dirname "$(dirname "$DIR")")"
echo "仓库目录: $REPO_DIR"

sed "s|{{SCRIPT_DIR}}|$DIR|g" "$PLIST" | sed "s|{{REPO_DIR}}|$REPO_DIR|g" > /tmp/com.huigu.astock-analysis.plist

echo "复制 plist 到 ~/Library/LaunchAgents/"
mkdir -p ~/Library/LaunchAgents
cp /tmp/com.huigu.astock-analysis.plist ~/Library/LaunchAgents/

echo ""
echo "加载定时任务..."
launchctl load ~/Library/LaunchAgents/com.huigu.astock-analysis.plist 2>/dev/null || true
echo ""
echo "=== 安装完成 ==="
echo "查看状态: launchctl list | grep huigu"
echo "测试运行: python3 $DIR/scripts/run_daily.py --session morning"
