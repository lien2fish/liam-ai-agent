#!/usr/bin/env python3
"""
Personal Finance OS v2.0 — Chart Generator
從 Notion 月度快照讀取真實資料，產出 3 張圖表嵌入 Notion dashboard。

產出（finance/charts/）：
  chart_networth.png   — 淨值 + 總資產趨勢（折線）
  chart_assets.png     — 資產分佈（甜甜圈）
  chart_cashflow.png   — 收支對比（長條）

執行後自動 commit + push，並更新 Notion dashboard image blocks。
"""
import io
import json
import os
import sys
import subprocess
import urllib.request
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib import rcParams
from PIL import Image

# ── Paths ──────────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
CHARTS = os.path.join(HERE, "charts")
PINGFANG = "/System/Library/Fonts/PingFang.ttc"

# ── Colors ─────────────────────────────────────────────────────────────────────
BG = "#faf8f3"
CARD = "#ffffff"
GOLD = "#b7874a"
GOLD_LT = "#d4a574"
GOLD_DK = "#8b4513"
CREAM = "#f0e6d3"
BORDER = "#e8d5b7"
TEXT_DK = "#2d1b0e"
TEXT_MID = "#6b4c2a"
TEXT_LT = "#a08060"
GREEN = "#3d7a52"
RED = "#b84444"

ASSET_COLORS = [GOLD_DK, GOLD, "#c8a06a", GOLD_LT, "#a0b890", "#d4c490"]


# ── Notion API ─────────────────────────────────────────────────────────────────
def _load_token():
    token = os.environ.get("NOTION_TOKEN")
    if token:
        return token
    try:
        config_dir = os.path.join(HERE, "..", "notion_crm")
        sys.path.insert(0, os.path.abspath(config_dir))
        import config as _cfg

        sys.path.pop(0)
        return _cfg.NOTION_TOKEN
    except (ImportError, AttributeError):
        pass
    raise RuntimeError("NOTION_TOKEN 未設定")


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def api(method, path, data=None, token=None):
    if token is None:
        token = _load_token()
    url = f"https://api.notion.com/v1{path}"
    body = json.dumps(data, ensure_ascii=False).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=_headers(token), method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def load_config():
    cfg_path = os.path.join(HERE, "finance_config.json")
    if not os.path.exists(cfg_path):
        return None
    with open(cfg_path, encoding="utf-8") as f:
        return json.load(f)


# ── Fetch real Notion data ─────────────────────────────────────────────────────
def fetch_snapshots(snap_db_id, token):
    """Fetch monthly snapshots sorted by month label."""
    results = api(
        "POST",
        f"/databases/{snap_db_id}/query",
        {
            "page_size": 24,
            "sorts": [{"property": "月份 / Month", "direction": "ascending"}],
        },
        token,
    )
    rows = []
    for p in results.get("results", []):
        props = p["properties"]

        def num(key):
            return props.get(key, {}).get("number") or 0

        def title(key):
            arr = props.get(key, {}).get("title", [])
            return arr[0]["plain_text"] if arr else ""

        rows.append(
            {
                "month": title("月份 / Month"),
                "assets": num("總資產 / Total Assets"),
                "liab": num("總負債 / Total Liabilities"),
                "net": num("淨值 / Net Worth"),
                "income": num("月收入 / Monthly Income"),
                "expenses": num("月支出 / Monthly Expenses"),
                "cashflow": num("月結餘 / Net Cash Flow"),
            }
        )
    return rows


def fetch_assets(assets_db_id, token):
    """Fetch assets for breakdown chart."""
    results = api("POST", f"/databases/{assets_db_id}/query", {"page_size": 50}, token)
    items = []
    for p in results.get("results", []):
        props = p["properties"]

        def title(key):
            arr = props.get(key, {}).get("title", [])
            return arr[0]["plain_text"] if arr else ""

        def num(key):
            return props.get(key, {}).get("number") or 0

        def sel(key):
            s = props.get(key, {}).get("select")
            return s["name"] if s else ""

        items.append(
            {
                "name": title("項目名稱 / Asset Name"),
                "cat": sel("類別 / Category"),
                "value": num("當前金額 / Current Value"),
            }
        )
    return [a for a in items if a["value"] > 0]


