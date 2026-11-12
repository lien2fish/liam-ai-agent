# -*- coding: utf-8 -*-
"""台股盤後日報（每天 21:37，融資約 21:00 公布後）。

公開版 → reports/盤後日報_YYYY-MM-DD.md（只有一般市場資料，進公開 repo）
私人版 → Email 附 PDF＋Notion（加上持股，持股清單只從環境變數 MARKET_HOLDINGS 讀）
預測紀錄 → market/forecast_log.json（隔日與 5 日區間，到期自動結算命中率）

用法：
    python3 market/evening_report.py                 # 正式
    python3 market/evening_report.py --date 2026-11-12 --no-send   # 本機測試，不寄信不寫 Notion
"""
import argparse
import json
import os
import smtplib
import ssl
import subprocess
import sys
import time
from datetime import date
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "market"))
sys.path.insert(0, str(ROOT))
from tw_daily import *  # noqa: E402,F401

LOG_FILE = ROOT / "market" / "forecast_log.json"
CONFIG = ROOT / "market" / "market_config.json"
MAIL = "lien2fish@gmail.com"

OVERSEAS = [
    ("^SOX", "費城半導體"),
    ("^IXIC", "NASDAQ"),
    ("^GSPC", "S&P 500"),
    ("TSM", "台積電 ADR"),
    ("^VIX", "VIX 恐慌指數"),
    ("TWD=X", "美元/台幣"),
    ("^TNX", "美 10 年債殖利率(%)"),
]


def load_log():
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text())
    return {"forecasts": [], "state": {}}


def save_log(log):
    keep = sorted(log.get("delivered", {}))[-60:]
    log["delivered"] = {k: log["delivered"][k] for k in keep}
    LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=1, default=str))


def wait_margin(d, minutes):
    """融資約 21:00 公布，晚一點再補抓；仍沒有就回 None，不拿昨天的頂替。"""
    deadline = time.time() + minutes * 60
    while True:
        m = twse_margin(d)
        if m or time.time() >= deadline:
            return m
        print("融資尚未公布，10 分鐘後再試")
        time.sleep(600)


def overseas(d):
    """只取報告日以前的資料：美股當天 21:37 還沒收盤，所以美股取 d 之前；匯率／VIX 可含 d。補跑舊日期也不會混入未來資料。"""
    out = []
    for sym, name in OVERSEAS:
        try:
            live = sym in ("TWD=X", "^VIX")
            s = [(k, c) for k, c in yf_daily(sym, 0.3) if (k <= d if live else k < d)]
            (d1, c1), (_, c0) = s[-1], s[-2]
            out.append(
                {
                    "sym": sym,
                    "name": name,
                    "date": d1.isoformat(),
                    "close": c1,
                    "pct": (c1 / c0 - 1) * 100,
                    "low20": min(c for _, c in s[-21:-1]) if len(s) > 21 else None,
                }
            )
        except Exception as e:
            out.append({"sym": sym, "name": name, "error": str(e)})
    return out


def rule_status(closes, inst_days, sox, ds):
    """分批進場的觸發條件（2026-11-06 與 Codex 討論定的規則）。缺資料一律算「不成立」，不會因此亮綠燈。"""
    ma240 = sma(closes, 240)
    below = streak(closes, 240, above=False)
    above = streak(closes, 240, above=True)
    f = [x["foreign"] for x in inst_days]
    inst_ok = len(f) >= 6 and inst_days[0]["date"] == ds
    shrinking = inst_ok and (f[0] >= 0 or f[0] > sum(f[1:6]) / 5)
    sox_ok = bool(sox) and sox.get("low20") is not None
    sox_new_low = sox_ok and sox["close"] < sox["low20"]
    checks = [
        (
            f"連 3 日收在年線（{fmt(ma240, 0)}）之上",
            above >= 3,
            f"目前連 {above} 日" if above else f"已連 {below} 日在年線下",
        ),
        (
            "外資賣超縮小或轉買超",
            shrinking,
            (
                f"今日 {fmt(yi(f[0]), 0, sign=True)} 億 vs 前 5 日平均 {fmt(yi(sum(f[1:6]) / 5), 0, sign=True)} 億"
                if inst_ok
                else "當日法人資料未公布，視為不成立"
            ),
        ),
        (
            "費半沒有創 20 日新低",
            sox_ok and not sox_new_low,
            ("已創新低" if sox_new_low else "未創新低") if sox_ok else "費半資料抓取失敗，視為不成立",
        ),
    ]
    if below >= 2:
        status = "🔴 暫停加碼"
        why = f"已連 {below} 日收在年線下"
    elif all(c[1] for c in checks):
        status = "🟢 照計畫分批"
        why = "三個條件都成立：本月這一批可以照計畫投入（每月 1 批、每批 ≤ 新增預算 20%、不用融資）"
    else:
        status = "🟡 本月這批先等"
        why = "條件未全部成立：" + "、".join(c[0] for c in checks if not c[1])
    return status, why, checks


