#!/usr/bin/env bash
# setup.sh —— Huigu-AI 一键安装脚本
# 用法：bash setup.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL="git@github.com:berming/Huigu-AI.git"
PLIST_SRC="$SCRIPT_DIR/com.huigu.astock-daily.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.huigu.astock-daily.plist"

echo "═══════════════════════════════════════════"
echo " Huigu-AI A股日报 · 自动存档系统 · 安装脚本"
echo "═══════════════════════════════════════════"
echo ""

# ── 1. 检查依赖 ──────────────────────────────
echo "▶ 检查依赖..."
command -v python3 >/dev/null || { echo "❌ 未找到 python3"; exit 1; }
command -v git     >/dev/null || { echo "❌ 未找到 git";     exit 1; }
PYTHON=$(command -v python3)
GIT=$(command -v git)
echo "  python3: $PYTHON"
echo "  git:     $GIT"

# ── 2. 检查 SSH key ───────────────────────────
echo ""
echo "▶ 测试 GitHub SSH 连通性..."
if ssh -T -o ConnectTimeout=6 -o StrictHostKeyChecking=no git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo "  ✅ SSH Key 已配置，GitHub 连通"
else
    echo "  ⚠️  SSH 连通测试未通过（可能是首次，继续安装...）"
    echo "  若 push 失败，请执行：ssh-keygen -t ed25519 && cat ~/.ssh/id_ed25519.pub"
    echo "  然后将公钥添加到：https://github.com/settings/keys"
fi

# ── 3. 确认项目路径 ───────────────────────────
echo ""
echo "▶ 项目路径: $SCRIPT_DIR"
mkdir -p "$SCRIPT_DIR/reports" "$SCRIPT_DIR/logs"

# ── 4. 修改 plist 中的路径 ────────────────────
echo ""
echo "▶ 配置 launchd plist..."
ESCAPED_DIR=$(echo "$SCRIPT_DIR" | sed 's|/|\\/|g')
ESCAPED_PY=$(echo "$PYTHON" | sed 's|/|\\/|g')

# 替换 plist 中的占位符
sed -e "s/\/Users\/YOUR_USERNAME\/huigu-reporter\/scripts\/run_daily.py/${ESCAPED_DIR}\/scripts\/run_daily.py/g" \
    -e "s/\/Users\/YOUR_USERNAME\/huigu-reporter/${ESCAPED_DIR}/g" \
    -e "s/\/usr\/bin\/python3/${ESCAPED_PY}/g" \
    "$PLIST_SRC" > "$PLIST_DST"
echo "  ✅ plist 已写入: $PLIST_DST"

# ── 5. 加载 launchd ───────────────────────────
echo ""
echo "▶ 加载 launchd 任务..."
# 先卸载（如果已存在）
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"
echo "  ✅ 定时任务已加载"

# ── 6. 验证 ──────────────────────────────────
echo ""
echo "▶ 验证任务状态..."
launchctl list | grep "huigu" || echo "  ⚠️  未在列表中找到，请检查 plist"

# ── 7. 立即试跑一次 ───────────────────────────
echo ""
read -p "▶ 是否立即试跑一次（测试完整流程）? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  运行中，请稍候..."
    python3 "$SCRIPT_DIR/scripts/run_daily.py" || true
fi

echo ""
echo "═══════════════════════════════════════════"
echo " ✅ 安装完成！"
echo ""
echo " 定时任务：每天 12:00（午间） 和 17:00（每日收盘）各自动运行一次"
echo " 报告目录：$SCRIPT_DIR/reports/"
echo "         文件名示例：astock_YYYYMMDD_1200.html / astock_YYYYMMDD_1700.html"
echo " 日志目录：$SCRIPT_DIR/logs/"
echo ""
echo " 手动触发：launchctl start com.huigu.astock-daily"
echo "        （按当前时间自动识别 session，也可：python3 scripts/run_daily.py --session noon|daily）"
echo " 查看日志：tail -f $SCRIPT_DIR/logs/launchd_stderr.log"
echo " 卸载任务：launchctl unload $PLIST_DST"
echo "═══════════════════════════════════════════"