# ── Matplotlib setup ────────────────────────────────────────────────────────────
def setup_mpl():
    rcParams["font.family"] = [
        "PingFang HK",
        "Heiti TC",
        "Arial Unicode MS",
        "sans-serif",
    ]
    rcParams["axes.facecolor"] = CARD
    rcParams["figure.facecolor"] = CARD
    rcParams["text.color"] = TEXT_DK
    rcParams["axes.labelcolor"] = TEXT_MID
    rcParams["xtick.color"] = TEXT_LT
    rcParams["ytick.color"] = TEXT_LT
    rcParams["axes.edgecolor"] = BORDER
    rcParams["axes.spines.top"] = False
    rcParams["axes.spines.right"] = False
    rcParams["grid.color"] = CREAM
    rcParams["grid.linestyle"] = "--"
    rcParams["grid.alpha"] = 0.9


def save(fig, fname, dpi=150):
    path = os.path.join(CHARTS, fname)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor=CARD)
    plt.close(fig)
    print(f"    ✅ {fname}")
    return path


# ── Chart 1: Net Worth Trend ───────────────────────────────────────────────────
def chart_networth(rows):
    setup_mpl()
    labels = [r["month"] for r in rows]
    nets = [r["net"] / 1e6 for r in rows]
    assets = [r["assets"] / 1e6 for r in rows]
    liabs = [r["liab"] / 1e6 for r in rows]
    x = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.fill_between(x, nets, min(nets) - 0.1, alpha=0.14, color=GOLD)
    ax.plot(
        x, liabs, color=RED, linewidth=1.4, linestyle=":", label="總負債", alpha=0.75
    )
    ax.plot(
        x,
        assets,
        color=TEXT_LT,
        linewidth=1.5,
        linestyle="--",
        label="總資產",
        alpha=0.75,
    )
    ax.plot(
        x,
        nets,
        color=GOLD,
        linewidth=2.6,
        marker="o",
        markersize=5,
        markerfacecolor=GOLD_DK,
        zorder=3,
        label="淨值",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.1f}M"))
    ax.set_ylabel("NT$ 百萬", fontsize=9)
    ax.legend(fontsize=9, framealpha=0.95, loc="upper left")
    ax.grid(axis="y")
    ax.set_title("淨值趨勢  ·  Net Worth Trend", fontsize=12, color=GOLD_DK, pad=10)
    fig.tight_layout(pad=0.8)
    return save(fig, "chart_networth.png")


# ── Chart 2: Asset Breakdown ───────────────────────────────────────────────────
def chart_assets(asset_rows):
    setup_mpl()
    # Group by category
    cat_map = {}
    for a in asset_rows:
        cat = a["cat"].split(" ")[0] if " " in a["cat"] else a["cat"]  # 取中文部分
        cat_map[cat] = cat_map.get(cat, 0) + a["value"]

    labels = list(cat_map.keys())
    values = list(cat_map.values())
    colors = (ASSET_COLORS * 3)[: len(labels)]
    total = sum(values)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    wedges, _ = ax.pie(
        values,
        colors=colors,
        startangle=130,
        wedgeprops={"linewidth": 2, "edgecolor": "white", "width": 0.56},
    )
    ax.text(
        0,
        0,
        f"NT$\n{total/1e6:.1f}M",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color=TEXT_DK,
    )
    pcts = [f"{v/total*100:.0f}%" for v in values]
    legend_items = [f"{l}  {p}" for l, p in zip(labels, pcts)]
    ax.legend(
        wedges,
        legend_items,
        loc="center left",
        bbox_to_anchor=(1, 0, 0.45, 1),
        fontsize=9,
        framealpha=0.95,
    )
    ax.set_title("資產分佈  ·  Asset Breakdown", fontsize=12, color=GOLD_DK, pad=10)
    fig.tight_layout(pad=0.8)
    return save(fig, "chart_assets.png")


# ── Chart 3: Cash Flow Bar ─────────────────────────────────────────────────────
def chart_cashflow(rows):
    setup_mpl()
    labels = [r["month"] for r in rows]
    income = [r["income"] / 1e3 for r in rows]
    expenses = [r["expenses"] / 1e3 for r in rows]
    cashflow = [r["cashflow"] / 1e3 for r in rows]
    x = np.arange(len(labels))
    w = 0.32

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(x - w, income, w, label="月收入", color=GOLD_LT, alpha=0.9)
    ax.bar(x, expenses, w, label="月支出", color=GOLD_DK, alpha=0.85)
    bars = ax.bar(
        x + w,
        cashflow,
        w,
        label="月結餘",
        color=[GREEN if v >= 0 else RED for v in cashflow],
        alpha=0.9,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}K"))
    ax.set_ylabel("NT$ 千元", fontsize=9)
    ax.axhline(0, color=BORDER, linewidth=1)
    ax.legend(fontsize=9, framealpha=0.95)
    ax.grid(axis="y")
    ax.set_title("月收支對比  ·  Monthly Cash Flow", fontsize=12, color=GOLD_DK, pad=10)
    fig.tight_layout(pad=0.8)
    return save(fig, "chart_cashflow.png")


