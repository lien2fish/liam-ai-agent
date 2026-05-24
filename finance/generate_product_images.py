#!/usr/bin/env python3
"""
Personal Finance OS v2.0 — Product Image Generator
生成 Gumroad 商品展示圖（暖金色系）

產出 3 張 1400×800 PNG：
  product_01_hero.png    — 儀表板總覽
  product_02_charts.png  — 圖表展示
  product_03_features.png — 功能亮點
"""
import io
import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ── Paths ──────────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "product_images")
PINGFANG = "/System/Library/Fonts/PingFang.ttc"

# ── Color palette ──────────────────────────────────────────────────────────────
BG = "#faf8f3"
GOLD = "#b7874a"
GOLD_LT = "#d4a574"
GOLD_DARK = "#8b4513"
CREAM = "#f0e6d3"
CARD = "#ffffff"
TEXT_DARK = "#2d1b0e"
TEXT_MID = "#6b4c2a"
TEXT_LIGHT = "#a08060"
BORDER = "#e8d5b7"
GREEN = "#3d7a52"
RED = "#b84444"

W, H = 1400, 800


# ── Font ───────────────────────────────────────────────────────────────────────
def font(size, idx=0):
    """PingFang HK — CJK + Latin + common symbols"""
    try:
        return ImageFont.truetype(PINGFANG, size, index=idx)
    except Exception:
        return ImageFont.load_default()


# ── Drawing helpers ─────────────────────────────────────────────────────────────
def rounded_rect(draw, xy, radius=14, fill=CARD, outline=BORDER, width=1):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(
        [x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=width
    )


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def draw_icon_circle(draw, cx, cy, r, char, bg, fg=None):
    """Filled circle with a single CJK character — no emoji needed."""
    if fg is None:
        fg = CARD
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg)
    draw.text((cx, cy), char, font=font(r), fill=fg, anchor="mm")


def make_gradient_bar(draw, y0, y1, w):
    """Horizontal gold gradient bar."""
    for x in range(w):
        t = x / w
        r = int(139 + t * (183 - 139))
        g = int(69 + t * (135 - 69))
        b = int(19 + t * (74 - 19))
        draw.line([(x, y0), (x, y1)], fill=(r, g, b))


# ── Matplotlib ──────────────────────────────────────────────────────────────────
def setup_mpl():
    rcParams["font.family"] = [
        "PingFang HK",
        "Heiti TC",
        "Arial Unicode MS",
        "sans-serif",
    ]
    rcParams["axes.facecolor"] = CARD
    rcParams["figure.facecolor"] = "none"
    rcParams["text.color"] = TEXT_DARK
    rcParams["axes.labelcolor"] = TEXT_MID
    rcParams["xtick.color"] = TEXT_LIGHT
    rcParams["ytick.color"] = TEXT_LIGHT
    rcParams["axes.edgecolor"] = BORDER
    rcParams["axes.spines.top"] = False
    rcParams["axes.spines.right"] = False
    rcParams["grid.color"] = CREAM
    rcParams["grid.linestyle"] = "--"
    rcParams["grid.alpha"] = 0.8


def fig_to_pil(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=144, bbox_inches="tight", transparent=True)
    buf.seek(0)
    return Image.open(buf).copy()


# ── Data ────────────────────────────────────────────────────────────────────────
MONTHS = ["25-10", "25-11", "25-12", "26-01", "26-02", "26-03", "26-04", "26-05"]
NET_WORTH = [9.57, 9.63, 9.69, 9.75, 9.81, 9.87, 9.93, 9.99]
TOTAL_ASSETS = [13.25, 13.29, 13.33, 13.37, 13.41, 13.45, 13.49, 13.53]

ASSET_LABELS = ["不動產", "公司股權", "銀行存款", "保單", "ETF", "黃金"]
ASSET_VALUES = [8.0, 3.0, 0.92, 0.60, 0.45, 0.28]
ASSET_COLORS = [GOLD_DARK, GOLD, "#c8a06a", GOLD_LT, "#a0b890", "#d4c490"]


# ══════════════════════════════════════════════════════════════════════════════
# IMAGE 1 — Hero Dashboard
# ══════════════════════════════════════════════════════════════════════════════

