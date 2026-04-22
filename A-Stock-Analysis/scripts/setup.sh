#!/usr/bin/env bash
# setup.sh — A-Stock-Analysis 一键安装 macOS 定时任务
set -e

# ── 路径解析 ─────────────────────────────────
DIR="$(cd "$(dirname "$0")/.." && pwd)"          # A-Stock-Analysis/
SCRIPT_DIR="$DIR/scripts"
BASE_DIR="$DIR"
REPO_DIR="$(dirname "$DIR")"                     # Huigu-AI/

PLIST_SRC="$DIR/com.huigu.astock-analysis.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.huigu.astock-analysis.plist"

echo "═══════════════════════════════════════════"
echo " A-Stock-Analysis · 定时任务安装"
echo "═══════════════════════════════════════════"
echo ""

# ── 1. 检查依赖 ──────────────────────────────
echo "▶ 检查依赖..."
command -v python3 >/dev/null || { echo "❌ 未找到 python3"; exit 1; }
command -v git     >/dev/null || { echo "❌ 未找到 git"; exit 1; }
PYTHON=$(command -v python3)
GIT=$(command -v git)
echo "  python3: $PYTHON"
echo "  git:     $GIT"

# 检查 baostock
python3 -c "import baostock" 2>/dev/null && echo "  baostock: ✅" || {
    echo "  baostock: ❌ 未安装，请先 pip3 install baostock"
    exit 1
}

# ── 2. 创建日志目录 ──────────────────────────
mkdir -p "$BASE_DIR/logs" "$BASE_DIR/reports"

# ── 3. 生成 plist（替换占位符） ──────────────
echo ""
echo "▶ 配置 launchd plist..."
sed -e "s|{{PYTHON3}}|$PYTHON|g" \
    -e "s|{{SCRIPT_DIR}}|$SCRIPT_DIR|g" \
    -e "s|{{BASE_DIR}}|$BASE_DIR|g" \
    -e "s|{{REPO_DIR}}|$REPO_DIR|g" \
    "$PLIST_SRC" > "$PLIST_DST"
echo "  ✅ plist 已写入: $PLIST_DST"

# ── 4. 加载 launchd（先卸载旧的，再加载） ───
echo ""
echo "▶ 加载 launchd 任务..."
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"
echo "  ✅ 定时任务已加载"

# ── 5. 验证 ──────────────────────────────────
echo ""
echo "▶ 验证任务状态..."
launchctl list | grep "astock-analysis" || echo "  ⚠️ 未在列表中找到"

# ── 6. 完成 ──────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo " ✅ 安装完成！"
echo ""
echo " 定时任务：每天 07:30（早市）/ 12:10（午市）/ 17:00（晚市）"
echo " 报告目录：$BASE_DIR/reports/"
echo " 日志目录：$BASE_DIR/logs/"
echo ""
echo " 手动触发：launchctl start com.huigu.astock-analysis"
echo " 手动测试：python3 $SCRIPT_DIR/run_daily.py --session morning"
echo " 查看日志：tail -f $BASE_DIR/logs/launchd.log"
echo " 卸载任务：launchctl unload $PLIST_DST"
echo "═══════════════════════════════════════════"