def build(d, args):
    day = twse_day(d)
    if not day:
        return None
    ds = d.isoformat()
    inst_days = recent_trading_days(d, 6, twse_institutional)
    inst = inst_days[0] if inst_days and inst_days[0]["date"] == ds else None
    margin = wait_margin(d, args.margin_wait)
    valu = twse_valuation(d)

    taiex_hist = yf_daily("^TWII", 10)
    prev_official = day["taiex"] - day["taiex_chg"]
    prev_yf = [c for k, c in taiex_hist if k < d][-1]
    if abs(prev_yf / prev_official - 1) > 0.005:
        raise SystemExit(
            f"Yahoo 昨收 {prev_yf:.2f} 與證交所 {prev_official:.2f} 差超過 0.5%，不出報"
        )
    tx = merge_today(taiex_hist, d, day["taiex"])
    closes = [c for _, c in tx]
    idx = stock_metrics(tx, tx)

    cfg = json.loads(CONFIG.read_text())
    holdings = {
        h.strip() for h in os.environ.get("MARKET_HOLDINGS", "").split(",") if h.strip()
    }
    watch = []
    for s in cfg["watch_stocks"]:
        code = s["code"].split(".")[0]
        o = day["stocks"].get(code)
        row = {
            "code": code,
            "name": s["name"],
            "official": o,
            "val": valu.get(code, {}),
        }
        if o:
            try:
                h = yf_daily(s["code"], 2)
                prev = [c for k, c in h if k < d][-1]
                if abs(prev / (o["close"] - o["chg"]) - 1) <= 0.01:
                    row["m"] = stock_metrics(merge_today(h, d, o["close"]), tx)
                else:
                    row["note"] = "歷史資料與官方對不上，指標不計"
            except Exception as e:
                row["note"] = f"歷史資料抓取失敗：{e}"
            time.sleep(0.3)
        watch.append(row)

    ovs = overseas(d)
    sox = next((o for o in ovs if o["sym"] == "^SOX" and "error" not in o), None)
    status, why, checks = rule_status(closes, inst_days, sox, ds)

    log = load_log()
    trading_days = [k.isoformat() for k, _ in tx]
    settle(log, trading_days, {k.isoformat(): c for k, c in tx})
    fc = {h: forecast(tx, h) for h in (1, 5)}
    bt = {h: backtest_coverage(tx, h) for h in (1, 5)}
    # 只記當天出的預測。補跑舊日期時結果已經知道了，記進去會把命中率灌水。
    live = d == now_tw().date()
    if live:
        log["forecasts"] = [
            e
            for e in log["forecasts"]
            if not (e["kind"] == "evening" and e["base_date"] == ds)
        ]
    for h in (1, 5) if live else ():
        log["forecasts"].append(
            {
                "kind": "evening",
                "base_date": ds,
                "h": h,
                "base_close": day["taiex"],
                "q": qkey(fc[h]["q"]),
            }
        )
    prev_status = log["state"].get("status")
    is_latest = live and ds >= log["state"].get("date", "")
    if is_latest:
        log["state"].update(status=status, date=ds)

    return dict(
        d=d,
        day=day,
        inst=inst,
        inst_days=inst_days,
        margin=margin,
        idx=idx,
        closes=closes,
        watch=watch,
        holdings=holdings,
        ovs=ovs,
        status=status,
        why=why,
        checks=checks,
        fc=fc,
        bt=bt,
        is_latest=is_latest,
        log=log,
        prev_status=prev_status,
    )