# icon char / label_zh / label_en / value / value_color / tag / icon_bg
METRICS_R1 = [
    ("淨", "淨資產", "Net Worth", "NT$ 9,990,000", GREEN, "趨勢 ↑", GREEN),
    ("資", "總資產", "Total Assets", "NT$ 13,530,000", TEXT_DARK, None, GOLD),
    ("債", "總負債", "Total Liabilities", "NT$ 3,540,000", RED, "趨勢 ↓", RED),
]
METRICS_R2 = [
    ("率", "儲蓄率", "Savings Rate", "-8.99%  →  待補齊", TEXT_MID, None, GOLD_LT),
    (
        "自",
        "自動更新",
        "Auto-Updated",
        "每月 1 日 08:00",
        GOLD_DARK,
        "GitHub Actions",
        GOLD_DARK,
    ),
    (
        "填",
        "手動待填",
        "Manual Fields",
        "佣金  ·  日常生活費",
        TEXT_MID,
        None,
        TEXT_LIGHT,
    ),
]


def draw_metric_card(
    draw,
    x0,
    y0,
    x1,
    y1,
    icon_char,
    label_zh,
    label_en,
    value,
    value_color,
    tag,
    icon_bg,
):
    rounded_rect(draw, [x0, y0, x1, y1], radius=12, fill=CARD, outline=BORDER)
    # Gold left-edge accent
    draw.rounded_rectangle([x0, y0, x0 + 4, y1], radius=2, fill=GOLD)
    # Icon circle
    draw_icon_circle(draw, x0 + 34, y0 + 32, 20, icon_char, icon_bg)
    cx = (x0 + x1) // 2
    # Tag badge
    if tag:
        tw = draw.textlength(tag, font=font(10))
        tx0 = int(x1 - tw - 22)
        draw.rounded_rectangle([tx0, y0 + 10, x1 - 10, y0 + 30], radius=8, fill=CREAM)
        draw.text(
            (x1 - 10 - (tw / 2) - 6, y0 + 20),
            tag,
            font=font(10),
            fill=GOLD_DARK,
            anchor="mm",
        )
    # Labels
    draw.text((cx, y0 + 56), label_zh, font=font(13), fill=TEXT_MID, anchor="mm")
    draw.text((cx, y0 + 72), label_en, font=font(11), fill=TEXT_LIGHT, anchor="mm")
    # Value
    draw.text((cx, y0 + 98), value, font=font(19), fill=value_color, anchor="mm")


def make_net_worth_chart(width, height):
    setup_mpl()
    fig, ax = plt.subplots(figsize=(width / 144, height / 144))
    x = np.arange(len(MONTHS))
    ax.fill_between(x, NET_WORTH, min(NET_WORTH) - 0.08, alpha=0.18, color=GOLD)
    ax.plot(
        x,
        NET_WORTH,
        color=GOLD,
        linewidth=2.6,
        marker="o",
        markersize=5,
        markerfacecolor=GOLD_DARK,
        zorder=3,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(MONTHS, fontsize=9)
    ax.set_ylabel("NT$ 百萬", fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.2f}M"))
    ax.grid(axis="y")
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)
    fig.tight_layout(pad=0.5)
    pil = fig_to_pil(fig)
    plt.close(fig)
    return pil