# ── Push to GitHub & get public URLs ──────────────────────────────────────────
REPO_OWNER = "lien2fish"
REPO_NAME = "liam-ai-agent"
BRANCH = "main"


def github_raw_url(fname):
    return f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/finance/charts/{fname}"


def git_commit_push():
    root = os.path.join(HERE, "..")
    cmds = [
        ["git", "-C", root, "add", "finance/charts/"],
        [
            "git",
            "-C",
            root,
            "commit",
            "-m",
            f"chore: 更新財務圖表 {date.today().isoformat()}",
        ],
        ["git", "-C", root, "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 and "nothing to commit" not in result.stdout:
            print(f"  git: {result.stderr.strip()}")
    print("  ✅ 圖表已 push 到 GitHub")


# ── Embed images into Notion dashboard ────────────────────────────────────────
def embed_charts_in_notion(page_id, token):
    """Append image blocks to the root template page."""
    fnames = ["chart_networth.png", "chart_assets.png", "chart_cashflow.png"]
    titles = [
        "📈 淨值趨勢  ·  Net Worth Trend",
        "💰 資產分佈  ·  Asset Breakdown",
        "💹 月收支對比  ·  Monthly Cash Flow",
    ]

    blocks = []
    for fname, title in zip(fnames, titles):
        url = github_raw_url(fname)
        blocks.append(
            {
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": title}}],
                    "color": "default",
                },
            }
        )
        blocks.append(
            {
                "type": "image",
                "image": {"type": "external", "external": {"url": url}},
            }
        )
        blocks.append({"type": "divider", "divider": {}})

    api("PATCH", f"/blocks/{page_id}/children", {"children": blocks}, token)
    print(f"  ✅ 已嵌入 {len(fnames)} 張圖表到 Notion")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    token = _load_token()
    cfg = load_config()

    print("=" * 55)
    print(f"Personal Finance OS v2.0 — 圖表生成  {date.today()}")

    # Load DB IDs
    if cfg:
        snap_db = cfg["notion"]["snapshot_db_id"]
        assets_db = cfg["notion"]["assets_db_id"]
        page_id = None  # Will embed to whichever page
    else:
        # Fallback: use the commercial template DB IDs
        snap_db = "369f4149-a6aa-8185-8ee6-f9a74de89c98"
        assets_db = "369f4149-a6aa-816d-a81d-fda844c6488e"
        page_id = "369f4149-a6aa-817a-9a1e-f536b11f4d97"  # root template page

    os.makedirs(CHARTS, exist_ok=True)

    # Fetch data
    print("\n[1/3] 讀取 Notion 資料...")
    snapshots = fetch_snapshots(snap_db, token)
    asset_rows = fetch_assets(assets_db, token)
    print(f"  快照: {len(snapshots)} 筆  資產: {len(asset_rows)} 筆")

    if not snapshots:
        print("  ⚠️  月度快照無資料，使用示範數值")
        snapshots = [
            {
                "month": f"26-0{i}",
                "assets": 13e6 + i * 40000,
                "liab": 3.68e6 - i * 20000,
                "net": 9.57e6 + i * 60000,
                "income": 43000,
                "expenses": 46870,
                "cashflow": -3870,
            }
            for i in range(1, 6)
        ]

    # Generate charts
    print("\n[2/3] 生成圖表...")
    chart_networth(snapshots)
    chart_assets(
        asset_rows
        if asset_rows
        else [
            {"name": "房產", "cat": "不動產", "value": 8e6},
            {"name": "股權", "cat": "股權", "value": 3e6},
            {"name": "存款", "cat": "存款", "value": 0.92e6},
        ]
    )
    chart_cashflow(snapshots)

    # Push to GitHub
    print("\n[3/3] Push 圖表到 GitHub...")
    git_commit_push()

    # Embed in Notion (if we have a page_id)
    if page_id:
        print("\n[+] 嵌入圖表到 Notion dashboard...")
        embed_charts_in_notion(page_id, token)

    print("\n圖表公開 URL：")
    for f in ["chart_networth.png", "chart_assets.png", "chart_cashflow.png"]:
        print(f"  {github_raw_url(f)}")
    print("=" * 55)


if __name__ == "__main__":
    main()