def render(r, private):
    d, day, idx = r["d"], r["day"], r["idx"]
    L = [
        f"# 台股盤後日報 {d.isoformat()}",
        "",
        f"> 產出：{now_tw():%Y-%m-%d %H:%M}（台灣時間）｜台股數字來源：證交所當日收盤｜海外：Yahoo Finance（各列標日期）",
        "",
        f"**分批進場燈號：{r['status']}**　{r['why']}",
        "",
    ]

    q1, q5 = r["fc"][1]["q"], r["fc"][5]["q"]
    L += [
        "## 一、明日與 5 日預測（程式依歷史分布計算，非 AI 判斷）",
        "",
        "| 期限 | 中位數 | 50% 區間 | 80% 區間 |",
        "|---|---|---|---|",
        f"| 下一個交易日收盤 | {fmt(q1[0.5], 0)} | {fmt(q1[0.25], 0)}～{fmt(q1[0.75], 0)} | {fmt(q1[0.1], 0)}～{fmt(q1[0.9], 0)} |",
        f"| 5 個交易日後收盤 | {fmt(q5[0.5], 0)} | {fmt(q5[0.25], 0)}～{fmt(q5[0.75], 0)} | {fmt(q5[0.1], 0)}～{fmt(q5[0.9], 0)} |",
        "",
        f"- 方法：近 5 年日報酬先除以當時波動（EWMA λ=0.94）取分布，再乘上目前波動；目前日波動估 {fmt(r['fc'][1]['sigma_daily_pct'])}%。",
        "- 明早 08:41 會依昨夜美股（費半）修正明日區間，LINE 推播。",
        "",
    ]
    bt1, bt5 = r["bt"][1], r["bt"][5]
    L += [
        "**命中率**",
        "",
        "| 項目 | 樣本 | 50% 區間命中 | 80% 區間命中 |",
        "|---|---|---|---|",
        f"| 歷史回測・隔日 | {bt1['n']} | {fmt(bt1['cov50'], 1)}% | {fmt(bt1['cov80'], 1)}% |",
        f"| 歷史回測・5 日 | {bt5['n']} | {fmt(bt5['cov50'], 1)}% | {fmt(bt5['cov80'], 1)}% |",
    ]
    for kind, h, label in (
        ("evening", 1, "實際上線・晚報隔日"),
        ("morning", 1, "實際上線・早盤修正"),
        ("evening", 5, "實際上線・5 日"),
    ):
        sc = scorecard(r["log"], kind, h)
        L.append(
            f"| {label} | {sc['n']} | {fmt(sc['cov50'], 1)}% | {fmt(sc['cov80'], 1)}% |"
            if sc
            else f"| {label} | 0 | 累積中 | 累積中 |"
        )
    L += [
        "",
        "> 理想值：50% 區間約 50%、80% 區間約 80%。實際上線樣本未滿 250 筆前視為未校準。",
        "",
    ]

    L += [
        "## 二、今日大盤",
        "",
        "| 項目 | 數值 |",
        "|---|---|",
        f"| 加權指數收盤 | {fmt(day['taiex'])}（{fmt(day['taiex_chg'], sign=True)}，{fmt(day['taiex_pct'], sign=True, pct=True)}） |",
        f"| 成交值 | {fmt(yi(day.get('turnover')), 0)} 億 |",
        f"| 上漲／下跌／持平家數 | {day.get('up')}／{day.get('down')}／{day.get('flat')} |",
        f"| 月線 MA20 | {fmt(idx['ma20'], 0)}（{'站上' if day['taiex'] > (idx['ma20'] or 0) else '跌破'}） |",
        f"| 季線 MA60 | {fmt(idx['ma60'], 0)}（{'站上' if day['taiex'] > (idx['ma60'] or 0) else '跌破'}） |",
        f"| 年線 MA240 | {fmt(idx['ma240'], 0)}（距離 {fmt((day['taiex'] / idx['ma240'] - 1) * 100, 1, sign=True, pct=True)}） |",
        f"| RSI14 | {fmt(idx['rsi'], 0)} |",
        f"| 距 52 週高點 | {fmt(idx['from_high'], 1, pct=True)} |",
        f"| 60 日年化波動 | {fmt(idx['vol60'], 1, pct=True)} |",
        "",
    ]

    inst, m = r["inst"], r["margin"]
    L += ["## 三、籌碼", "", "| 項目 | 今日 | 說明 |", "|---|---|---|"]
    if inst:
        f5 = sum(x["foreign"] for x in r["inst_days"][:5])
        L += [
            f"| 外資 | {fmt(yi(inst['foreign']), 1, sign=True)} 億 | 近 5 日合計 {fmt(yi(f5), 0, sign=True)} 億 |",
            f"| 投信 | {fmt(yi(inst['trust']), 1, sign=True)} 億 | |",
            f"| 自營商 | {fmt(yi(inst['dealer']), 1, sign=True)} 億 | |",
            f"| 三大法人合計 | {fmt(yi(inst['total']), 1, sign=True)} 億 | |",
        ]
    else:
        L.append("| 三大法人 | 未公布 | 不以前一日數字頂替 |")
    if m:
        L.append(
            f"| 融資餘額 | {fmt(m['balance'] / 1e5, 0)} 億 | 較前日 {fmt(m['change'] / 1e5, 1, sign=True)} 億（證交所隔日會調帳，屬參考值） |"
        )
    else:
        L.append("| 融資餘額 | 未公布 | 出報時證交所尚未公布 |")
    L.append("")

    L += ["## 四、分批進場條件", "", "| 條件 | 成立 | 現況 |", "|---|---|---|"]
    L += [f"| {c[0]} | {'✅' if c[1] else '❌'} | {c[2]} |" for c in r["checks"]]
    L += [
        "",
        "- 燈號規則：連 2 日收在年線下＝暫停加碼；三條件同時成立＝本月這一批可照計畫投入。燈號不是每天買進的訊號，一個月最多投入一批。",
        "",
    ]

    L += [
        "## 五、海外與總經",
        "",
        "| 項目 | 最新 | 漲跌 | 資料日期 |",
        "|---|---|---|---|",
    ]
    for o in r["ovs"]:
        if "error" in o:
            L.append(f"| {o['name']} | 抓取失敗 | | |")
        else:
            L.append(
                f"| {o['name']} | {fmt(o['close'])} | {fmt(o['pct'], sign=True, pct=True)} | {o['date']} |"
            )
    L += [
        "",
        "> 21:37 出報時美股尚未開盤，表中美股為前一個交易日收盤；匯率為最新報價。",
        "",
    ]

    L += [
        "## 六、觀察清單",
        "",
        "| 股票 | 收盤 | 漲跌 | MA20 | MA60 | RSI | Beta | 距高點 | 本益比 | 殖利率 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for w in r["watch"]:
        o, mm, v = w["official"], w.get("m", {}), w["val"]
        if not o:
            L.append(f"| {w['name']} {w['code']} | 無成交資料 | | | | | | | | |")
            continue
        L.append(
            f"| {w['name']} {w['code']} | {fmt(o['close'])} | {fmt(o['pct'], sign=True, pct=True)} | "
            f"{fmt(mm.get('ma20'))} | {fmt(mm.get('ma60'))} | {fmt(mm.get('rsi'), 0)} | {fmt(mm.get('beta'))} | "
            f"{fmt(mm.get('from_high'), 1, pct=True)} | {fmt(v.get('pe'), 1)} | {fmt(v.get('yield'), 2, pct=True)} |"
        )
    notes = [f"- {w['name']}：{w['note']}" for w in r["watch"] if w.get("note")]
    L += (
        [""]
        + notes
        + (
            [
                "- Beta 為對加權指數、120 日按日期對齊；樣本不足顯示 N/A。價格未還原除權息。",
                "",
            ]
        )
    )

    if private:
        L += ["## 七、我的持股（私人版）", ""]
        mine = [w for w in r["watch"] if w["code"] in r["holdings"]]
        if not mine:
            L.append(
                "- 未設定持股（GitHub Secret `MARKET_HOLDINGS`）或持股不在觀察清單內。"
            )
        for w in mine:
            o, mm = w["official"], w.get("m", {})
            if not o or not mm:
                L.append(f"- **{w['name']}**：資料不足")
                continue
            flags = []
            if mm.get("ma20") and o["close"] < mm["ma20"]:
                flags.append("收在月線下")
            if mm.get("ma60") and o["close"] < mm["ma60"]:
                flags.append("收在季線下")
            if mm.get("rsi") is not None and mm["rsi"] < 30:
                flags.append("RSI 超賣")
            if mm.get("rsi") is not None and mm["rsi"] > 70:
                flags.append("RSI 過熱")
            L.append(
                f"- **{w['name']} {w['code']}**：收 {fmt(o['close'])}（{fmt(o['pct'], sign=True, pct=True)}），"
                f"Beta {fmt(mm.get('beta'))}、距高點 {fmt(mm.get('from_high'), 1, pct=True)}；"
                + ("注意：" + "、".join(flags) if flags else "技術面無警示")
            )
        L += ["", "> 以上為依規則產生的提醒，不是買賣指令；是否動作由你決定。", ""]

    L += [
        "## 資料來源",
        "",
        "- 證交所 MI_INDEX（收盤、漲跌家數、成交值）、BFI82U（三大法人）、MI_MARGN（融資）、BWIBBU_d（本益比／殖利率）",
        "- Yahoo Finance：加權指數 10 年日線（計算均線、波動、預測）、個股 2 年日線、海外指數與匯率",
        "",
    ]
    return "\n".join(L)


def send_email(subject, body_html, pdf_path):
    pw = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not pw:
        print("⚠️ 未設 GMAIL_APP_PASSWORD，略過寄信")
        return False
    msg = MIMEMultipart()
    msg["Subject"], msg["From"], msg["To"] = subject, MAIL, MAIL
    msg.attach(MIMEText(body_html, "html", "utf-8"))
    part = MIMEApplication(Path(pdf_path).read_bytes(), _subtype="pdf")
    part.add_header(
        "Content-Disposition", "attachment", filename=("utf-8", "", Path(pdf_path).name)
    )
    msg.attach(part)
    with smtplib.SMTP_SSL(
        "smtp.gmail.com", 465, context=ssl.create_default_context()
    ) as s:
        s.login(MAIL, pw)
        s.send_message(msg)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--no-send", action="store_true")
    ap.add_argument(
        "--margin-wait", type=int, default=int(os.environ.get("MARGIN_WAIT_MIN", "60"))
    )
    args = ap.parse_args()
    d = date.fromisoformat(args.date) if args.date else now_tw().date()

    r = build(d, args)
    if r is None:
        print(f"{d} 證交所無收盤資料（休市），不出報")
        return

    public = render(r, private=False)
    private = render(r, private=True)
    pub_path = ROOT / "reports" / f"盤後日報_{d.isoformat()}.md"
    pub_path.write_text(public)
    out_dir = Path(os.environ.get("RUNNER_TEMP", "/tmp"))
    priv_md = out_dir / f"盤後日報_{d.isoformat()}_私人.md"
    pdf_text = private
    for k, v in {"🟢": "【綠燈】", "🟡": "【黃燈】", "🔴": "【紅燈】", "✅": "成立", "❌": "未成立"}.items():
        pdf_text = pdf_text.replace(k, v)
    priv_md.write_text(pdf_text)
    pdf = out_dir / f"台股盤後日報_{d.isoformat()}.pdf"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "md_to_pdf.py"),
            str(pdf),
            str(priv_md),
        ],
        check=True,
    )
    save_log(r["log"])
    print(f"✅ 公開版 {pub_path}\n✅ 私人版 {priv_md}\n✅ PDF {pdf}")

    if args.no_send:
        return

    q1 = r["fc"][1]["q"]
    summary = (
        f"加權 {fmt(r['day']['taiex'])}（{fmt(r['day']['taiex_pct'], sign=True, pct=True)}）<br>"
        f"燈號：{r['status']}　{r['why']}<br>"
        f"明日 80% 區間：{fmt(q1[0.1], 0)}～{fmt(q1[0.9], 0)}（中位 {fmt(q1[0.5], 0)}）<br><br>完整報告見附件 PDF。"
    )
    # 先 Notion 後 Email：Notion 失敗就不寄信。每完成一步就記進 forecast_log.json（commit 步驟失敗也會執行），
    # 重跑同一天時已完成的步驟會跳過，不會重複寄信或重複建頁。
    log = r["log"]
    done = log.setdefault("delivered", {}).setdefault(d.isoformat(), {})
    if not done.get("notion"):
        import notion_daily

        done["notion"] = notion_daily.publish(f"{d.isoformat()} {r['status']}", private)
        save_log(log)
    if not done.get("email"):
        if send_email(f"📊 台股盤後日報 {d.isoformat()}｜{r['status']}", summary, pdf):
            done["email"] = True
            save_log(log)

    if r["is_latest"] and r["prev_status"] and r["prev_status"] != r["status"] and not done.get("line"):
        from line_assistant.notify import notify

        notify(
            f"📊 台股分批燈號改變\n{r['prev_status']} → {r['status']}\n{r['why']}\n"
            f"加權 {fmt(r['day']['taiex'], 0)}，明日 80% 區間 {fmt(q1[0.1], 0)}～{fmt(q1[0.9], 0)}"
        )
        done["line"] = True
        save_log(log)


if __name__ == "__main__":
    main()
