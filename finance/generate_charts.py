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


# ── 股票即時股價 ───────────────────────────────────────────────────────────────
def fetch_stock_price(code: str):
    """從 Yahoo Finance 抓台股現價，先試 .TW 再試 .TWO。"""
    for suffix in [".TW", ".TWO"]:
        try:
            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/"
                f"{code}{suffix}?interval=1d&range=1d"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        except Exception:
            continue
    return None


def fetch_gold_price_twd():
    """黃金現價（TWD/克）= GC=F（USD/troy oz）× USD/TWD ÷ 31.1035"""

    def _yf(symbol: str):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        except Exception:
            return None

    gold_usd_oz = _yf("GC%3DF")  # GC=F
    usd_twd = _yf("USDTWD%3DX")  # USDTWD=X
    if gold_usd_oz and usd_twd:
        return round(gold_usd_oz * usd_twd / 31.1035, 1)
    return None


def _build_page_map(assets_db, token):
    """回傳 {asset_name: page_id} 對照表。"""
    rows = api("POST", f"/databases/{assets_db}/query", {"page_size": 50}, token)
    page_map = {}
    for row in rows.get("results", []):
        for v in row.get("properties", {}).values():
            if v.get("type") == "title" and v.get("title"):
                page_map[v["title"][0]["plain_text"]] = row["id"]
                break
    return page_map


def update_stock_prices(assets_db, cfg, token):
    """
    讀 finance_config.json 的 stocks 清單，
    抓即時股價後更新 Notion Assets DB（含成本 / Cost Basis → 報酬率自動計算）。
    """
    stocks = cfg.get("stocks", [])
    if not stocks:
        return {}

    today = date.today().isoformat()
    page_map = _build_page_map(assets_db, token)
    results = {}

    for stock in stocks:
        code = stock["code"]
        name = stock["name"]
        lots = stock["lots"]
        avg_cost = stock["avg_cost"]

        price = fetch_stock_price(code)
        if price is None:
            print(f"  ⚠️  {code} 股價取得失敗，略過")
            continue

        shares = lots * 1000
        current_val = round(price * shares)
        cost_val = round(avg_cost * shares)
        roi = round((price - avg_cost) / avg_cost * 100, 2)

        page_id = page_map.get(name)
        if page_id:
            api(
                "PATCH",
                f"/pages/{page_id}",
                {
                    "properties": {
                        "當前金額 / Current Value": {"number": current_val},
                        "成本 / Cost Basis": {"number": cost_val},
                        "上次更新 / Last Updated": {"date": {"start": today}},
                        "自動更新 / Auto Updated": {"checkbox": True},
                    }
                },
                token,
            )
            print(
                f"  📈 {name}：{price} × {shares}股 = NT${current_val:,}（{roi:+.2f}%）"
            )
        else:
            print(f"  ⚠️  {name} 在 Notion 找不到對應頁面，略過更新")

        results[code] = price

    return results


