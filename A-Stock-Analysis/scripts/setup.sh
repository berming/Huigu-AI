#!/usr/bin/env bash
# setup.sh
# 为 A-Stock-Analysis 安装 macOS 定时任务（launchd）
set -e

# A-Stock-Analysis 目录（setup.sh 的父目录）
DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="$DIR/scripts"
REPO_DIR="$(dirname "$DIR")"

PLIST="$DIR/com.huigu.astock-analysis.plist"

echo "=== A-Stock-Analysis 定时任务安装 ==="
echo "脚本目录: $SCRIPT_DIR"
echo "项目目录: $DIR"
echo "仓库目录: $REPO_DIR"

sed "s|{{SCRIPT_DIR}}|$SCRIPT_DIR|g" "$PLIST" | \
  sed "s|{{REPO_DIR}}|$REPO_DIR|g" > /tmp/com.huigu.astock-analysis.plist

echo "复制 plist 到 ~/Library/LaunchAgents/"
mkdir -p ~/Library/LaunchAgents
cp /tmp/com.huigu.astock-analysis.plist ~/Library/LaunchAgents/

echo ""
echo "加载定时任务..."
launchctl load ~/Library/LaunchAgents/com.huigu.astock-analysis.plist 2>/dev/null || true
echo ""
echo "=== 安装完成 ==="
echo "查看状态: launchctl list | grep huigu"
echo "测试运行: python3 $SCRIPT_DIR/run_daily.py --session morning"
