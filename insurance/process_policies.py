#!/usr/bin/env python3
"""
產險清單整理：去重複（同一保單續保多年只留最新生效日一筆），
輸出 Numbers 檔給人看、輸出 JSON 給每日到期提醒自動任務讀取。
"""

import json
from datetime import date, timedelta
from pathlib import Path

from policy_data import RAW_ROWS, COLUMNS

WORKSPACE = Path(__file__).resolve().parent.parent
OUT_JSON = WORKSPACE / "insurance" / "active_policies.json"
NUMBERS_DIR = Path("/Users/lien/Desktop/鉅鑫管理顧問/磊山保經/產險資料")
NUMBERS_PATH = NUMBERS_DIR / "有效產險清單_整理版.numbers"

MASKED_PREFIX = "XX"
MASK_MATCH_WINDOW_DAYS = 548  # 約 18 個月，用來提示新格式保單可能與哪筆舊保單重疊


def row_dict(r):
    return dict(zip(COLUMNS, r))


def signature(policy_no: str) -> str:
    return "".join(c for c in policy_no if c.isalpha())


def parse_date(s: str) -> date:
    y, m, d = map(int, s.split("-"))
    return date(y, m, d)


def day_of_year(d: date) -> int:
    """以固定（非閏年）參考年份計算月日對應的天數序號，用於跨年比較月日距離。"""
    ref = (
        date(2001, 3, 1) if (d.month, d.day) == (2, 29) else date(2001, d.month, d.day)
    )
    return (ref - date(2001, 1, 1)).days


MONTH_DAY_TOLERANCE = 45  # 同一份保單續保，生效月日每年飄動不會超過這個天數


def cluster_by_month_day(items):
    """同一字母代碼下，可能同時存在月日完全不同的「另一張保單」（例如同一人2台車都codeKMY），
    用月日相近度（含跨年首尾）再切成獨立的子系列，避免誤判成同一份續保。"""
    items = sorted(items, key=lambda x: day_of_year(parse_date(x["生效日"])))
    n = len(items)
    clusters = []
    used = [False] * n
    for i in range(n):
        if used[i]:
            continue
        cluster = [items[i]]
        used[i] = True
        for j in range(n):
            if used[j]:
                continue
            doy_i = day_of_year(parse_date(items[i]["生效日"]))
            doy_j = day_of_year(parse_date(items[j]["生效日"]))
            gap = min(abs(doy_i - doy_j), 365 - abs(doy_i - doy_j))
            if gap <= MONTH_DAY_TOLERANCE:
                cluster.append(items[j])
                used[j] = True
        clusters.append(cluster)
    return clusters


def dedupe(rows):
    """依 (要保人ID,被保險人ID,保險公司,保單號碼字母代碼,生效月日相近系列) 分組，
    同組僅保留生效日最新一筆；月日差太多視為不同保單（例如同人2台車）不互相取代。"""
    groups = {}
    for r in rows:
        d = row_dict(r)
        key = (d["要保人ID"], d["被保險人ID"], d["保險公司"], signature(d["保單號碼"]))
        groups.setdefault(key, []).append(d)

    kept, dropped = [], []
    for key, items in groups.items():
        for cluster in cluster_by_month_day(items):
            cluster.sort(key=lambda x: parse_date(x["生效日"]), reverse=True)
            kept.append(cluster[0])
            for old in cluster[1:]:
                dropped.append(
                    {
                        **old,
                        "取代者保單號碼": cluster[0]["保單號碼"],
                        "取代者生效日": cluster[0]["生效日"],
                    }
                )
    return kept, dropped


def flag_masked_overlaps(kept):
    """新格式（XX開頭）保單可能是舊保單的續保，但字母代碼比對不到，列出疑似重疊供人工核對。"""
    flags = []
    by_bucket = {}
    for d in kept:
        bucket = (d["要保人ID"], d["被保險人ID"], d["保險公司"])
        by_bucket.setdefault(bucket, []).append(d)

    for bucket, items in by_bucket.items():
        masked = [d for d in items if d["保單號碼"].startswith(MASKED_PREFIX)]
        non_masked = [d for d in items if not d["保單號碼"].startswith(MASKED_PREFIX)]
        for m in masked:
            m_date = parse_date(m["生效日"])
            for n in non_masked:
                n_date = parse_date(n["生效日"])
                gap = (m_date - n_date).days
                if 0 < gap <= MASK_MATCH_WINDOW_DAYS:
                    flags.append(
                        {
                            "要保人": m["要保人"],
                            "被保險人": m["被保險人"],
                            "保險公司": m["保險公司"],
                            "新格式保單號碼": m["保單號碼"],
                            "新格式生效日": m["生效日"],
                            "疑似舊保單號碼": n["保單號碼"],
                            "疑似舊保單生效日": n["生效日"],
                            "間隔天數": gap,
                        }
                    )
    return flags