def update_gold_roi(assets_db, cfg, token):
    """
    抓即時黃金價格（TWD/克），計算黃金存摺 ROI 並寫回 Notion。
    需在 finance_config.json 的 gold_savings 設定 grams / avg_cost_per_gram。
    """
    gold_cfg = cfg.get("gold_savings", {})
    if not gold_cfg.get("enabled"):
        return

    grams = gold_cfg.get("grams")
    avg_cost = gold_cfg.get("avg_cost_per_gram")
    asset_name = gold_cfg.get("asset_name", "華南銀行黃金存摺")

    if not grams or not avg_cost:
        print("  ⚠️  黃金存摺：請在 finance_config.json 設定 grams 和 avg_cost_per_gram")
        return

    gold_twd = fetch_gold_price_twd()
    if not gold_twd:
        print("  ⚠️  黃金現價取得失敗，略過 ROI 更新")
        return

    current_val = round(gold_twd * grams)
    cost_val = round(avg_cost * grams)
    roi = round((gold_twd - avg_cost) / avg_cost * 100, 2)

    page_map = _build_page_map(assets_db, token)
    page_id = page_map.get(asset_name)
    if page_id:
        api(
            "PATCH",
            f"/pages/{page_id}",
            {
                "properties": {
                    "當前金額 / Current Value": {"number": current_val},
                    "成本 / Cost Basis": {"number": cost_val},
                    "上次更新 / Last Updated": {
                        "date": {"start": date.today().isoformat()}
                    },
                    "自動更新 / Auto Updated": {"checkbox": True},
                }
            },
            token,
        )
        print(
            f"  🥇 {asset_name}：TWD {gold_twd:,.0f}/g × {grams}g"
            f" = NT${current_val:,}（{roi:+.2f}%）"
        )
    else:
        print(f"  ⚠️  {asset_name} 在 Notion 找不到對應頁面，略過更新")


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
    import sys

    if sys.platform == "darwin":
        fonts = ["PingFang HK", "Heiti TC", "Arial Unicode MS", "sans-serif"]
    else:
        # Linux (GitHub Actions)：安裝 fonts-noto-cjk 後可用
        fonts = [
            "Noto Sans CJK TC",
            "Noto Sans TC",
            "WenQuanYi Micro Hei",
            "DejaVu Sans",
            "sans-serif",
        ]
    rcParams["font.family"] = fonts
    rcParams["axes.facecolor"] = "none"
    rcParams["figure.facecolor"] = "none"
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
    fig.patch.set_facecolor("none")
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="none", transparent=True)
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
    fig.patch.set_facecolor("none")
    ax.set_facecolor("none")
    wedges, _ = ax.pie(
        values,
        colors=colors,
        startangle=130,
        wedgeprops={"linewidth": 1.5, "edgecolor": "none", "width": 0.56},
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
    leg = ax.legend(
        wedges,
        legend_items,
        loc="center left",
        bbox_to_anchor=(1, 0, 0.45, 1),
        fontsize=9,
        frameon=False,
    )
    for text in leg.get_texts():
        text.set_color(TEXT_DK)
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
    # 加日期 cache-bust，讓 Notion 每次執行都重新抓圖片
    today_str = date.today().strftime("%Y%m%d")
    return f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/finance/charts/{fname}?v={today_str}"


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
    """Update existing image blocks in-place; append only on first run."""
    fnames = ["chart_networth.png", "chart_assets.png", "chart_cashflow.png"]
    titles = [
        "📈 淨值趨勢  ·  Net Worth Trend",
        "💰 資產分佈  ·  Asset Breakdown",
        "💹 月收支對比  ·  Monthly Cash Flow",
    ]

    # 取得目前頁面所有 image blocks
    children = api("GET", f"/blocks/{page_id}/children?page_size=100", None, token)
    existing_imgs = [b for b in children.get("results", []) if b["type"] == "image"]

    if len(existing_imgs) >= len(fnames):
        # 更新現有 image blocks（不新增）
        for img_block, fname in zip(existing_imgs[: len(fnames)], fnames):
            new_url = github_raw_url(fname)
            api(
                "PATCH",
                f"/blocks/{img_block['id']}",
                {"image": {"external": {"url": new_url}}},
                token,
            )
        print(f"  ✅ 已更新 {len(fnames)} 張圖表（in-place）")
    else:
        # 首次建立：append 完整區塊
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
        print(f"  ✅ 已首次嵌入 {len(fnames)} 張圖表到 Notion")


# ── Homepage Sync ──────────────────────────────────────────────────────────────
def update_homepage(token, cfg=None):
    """
    從 Notion Assets/Liabilities DB 讀取最新數據，刷新首頁摘要區塊。
    Column 1：負債 + 投資績效（腳本管理）
    Column 2：資產概覽（腳本管理）
    月財務指標：4 個 callout（腳本管理）
    """
    ASSETS_DB = "36af4149-a6aa-81c7-932b-dce2f4fa35a2"
    LIAB_DB = "36af4149-a6aa-81dc-bd04-ff52cef71f61"

    BLK = {
        # Column 2 — 資產概覽
        "total_callout": "36af4149-a6aa-812d-963b-e380b690dced",
        "allocation": "36af4149-a6aa-8141-9dae-cf6a8119dbb2",
        # Column 1 — 負債 + 投資
        "liab_callout": "36cf4149-a6aa-813d-ab7a-ea427e39845a",
        "stock_callout": "36cf4149-a6aa-8181-b25f-d357d18d50c9",
        "gold_callout": "36cf4149-a6aa-81e2-8c74-d4dc8a3f806e",
        # 月財務指標
        "month_heading": "36af4149-a6aa-81ff-89e8-c8f7c1d590bc",
        "income_callout": "36af4149-a6aa-8106-b21a-f3e3c1ba920b",
        "expense_callout": "36af4149-a6aa-81d4-bc34-f8880851dc12",
        "surplus_callout": "36af4149-a6aa-81ac-8415-cb02411b6158",
        "savrate_callout": "36af4149-a6aa-81ee-ae44-e63d4a7dd516",
    }

    def rt(content):
        return [{"type": "text", "text": {"content": content}}]

    def seg(content, bold=False, color="default"):
        return {
            "type": "text",
            "text": {"content": content},
            "annotations": {"bold": bold, "color": color},
        }

    def patch(block_id, btype, text):
        api("PATCH", f"/blocks/{block_id}", {btype: {"rich_text": rt(text)}}, token)

    def patch_rich(block_id, btype, segments):
        api("PATCH", f"/blocks/{block_id}", {btype: {"rich_text": segments}}, token)

    # 1. 讀取 Assets DB
    rows = api("POST", f"/databases/{ASSETS_DB}/query", {"page_size": 50}, token)
    assets = {}
    for row in rows.get("results", []):
        props = row["properties"]
        name = ""
        for k, v in props.items():
            if v.get("type") == "title" and v.get("title"):
                name = v["title"][0]["plain_text"]
                break
        val = (props.get("當前金額 / Current Value") or {}).get("number") or 0
        cost = (props.get("成本 / Cost Basis") or {}).get("number") or val
        cat_sel = (props.get("類別 / Category") or {}).get("select")
        cat = cat_sel["name"] if cat_sel else "其他"
        if name:
            assets[name] = {"value": val, "cost": cost, "cat": cat}

    total_assets = sum(a["value"] for a in assets.values())

    # 2. 讀取 Liabilities DB
    liab_rows = api("POST", f"/databases/{LIAB_DB}/query", {"page_size": 10}, token)
    liab_balance = 0
    liab_name = "玉山銀行信貸"
    liab_original = 600000
    liab_due = "2026/07/29"
    for row in liab_rows.get("results", []):
        props = row["properties"]
        for k, v in props.items():
            if v.get("type") == "title" and v.get("title"):
                liab_name = v["title"][0]["plain_text"]
        liab_balance = (props.get("餘額 / Balance") or {}).get("number") or 0
        liab_original = (props.get("原始金額 / Original Amount") or {}).get(
            "number"
        ) or 600000
        due_prop = (props.get("到期日 / Due Date") or {}).get("date")
        if due_prop:
            liab_due = due_prop.get("start", liab_due).replace("-", "/")
        break

    net_worth = total_assets - liab_balance
    liab_progress = (liab_original - liab_balance) / liab_original * 100

    # 3. 分類比例
    cat_totals = {}
    for a in assets.values():
        cat_totals[a["cat"]] = cat_totals.get(a["cat"], 0) + a["value"]
    sorted_cats = sorted(cat_totals.items(), key=lambda x: -x[1])
    BAR_W = 16
    alloc_segs = []
    for i, (c, v) in enumerate(sorted_cats):
        pct = v / total_assets * 100
        filled = max(0, min(BAR_W, round(pct / 100 * BAR_W)))
        cat_label = c.split(" ")[0]  # 取中文部分
        if i > 0:
            alloc_segs.append(seg("\n"))
        alloc_segs.append(seg(f"{cat_label:<3}  ", bold=True, color="default"))
        if filled > 0:
            alloc_segs.append(seg("█" * filled, color="orange"))
        if filled < BAR_W:
            alloc_segs.append(seg("░" * (BAR_W - filled), color="gray"))
        alloc_segs.append(seg(f"  {pct:.1f}%", color="brown"))

    # 4. 投資績效計算
    stocks = {k: v for k, v in assets.items() if v["cat"] == "股票"}
    gold = {k: v for k, v in assets.items() if "黃金" in k}

    stock_val = sum(s["value"] for s in stocks.values())
    stock_cost = sum(s["cost"] for s in stocks.values())
    stock_pnl = stock_val - stock_cost
    stock_roi = stock_pnl / stock_cost * 100 if stock_cost else 0
    stock_sign = "+" if stock_pnl >= 0 else ""
    stock_names = "\n".join(
        f"{k}  NT${v['value']:,.0f}  ({(v['value']-v['cost'])/v['cost']*100:+.1f}%)"
        for k, v in stocks.items()
    )

    gold_val, gold_cost, gold_name = 0, 0, "黃金存摺"
    for k, v in gold.items():
        gold_val, gold_cost, gold_name = v["value"], v["cost"], k
    gold_pnl = gold_val - gold_cost
    gold_roi = gold_pnl / gold_cost * 100 if gold_cost else 0

    # 5. 月財務指標
    if cfg:
        inc = cfg.get("income", {})
        exp = cfg.get("fixed_expenses", {})
        monthly_income = round(
            inc.get("monthly_base", 0)
            + inc.get("insurance_commission_annual", 0) / 12
            + inc.get("company_interest_annual", 0) / 12
            + inc.get("child_subsidy_monthly", 0)
        )
        monthly_expense = round(sum(exp.values()))
    else:
        monthly_income = 72767
        monthly_expense = 75203
    monthly_surplus = monthly_income - monthly_expense
    savings_rate = monthly_surplus / monthly_income * 100 if monthly_income else 0

    # 6. 更新所有區塊
    today = date.today()
    month_str = f"{today.year}-{today.month:02d}"

    # Column 2 — 資產概覽
    patch(
        BLK["total_callout"],
        "callout",
        f"總資產  NT${total_assets:,.0f}\n淨值  NT${net_worth:,.0f}",
    )
    patch_rich(BLK["allocation"], "paragraph", alloc_segs)

    # Column 1 — 負債
    patch(
        BLK["liab_callout"],
        "callout",
        f"{liab_name}\n餘額  NT${liab_balance:,.0f}\n進度  {liab_progress:.1f}%  還清  {liab_due}",
    )

    # Column 1 — 股票
    patch(
        BLK["stock_callout"],
        "callout",
        f"股票組合  NT${stock_val:,.0f}\n損益  {stock_sign}NT${abs(stock_pnl):,.0f}  ({stock_sign}{stock_roi:.1f}%)\n{stock_names}",
    )

    # Column 1 — 黃金
    gold_sign = "+" if gold_pnl >= 0 else ""
    patch(
        BLK["gold_callout"],
        "callout",
        f"{gold_name}  NT${gold_val:,.0f}\n損益  {gold_sign}NT${abs(gold_pnl):,.0f}  ({gold_sign}{gold_roi:.1f}%)",
    )

    # 月財務指標
    patch(BLK["month_heading"], "heading_2", f"📅 本月財務指標  ·  {month_str}")
    surplus_fmt = (
        f"-NT${abs(monthly_surplus):,.0f}"
        if monthly_surplus < 0
        else f"NT${monthly_surplus:,.0f}"
    )
    patch(BLK["income_callout"], "callout", f"月收入\nNT${monthly_income:,.0f}")
    patch(BLK["expense_callout"], "callout", f"月支出\nNT${monthly_expense:,.0f}")
    patch(BLK["surplus_callout"], "callout", f"月結餘\n{surplus_fmt}")
    patch(BLK["savrate_callout"], "callout", f"儲蓄率\n{savings_rate:.1f}%")

    print(f"  ✅ 首頁更新完成  總資產 NT${total_assets:,.0f}  淨值 NT${net_worth:,.0f}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    token = _load_token()
    cfg = load_config()

    print("=" * 55)
    print(f"Personal Finance OS v2.1 — 圖表生成  {date.today()}")

    # Load DB IDs
    if cfg:
        snap_db = cfg["notion"]["snapshot_db_id"]
        assets_db = cfg["notion"]["assets_db_id"]
        page_id = cfg["notion"].get("charts_page_id")  # Charts & Analytics sub-page
    else:
        # Fallback: v2.1 商業模板 IDs
        snap_db = "36af4149-a6aa-81eb-8ff9-f3886b060e7b"
        assets_db = "36af4149-a6aa-81c7-932b-dce2f4fa35a2"
        page_id = "36af4149-a6aa-811c-a0b2-c82374d93db3"  # Charts & Analytics sub-page

    # Allow env override for Charts page
    page_id = os.environ.get("NOTION_CHARTS_PAGE_ID", page_id)

    os.makedirs(CHARTS, exist_ok=True)

    # 更新股票即時股價
    if cfg and cfg.get("stocks"):
        print("\n[0/3] 更新股票即時股價...")
        update_stock_prices(assets_db, cfg, token)

    # 更新黃金存摺 ROI
    if cfg and cfg.get("gold_savings", {}).get("enabled"):
        print("\n[0b] 更新黃金存摺 ROI...")
        update_gold_roi(assets_db, cfg, token)

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

    # 同步首頁靜態數字
    print("\n[+] 更新 Notion 首頁...")
    update_homepage(token, cfg)

    print("\n圖表公開 URL：")
    for f in ["chart_networth.png", "chart_assets.png", "chart_cashflow.png"]:
        print(f"  {github_raw_url(f)}")
    print("=" * 55)


if __name__ == "__main__":
    main()