def image_01_hero():
    print("  生成 product_01_hero.png ...")
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    make_gradient_bar(draw, 0, 58, W)
    draw.text(
        (W // 2, 19),
        "Personal Finance OS  ·  個人財務作業系統",
        font=font(21),
        fill="#fff5e6",
        anchor="mm",
    )
    draw.text(
        (W // 2, 44),
        "v2.0  ·  雙語  ·  GitHub Actions 自動更新  ·  Bilingual Auto-Updated",
        font=font(12),
        fill="#f0d8b0",
        anchor="mm",
    )

    CARD_W, CARD_H = 420, 118
    GAP = 20
    SX = (W - (CARD_W * 3 + GAP * 2)) // 2
    Y1 = 68

    for i, m in enumerate(METRICS_R1):
        x0 = SX + i * (CARD_W + GAP)
        draw_metric_card(draw, x0, Y1, x0 + CARD_W, Y1 + CARD_H, *m)

    Y2 = Y1 + CARD_H + 10
    for i, m in enumerate(METRICS_R2):
        x0 = SX + i * (CARD_W + GAP)
        draw_metric_card(draw, x0, Y2, x0 + CARD_W, Y2 + CARD_H, *m)

    CHART_Y = Y2 + CARD_H + 14
    CHART_H = H - CHART_Y - 42
    CW = CARD_W * 3 + GAP * 2

    draw.rounded_rectangle(
        [SX, CHART_Y, SX + CW, CHART_Y + CHART_H], radius=12, fill=BG, outline=BORDER
    )
    draw.text(
        (SX + 18, CHART_Y + 14),
        "淨值趨勢  ·  Net Worth Trend (NT$ 百萬)",
        font=font(13),
        fill=GOLD_DARK,
        anchor="lm",
    )

    chart = make_net_worth_chart(CW - 32, CHART_H - 34)
    chart = chart.resize((CW - 32, CHART_H - 34), Image.LANCZOS)
    img.paste(chart, (SX + 16, CHART_Y + 28), chart if chart.mode == "RGBA" else None)

    draw.rectangle([0, H - 36, W, H], fill=GOLD_DARK)
    draw.text(
        (W // 2, H - 18),
        "Personal Finance OS v2.0  ·  台灣企業主 / 管理顧問專屬設計  ·  Available on Gumroad",
        font=font(12),
        fill="#f5e0c0",
        anchor="mm",
    )

    img.save(os.path.join(OUT, "product_01_hero.png"), dpi=(144, 144))
    print("    ✅ product_01_hero.png")


# ══════════════════════════════════════════════════════════════════════════════
# IMAGE 2 — Charts Showcase
# ══════════════════════════════════════════════════════════════════════════════


def make_trend_chart(width, height):
    setup_mpl()
    fig, ax = plt.subplots(figsize=(width / 144, height / 144))
    x = np.arange(len(MONTHS))
    ax.fill_between(x, NET_WORTH, min(NET_WORTH) - 0.2, alpha=0.15, color=GOLD)
    ax.plot(
        x,
        TOTAL_ASSETS,
        color="#a0b890",
        linewidth=1.5,
        linestyle="--",
        label="總資產",
        alpha=0.7,
    )
    ax.plot(
        x,
        NET_WORTH,
        color=GOLD,
        linewidth=2.8,
        marker="o",
        markersize=6,
        markerfacecolor=GOLD_DARK,
        label="淨值",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(MONTHS, fontsize=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}M"))
    ax.set_ylabel("NT$ 百萬", fontsize=10)
    ax.legend(fontsize=10, framealpha=0.9, loc="upper left")
    ax.grid(axis="y")
    ax.set_facecolor(CARD)
    fig.patch.set_facecolor("none")
    fig.tight_layout(pad=0.5)
    pil = fig_to_pil(fig)
    plt.close(fig)
    return pil


def make_donut_chart(size):
    """Donut chart — labels outside, cleaner than pie."""
    setup_mpl()
    fig, ax = plt.subplots(figsize=(size / 144, size / 144))
    total = sum(ASSET_VALUES)
    pcts = [v / total * 100 for v in ASSET_VALUES]
    wedges, _ = ax.pie(
        ASSET_VALUES,
        colors=ASSET_COLORS,
        startangle=130,
        wedgeprops={"linewidth": 2, "edgecolor": "white", "width": 0.6},
    )
    # Center text
    ax.text(
        0,
        0,
        f"NT$\n{total:.1f}M",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color=TEXT_DARK,
    )
    # Legend instead of labels to avoid crowding
    legend_items = [f"{lbl}  {pct:.0f}%" for lbl, pct in zip(ASSET_LABELS, pcts)]
    ax.legend(
        wedges,
        legend_items,
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=9,
        framealpha=0.9,
    )
    ax.set_facecolor("none")
    fig.patch.set_facecolor("none")
    fig.tight_layout(pad=0.3)
    pil = fig_to_pil(fig)
    plt.close(fig)
    return pil


def make_cashflow_bar(width, height):
    setup_mpl()
    fig, ax = plt.subplots(figsize=(width / 144, height / 144))
    income = [43000] * 8
    expenses = [46870] * 8
    x = np.arange(len(MONTHS))
    w = 0.36
    ax.bar(x - w / 2, income, w, label="月收入", color=GOLD_LT, alpha=0.9)
    ax.bar(x + w / 2, expenses, w, label="月支出", color=GOLD_DARK, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(MONTHS, fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v/1000)}K"))
    ax.set_ylabel("NT$", fontsize=10)
    ax.legend(fontsize=9, framealpha=0.9)
    ax.grid(axis="y")
    ax.set_facecolor(CARD)
    fig.patch.set_facecolor("none")
    fig.tight_layout(pad=0.5)
    pil = fig_to_pil(fig)
    plt.close(fig)
    return pil


def image_02_charts():
    print("  生成 product_02_charts.png ...")
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    make_gradient_bar(draw, 0, 58, W)
    draw.text(
        (W // 2, 19),
        "圖表展示  ·  Built-in Charts & Analytics",
        font=font(21),
        fill="#fff5e6",
        anchor="mm",
    )
    draw.text(
        (W // 2, 44),
        "Notion 原生圖表  ·  3 種視圖  ·  自動資料連動",
        font=font(12),
        fill="#f0d8b0",
        anchor="mm",
    )

    PAD = 22
    TOP = 68
    MID = W // 2 + 4

    # Left: Trend chart
    lw = MID - PAD * 2
    lh = H - TOP - PAD - 46
    draw.rounded_rectangle(
        [PAD, TOP, MID - PAD, H - PAD - 40], radius=12, fill=CARD, outline=BORDER
    )
    draw_icon_circle(draw, PAD + 26, TOP + 20, 14, "淨", GOLD_DARK)
    draw.text(
        (PAD + 46, TOP + 20),
        "淨值趨勢  ·  Net Worth Trend",
        font=font(13),
        fill=GOLD_DARK,
        anchor="lm",
    )
    trend = make_trend_chart(lw - 20, lh - 34)
    trend = trend.resize((lw - 20, lh - 34), Image.LANCZOS)
    img.paste(trend, (PAD + 10, TOP + 36), trend if trend.mode == "RGBA" else None)

    # Right-top: Donut
    rx0 = MID + PAD
    rw = W - rx0 - PAD
    half_h = (H - TOP - PAD - 46) // 2 - 6
    draw.rounded_rectangle(
        [rx0, TOP, W - PAD, TOP + half_h + 28], radius=12, fill=CARD, outline=BORDER
    )
    draw_icon_circle(draw, rx0 + 26, TOP + 20, 14, "資", GOLD)
    draw.text(
        (rx0 + 46, TOP + 20),
        "資產分佈  ·  Asset Breakdown",
        font=font(13),
        fill=GOLD_DARK,
        anchor="lm",
    )
    donut_size = min(rw - 20, half_h + 14)
    donut = make_donut_chart(donut_size)
    donut = donut.resize((rw - 20, half_h + 6), Image.LANCZOS)
    img.paste(donut, (rx0 + 10, TOP + 34), donut if donut.mode == "RGBA" else None)

    # Right-bottom: Bar
    bar_y0 = TOP + half_h + 38
    bar_h = H - PAD - 40 - bar_y0
    draw.rounded_rectangle(
        [rx0, bar_y0, W - PAD, H - PAD - 40], radius=12, fill=CARD, outline=BORDER
    )
    draw_icon_circle(draw, rx0 + 26, bar_y0 + 20, 14, "收", GOLD_DARK)
    draw.text(
        (rx0 + 46, bar_y0 + 20),
        "收支對比  ·  Income vs. Expenses",
        font=font(13),
        fill=GOLD_DARK,
        anchor="lm",
    )
    bar = make_cashflow_bar(rw - 20, bar_h - 28)
    bar = bar.resize((rw - 20, bar_h - 28), Image.LANCZOS)
    img.paste(bar, (rx0 + 10, bar_y0 + 34), bar if bar.mode == "RGBA" else None)

    draw.rectangle([0, H - 36, W, H], fill=GOLD_DARK)
    draw.text(
        (W // 2, H - 18),
        "Personal Finance OS v2.0  ·  Notion 原生圖表，無需額外工具",
        font=font(12),
        fill="#f5e0c0",
        anchor="mm",
    )

    img.save(os.path.join(OUT, "product_02_charts.png"), dpi=(144, 144))
    print("    ✅ product_02_charts.png")


# ══════════════════════════════════════════════════════════════════════════════
# IMAGE 3 — Features Grid
# ══════════════════════════════════════════════════════════════════════════════

FEATURES = [
    (
        "自",
        GOLD_DARK,
        "自動更新  ·  Auto-Update",
        ["GitHub Actions 每月 1 日執行", "黃金 / 信貸餘額自動計算", "Zero manual work"],
    ),
    (
        "圖",
        GOLD,
        "三大圖表  ·  3 Charts",
        ["淨值趨勢折線圖", "資產分佈圓餅圖", "收支對比長條圖"],
    ),
    (
        "語",
        GOLD_LT,
        "雙語介面  ·  Bilingual",
        ["繁體中文 + English", "所有欄位附英文標籤", "適合國際銷售"],
    ),
    (
        "資",
        GOLD_DARK,
        "6 大資產類別",
        ["不動產、股權、保單", "投資、黃金、存款", "完整 Select 標籤系統"],
    ),
    (
        "安",
        GOLD,
        "GitHub 安全託管",
        ["NOTION_TOKEN 環境變數", "無憑證寫入程式碼", "企業級安全標準"],
    ),
    (
        "雲",
        GOLD_LT,
        "隨時查看  ·  Anywhere",
        ["Notion Web / App 皆可", "自動 commit 執行記錄", "任何裝置即時同步"],
    ),
]


def draw_feature_card(draw, x0, y0, x1, y1, icon_char, icon_color, title, desc_lines):
    rounded_rect(draw, [x0, y0, x1, y1], radius=14, fill=CARD, outline=BORDER)
    # Gold top strip
    draw.rounded_rectangle([x0, y0, x1, y0 + 5], radius=3, fill=icon_color)
    # Icon circle
    draw_icon_circle(draw, x0 + 34, y0 + 38, 22, icon_char, icon_color)
    # Title
    draw.text((x0 + 66, y0 + 38), title, font=font(14), fill=TEXT_DARK, anchor="lm")
    # Divider
    draw.line([(x0 + 16, y0 + 62), (x1 - 16, y0 + 62)], fill=BORDER, width=1)
    # Description — evenly spaced in remaining card height
    total_h = y1 - y0 - 74
    line_h = total_h // (len(desc_lines) + 1)
    for i, line in enumerate(desc_lines):
        ty = y0 + 74 + (i + 1) * line_h - line_h // 2
        draw.text((x0 + 16, ty), line, font=font(13), fill=TEXT_MID, anchor="lm")


def image_03_features():
    print("  生成 product_03_features.png ...")
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    make_gradient_bar(draw, 0, 58, W)
    draw.text(
        (W // 2, 19),
        "核心功能  ·  Key Features",
        font=font(21),
        fill="#fff5e6",
        anchor="mm",
    )
    draw.text(
        (W // 2, 44),
        "6 大設計亮點  ·  Why Choose Personal Finance OS v2.0",
        font=font(12),
        fill="#f0d8b0",
        anchor="mm",
    )

    PAD = 22
    TOP = 68
    COLS, ROWS = 3, 2
    CARD_W = (W - PAD * (COLS + 1)) // COLS
    CARD_H = (H - TOP - PAD * (ROWS + 1) - 40) // ROWS

    for i, feat in enumerate(FEATURES):
        row, col = divmod(i, COLS)
        x0 = PAD + col * (CARD_W + PAD)
        y0 = TOP + PAD + row * (CARD_H + PAD)
        draw_feature_card(draw, x0, y0, x0 + CARD_W, y0 + CARD_H, *feat)

    draw.rectangle([0, H - 40, W, H], fill=GOLD_DARK)
    draw.text(
        (W // 2, H - 20),
        "Personal Finance OS v2.0  ·  NT$800-1,500  ·  一次購買，永久使用  ·  One-time purchase",
        font=font(12),
        fill="#f5e0c0",
        anchor="mm",
    )

    img.save(os.path.join(OUT, "product_03_features.png"), dpi=(144, 144))
    print("    ✅ product_03_features.png")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    print("Personal Finance OS v2.0 — 生成商品展示圖")
    print("=" * 50)
    image_01_hero()
    image_02_charts()
    image_03_features()
    print("=" * 50)
    print(f"✅ 完成！輸出目錄：{OUT}")
    print("   product_01_hero.png     — 儀表板總覽")
    print("   product_02_charts.png   — 圖表展示")
    print("   product_03_features.png — 功能亮點")