def next_renewal(effective_date_str: str, today: date) -> date:
    d = parse_date(effective_date_str)
    try:
        nd = d.replace(year=today.year)
    except ValueError:  # 2/29 對應非閏年
        nd = d.replace(year=today.year, day=28)
    while nd < today:
        try:
            nd = nd.replace(year=nd.year + 1)
        except ValueError:
            nd = nd.replace(year=nd.year + 1, day=28)
    return nd


def build_numbers(kept, dropped, flags):
    from numbers_parser import Document

    NUMBERS_DIR.mkdir(parents=True, exist_ok=True)
    doc = Document()
    today = date.today()

    sheet = doc.sheets[0]
    sheet.name = "目前有效保單"
    table = sheet.tables[0]
    table.name = "有效保單"
    headers = [
        "保險公司",
        "要保人",
        "要保人ID",
        "被保險人",
        "被保險人ID",
        "保單號碼",
        "生效日",
        "下次續保日",
        "是否已發佣",
    ]
    kept_sorted = sorted(
        kept, key=lambda d: (d["保險公司"], d["要保人"], d["生效日"]), reverse=False
    )
    for c, h in enumerate(headers):
        table.write(0, c, h)
    for i, d in enumerate(kept_sorted, start=1):
        renewal = next_renewal(d["生效日"], today)
        vals = [
            d["保險公司"],
            d["要保人"],
            d["要保人ID"],
            d["被保險人"],
            d["被保險人ID"],
            d["保單號碼"],
            d["生效日"],
            renewal.isoformat(),
            d["是否已發佣"],
        ]
        for c, v in enumerate(vals):
            table.write(i, c, v)

    doc.add_sheet("歷史重複保單（已被續保取代）")
    sheet2 = doc.sheets[-1]
    table2 = sheet2.tables[0]
    headers2 = [
        "要保人",
        "被保險人",
        "保險公司",
        "舊保單號碼",
        "舊生效日",
        "取代者保單號碼",
        "取代者生效日",
    ]
    for c, h in enumerate(headers2):
        table2.write(0, c, h)
    for i, d in enumerate(
        sorted(dropped, key=lambda x: x["生效日"], reverse=True), start=1
    ):
        vals = [
            d["要保人"],
            d["被保險人"],
            d["保險公司"],
            d["保單號碼"],
            d["生效日"],
            d["取代者保單號碼"],
            d["取代者生效日"],
        ]
        for c, v in enumerate(vals):
            table2.write(i, c, v)

    doc.add_sheet("⚠️ 新格式保單需人工核對")
    sheet3 = doc.sheets[-1]
    table3 = sheet3.tables[0]
    headers3 = [
        "要保人",
        "被保險人",
        "保險公司",
        "新格式保單號碼",
        "新格式生效日",
        "疑似舊保單號碼",
        "疑似舊保單生效日",
        "間隔天數",
    ]
    for c, h in enumerate(headers3):
        table3.write(0, c, h)
    for i, f in enumerate(flags, start=1):
        vals = [f[h] for h in headers3]
        for c, v in enumerate(vals):
            table3.write(i, c, v)

    doc.save(str(NUMBERS_PATH))


def strip_pii(rows):
    """供 GitHub 公開 repo 用的到期提醒只需公司/姓名/保單號碼/日期，不應含身分證號等個資。"""
    return [
        {k: v for k, v in d.items() if k not in ("要保人ID", "被保險人ID")}
        for d in rows
    ]


def main():
    kept, dropped = dedupe(RAW_ROWS)
    flags = flag_masked_overlaps(kept)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(strip_pii(kept), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    build_numbers(kept, dropped, flags)

    print(f"原始：{len(RAW_ROWS)} 筆")
    print(f"去重複後保留：{len(kept)} 筆")
    print(f"歷史重複移除：{len(dropped)} 筆")
    print(f"新格式保單待人工核對：{len(flags)} 筆")
    print(f"Numbers 檔已輸出：{NUMBERS_PATH}")
    print(f"自動任務用資料已輸出：{OUT_JSON}")


if __name__ == "__main__":
    main()
