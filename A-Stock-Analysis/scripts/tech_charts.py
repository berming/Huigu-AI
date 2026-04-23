"""
Technical indicator chart rendering (MACD, BOLL, KDJ).
Returns dict of base64 PNG strings.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import base64, io, statistics


def get_font():
    """Get a suitable CJK font."""
    font_paths = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for fp in font_paths:
        try:
            return fm.FontProperties(fname=fp)
        except Exception:
            pass
    return fm.FontProperties()


def ema(data, period):
    k = 2.0 / (period + 1)
    result = [data[0]]
    for v in data[1:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def savefig(fig):
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=90, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return b64


def _setup_axes(fig, nrows=1):
    """Apply common styling to axes."""
    plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.3
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False


def render_tech_charts(df):
    """
    df: pandas DataFrame with columns [date, open, high, low, close, volume, amount, pctChg]
    Returns dict: {"macd": b64_png_str, "boll": b64_png_str, "kdj": b64_png_str}
    """
    result = {}
    font = get_font()

    if df is None or len(df) < 30:
        return result

    closes = df["close"].astype(float).tolist()
    highs  = df["high"].astype(float).tolist()
    lows   = df["low"].astype(float).tolist()
    vols   = df["volume"].astype(float).tolist()
    n = len(closes)

    _setup_axes(plt)

    # ══════════════════════════════════════════════════════════
    # 1. MACD Chart
    # ══════════════════════════════════════════════════════════
    if n >= 26:
        e12 = ema(closes, 12)
        e26 = ema(closes, 26)
        dif = [e12[i] - e26[i] for i in range(len(e26))]
        sig = ema(dif, 9)
        # align dif and sig
        dif_s = dif[-len(sig):]
        hist = [dif_s[i] - sig[i] for i in range(len(sig))]

        x_price = np.arange(n)
        x_macd  = np.arange(len(dif_s))

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 4.5),
                                        gridspec_kw={"height_ratios": [3, 1]})
        fig.suptitle("MACD (12,26,9)", fontproperties=font, fontsize=11, fontweight="bold", y=0.98)

        # Price line
        ax1.plot(x_price[-90:], closes[-90:], color="#444", linewidth=1.4, label="收盘价")
        ax1.set_ylabel("价格", fontsize=9)
        ax1.tick_params(labelsize=8)
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)
        ax1.grid(alpha=0.3)

        # MACD histogram + lines
        bar_colors = ["#dc2626" if h >= 0 else "#16a34a" for h in hist[-90:]]
        ax2.bar(x_macd[-90:], hist[-90:], color=bar_colors, width=0.7, alpha=0.85)
        ax2.axhline(0, color="gray", linewidth=0.5)
        ax2.plot(x_macd[-90:], dif_s[-90:], color="#2563eb", linewidth=1.2, label="DIF")
        ax2.plot(x_macd[-90:], sig[-90:], color="#f59e0b", linewidth=1.2, label="DEA")
        ax2.set_ylabel("MACD", fontsize=9)
        ax2.set_xlabel("交易日", fontsize=9)
        ax2.tick_params(labelsize=8)
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)
        ax2.grid(alpha=0.3)

        fig.tight_layout()
        result["macd"] = savefig(fig)

    # ══════════════════════════════════════════════════════════
    # 2. Bollinger Bands Chart
    # ══════════════════════════════════════════════════════════
    if n >= 20:
        ma20_list, upper_list, lower_list = [], [], []
        for i in range(19, n):
            win = closes[i-19:i+1]
            m = statistics.mean(win)
            s = statistics.pstdev(win)
            ma20_list.append(m)
            upper_list.append(m + 2 * s)
            lower_list.append(m - 2 * s)

        offset = n - len(ma20_list)
        x = np.arange(len(ma20_list))

        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.fill_between(x, lower_list, upper_list, alpha=0.12, color="#6366f1", label="布林带(20,2)")
        ax.plot(x, closes[offset:], color="#444", linewidth=1.4, label="收盘价")
        ax.plot(x, ma20_list, color="#6366f1", linewidth=1.2, linestyle="--", label="MA20")
        ax.plot(x, upper_list, color="#6366f1", linewidth=0.7, linestyle=":", alpha=0.6)
        ax.plot(x, lower_list, color="#6366f1", linewidth=0.7, linestyle=":", alpha=0.6)

        lc = closes[-1]; lu = upper_list[-1]; ll = lower_list[-1]; lm = ma20_list[-1]
        ax.axhline(lu, color="#dc2626", linewidth=0.6, linestyle="--", alpha=0.4)
        ax.axhline(ll, color="#16a34a", linewidth=0.6, linestyle="--", alpha=0.4)
        ax.axhline(lm, color="#6366f1", linewidth=0.6, linestyle="--", alpha=0.4)

        ax.set_title(f"BOLL(20,2)  上轨{lu:.2f} / 中轨{lm:.2f} / 下轨{ll:.2f}  |  收盘{lc:.2f}",
                     fontproperties=font, fontsize=10, fontweight="bold")
        ax.set_xlabel("交易日", fontsize=9)
        ax.set_ylabel("价格", fontsize=9)
        ax.tick_params(labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        result["boll"] = savefig(fig)

    # ══════════════════════════════════════════════════════════
    # 3. KDJ Chart
    # ══════════════════════════════════════════════════════════
    if n >= 9:
        kvals, dvals = [50.0], [50.0]
        for i in range(9, n + 1):
            wl = min(lows[i-9:i]); wh = max(highs[i-9:i])
            rsv = (closes[i-1] - wl) / (wh - wl) * 100.0 if wh != wl else 50.0
            kvals.append(kvals[-1] * 2/3 + rsv / 3)
        for kv in kvals[1:]:
            dvals.append(dvals[-1] * 2/3 + kv / 3)
        jvals = [3 * kvals[i] - 2 * dvals[i] for i in range(len(kvals))]

        xk = np.arange(len(kvals))

        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.axhline(80, color="#dc2626", linewidth=0.8, linestyle="--", alpha=0.5, label="超买线(80)")
        ax.axhline(20, color="#16a34a", linewidth=0.8, linestyle="--", alpha=0.5, label="超卖线(20)")
        ax.plot(xk, kvals, color="#2563eb", linewidth=1.5, label="K")
        ax.plot(xk, dvals, color="#f59e0b", linewidth=1.5, label="D")
        ax.plot(xk, jvals, color="#7c3aed", linewidth=1.2, linestyle="-.", label="J", alpha=0.75)
        ax.fill_between(xk, 80, 110, alpha=0.04, color="#dc2626")
        ax.fill_between(xk, -10, 20, alpha=0.04, color="#16a34a")

        lk = kvals[-1]; ld = dvals[-1]; lj = jvals[-1]
        ax.set_title(f"KDJ(9,3,3)  K={lk:.1f}  D={ld:.1f}  J={lj:.1f}",
                     fontproperties=font, fontsize=10, fontweight="bold")
        ax.set_xlabel("交易日", fontsize=9)
        ax.set_ylabel("KDJ", fontsize=9)
        ax.tick_params(labelsize=8)
        ax.set_ylim(-5, 115)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        result["kdj"] = savefig(fig)

    return result
