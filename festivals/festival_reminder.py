#!/usr/bin/env python3
"""節慶送禮備料提醒：商業檔期前 N 天寄 Email。

13 個商業檔期一律節前 60 天提醒一次；春節（120）、中秋（90）、端午（75）
在各自的備料起點另有一封更早的。資料表＝festivals/festivals.json。

農曆走 lunardate。⚠️ 套件算錯就等於寄出日期錯的提醒，所以每次執行都先拿
官方公告的六個日期自我驗證，對不上就寄警告信並 exit 1、不寄任何提醒。

觸發是「剛好命中那一天」而不是「小於等於」——後者會連續 60 天每天寄一封。
代價是某天 run 掛掉就漏一封；Cloudflare 稽核輪會抓到沒跑並推 LINE，補
workflow_dispatch 即可（只寄信給自己，補跑安全）。

用法：
    python3 festivals/festival_reminder.py              # 每天跑的正常模式
    python3 festivals/festival_reminder.py --selfcheck  # 只驗農曆
    python3 festivals/festival_reminder.py --list 2027  # 印出該年所有檔期日期
    FESTIVAL_TODAY=2026-07-27 python3 ...               # 模擬某一天
"""
import json, os, smtplib, ssl, sys
from datetime import date, timedelta
from email.mime.text import MIMEText
from email.utils import formataddr

from lunardate import LunarDate

JSON_PATH = os.environ.get(
    "FESTIVALS_JSON", os.path.join(os.path.dirname(__file__), "festivals.json")
)
GMAIL_PW = os.environ.get("GMAIL_APP_PASSWORD", "")
ADDR = "lien2fish@gmail.com"
HORIZON = 120  # 信末總覽看多遠

# 人事行政總處 115／116 年行事曆與 PublicHolidays.tw 公告的國曆日期。
SELFCHECK = [
    ("2026 正月初一", 2026, 1, 1, "2026-02-17"),
    ("2026 五月初五", 2026, 5, 5, "2026-06-19"),
    ("2026 八月十五", 2026, 8, 15, "2026-09-25"),
    ("2027 正月初一", 2027, 1, 1, "2027-02-06"),
    ("2027 五月初五", 2027, 5, 5, "2027-06-09"),
    ("2027 八月十五", 2027, 8, 15, "2027-09-15"),
]


def selfcheck():
    bad = []
    for label, y, m, d, expect in SELFCHECK:
        got = LunarDate(y, m, d).toSolarDate().isoformat()
        print(
            ("  ✅ " if got == expect else "  ❌ ")
            + f"{label} → {got}（應為 {expect}）"
        )
        if got != expect:
            bad.append(f"{label}：算出 {got}，應為 {expect}")
    return bad


def nth_weekday(year, month, nth, weekday):
    """該月第 nth 個星期 weekday（weekday 用 Python 慣例，0=一 … 6=日）。"""
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (nth - 1))


def candidates(rule, year):
    """rule 在 year 附近可能落到的所有國曆日期。

    農曆要多看前後一年：農曆十二月十六（尾牙）落在下一個國曆年。
    """
    t = rule["type"]
    if t == "lunar":
        return sorted(
            LunarDate(y, rule["month"], rule["day"]).toSolarDate()
            for y in (year - 1, year, year + 1)
        )
    if t == "solar":
        return [date(y, rule["month"], rule["day"]) for y in (year, year + 1)]
    return [
        nth_weekday(y, rule["month"], rule["nth"], rule["weekday"])
        for y in (year, year + 1)
    ]


def next_occurrence(rule, today):
    return next(d for d in candidates(rule, today.year) if d >= today)


def load():
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def stars(brands):
    """只留有火力的品牌（★ — 是「這檔不用出」）。"""
    return {k: v for k, v in brands.items() if not v.startswith("★ ")}


def build_text(today, hits, upcoming):
    lines = [f"# 🧧 節慶備料提醒 {today}", ""]
    for f, r in hits:
        lines += [
            f"## {f['name']}　{f['date']}（還有 {f['days']} 天）",
            f"　{r['stage']}",
            "",
            f"- 送禮對象：{f['targets']}",
            f"- 主流品項：{f['items']}",
            f"- 客單價：{f['price_band']}",
            "- 品牌火力："
            + "／".join(f"{k} {v}" for k, v in stars(f["brands"]).items()),
            f"- 備註：{f['note']}",
            "",
        ]
    later = [
        f for f in upcoming if f["days"] <= HORIZON and f not in [h[0] for h in hits]
    ]
    if later:
        lines += [f"## 未來 {HORIZON} 天內的其他檔期", ""]
        for f in later:
            lines.append(f"- {f['date']}　{f['name']}（{f['days']} 天後）")
    return "\n".join(lines)


def build_html(today, hits, upcoming, taboos):
    css_card = (
        "border:1px solid #E2DCD2;border-top:3px solid #B32A22;"
        "padding:16px 18px;margin:0 0 18px;font-family:-apple-system,'PingFang TC',sans-serif"
    )
    css_th = "text-align:left;padding:4px 10px 4px 0;color:#7C7469;font-size:13px;white-space:nowrap;vertical-align:top"
    css_td = "padding:4px 0;font-size:14px;color:#1C1A18"
    out = [
        "<div style=\"max-width:640px;font-family:-apple-system,'PingFang TC',sans-serif;color:#1C1A18\">",
        f'<p style="font-size:12px;letter-spacing:.15em;color:#B32A22;margin:0 0 4px">節慶備料提醒　{today}</p>',
    ]
    for f, r in hits:
        rows = [
            ("送禮對象", f["targets"]),
            ("主流品項", f["items"]),
            ("客單價", f["price_band"]),
            (
                "品牌火力",
                "<br>".join(f"{k}　{v}" for k, v in stars(f["brands"]).items()),
            ),
            ("備註", f["note"]),
        ]
        out += [
            f'<div style="{css_card}">',
            f'<h2 style="margin:0 0 2px;font-size:21px">{f["name"]}</h2>',
            f'<p style="margin:0 0 12px;font-size:13px;color:#7C7469">'
            f'{f["date"]}　還有 <b style="color:#B32A22">{f["days"]}</b> 天　·　{r["stage"]}</p>',
            '<table style="border-collapse:collapse;width:100%">',
        ]
        for k, v in rows:
            out.append(
                f'<tr><th style="{css_th}">{k}</th><td style="{css_td}">{v}</td></tr>'
            )
        out += ["</table>", "</div>"]

    later = [
        f for f in upcoming if f["days"] <= HORIZON and f not in [h[0] for h in hits]
    ]
    if later:
        out.append(
            f'<p style="font-size:13px;color:#7C7469;margin:22px 0 6px">未來 {HORIZON} 天內的其他檔期</p>'
            '<table style="border-collapse:collapse;font-size:13px">'
        )
        for f in later:
            out.append(
                f'<tr><td style="padding:3px 14px 3px 0;color:#7C7469">{f["date"]}</td>'
                f'<td style="padding:3px 14px 3px 0">{f["name"]}</td>'
                f'<td style="padding:3px 0;color:#7C7469">{f["days"]} 天後</td></tr>'
            )
        out.append("</table>")

    out.append(
        '<p style="font-size:12px;color:#7C7469;margin:26px 0 0;border-top:1px solid #E2DCD2;padding-top:12px">'
        "送禮禁忌：" + "；".join(taboos) + "。<br>"
        "備料與開賣週數為禮盒通路慣例推估，非產季資料——海鮮實際備料須依當期漁獲調整。</p></div>"
    )
    return "".join(out)


def send(subject, html):
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("鉅鑫 節慶備料提醒", ADDR))
    msg["To"] = ADDR
    with smtplib.SMTP_SSL(
        "smtp.gmail.com", 465, context=ssl.create_default_context()
    ) as s:
        s.login(ADDR, GMAIL_PW)
        s.send_message(msg)


def main():
    data = load()

    if "--list" in sys.argv:
        year = int(sys.argv[sys.argv.index("--list") + 1])
        rows = []
        for f in data["festivals"]:
            for d in candidates(f["rule"], year):
                if d.year == year:
                    rows.append((d, f["name"]))
        for d, n in sorted(rows):
            print(f"{d}　{d.strftime('%a')}　{n}")
        return

    print("農曆自我驗證：", flush=True)
    bad = selfcheck()
    if bad:
        body = (
            "lunardate 算出的日期與官方公告不符，今日不寄任何節慶提醒。<br><br>"
            + "<br>".join(bad)
        )
        print("❌ 自我驗證失敗，不寄提醒", flush=True)
        if GMAIL_PW:
            send(f"🔴 節慶提醒停擺：農曆自我驗證失敗（{date.today()}）", body)
        sys.exit(1)

    if "--selfcheck" in sys.argv:
        return

    today = (
        date.fromisoformat(os.environ["FESTIVAL_TODAY"])
        if os.environ.get("FESTIVAL_TODAY")
        else date.today()
    )

    upcoming = []
    for f in data["festivals"]:
        nxt = next_occurrence(f["rule"], today)
        upcoming.append({**f, "date": nxt, "days": (nxt - today).days})
    upcoming.sort(key=lambda x: x["days"])

    hits = [(f, r) for f in upcoming for r in f["reminders"] if f["days"] == r["days"]]

    print(build_text(today, hits, upcoming), flush=True)

    if not hits:
        print(f"\n（{today} 無命中的檔期，不寄信）", flush=True)
        return
    if not GMAIL_PW:
        print("\n⚠️ 未設 GMAIL_APP_PASSWORD，不寄信", flush=True)
        return

    names = "、".join(f["name"] for f, _ in hits)
    days = hits[0][0]["days"]
    send(
        f"🧧 節慶備料提醒：{names}還有 {days} 天（{today}）",
        build_html(today, hits, upcoming, data["taboos"]),
    )
    print(f"\n✅ Email 已寄出（{len(hits)} 個檔期命中）", flush=True)


if __name__ == "__main__":
    main()
