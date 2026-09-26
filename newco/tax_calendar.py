"""新公司稅務行事曆提醒。

在提醒日當天寄出 Email，說明該做什麼、誰做、漏了會怎樣。
資料表＝ newco/tax_calendar.json。

    python3 newco/tax_calendar.py                  # 用今天跑
    TAX_TODAY=2026-11-08 python3 newco/tax_calendar.py   # 模擬某一天
    TAX_DRYRUN=1 python3 newco/tax_calendar.py     # 只印不寄

⚠️ JSON 的 active=false 時只做自我檢查與預覽，不寄信。
   公司設立完成、拿到統編之後才把 active 改成 true。
"""
import calendar
import json
import os
import smtplib
import ssl
import sys
from datetime import date, timedelta
from email.mime.text import MIMEText
from email.utils import formataddr

JSON_PATH = os.environ.get(
    "TAX_CALENDAR_JSON", os.path.join(os.path.dirname(__file__), "tax_calendar.json")
)
GMAIL_PW = os.environ.get("GMAIL_APP_PASSWORD", "")
ADDR = "lien2fish@gmail.com"
HORIZON = 90

LEVEL_COLOR = {"high": "#A8352A", "mid": "#8A5F14", "low": "#2F6B5C"}


def month_end(year, month):
    return date(year, month, calendar.monthrange(year, month)[1])


def occurrences(rule, start, end):
    """回傳 rule 在 [start, end] 之間的所有截止日。"""
    out = []
    t = rule.get("type")
    y, m = start.year, start.month
    while date(y, m, 1) <= end:
        d = None
        if t == "monthly":
            d = date(y, m, rule["day"])
        elif t == "odd_month" and m % 2 == 1:
            d = date(y, m, rule["day"])
        elif t == "month_end":
            d = month_end(y, m)
        elif t == "annual" and m == rule.get("month"):
            if rule.get("day"):
                d = date(y, m, rule["day"])
        if d and start <= d <= end:
            out.append(d)
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def selfcheck(today):
    """驗證規則算出來的日期符合預期，對不上就讓 run 變紅。"""
    problems = []
    year = today.year
    vat = occurrences({"type": "odd_month", "day": 15}, date(year, 1, 1), date(year, 12, 31))
    got = sorted({d.month for d in vat})
    if got != [1, 3, 5, 7, 9, 11]:
        problems.append(f"營業稅應落在單月，實際得到 {got}")
    if len(vat) != 6:
        problems.append(f"營業稅一年應 6 次，實際 {len(vat)} 次")
    me = occurrences({"type": "month_end"}, date(year, 2, 1), date(year, 2, 28))
    if not me or me[0] != month_end(year, 2):
        problems.append("月底規則在 2 月算錯")
    return problems


def load():
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_html(today, hits, upcoming, company):
    rows = []
    for it, due in hits:
        c = LEVEL_COLOR.get(it.get("level"), "#4B4B45")
        days = (due - today).days
        rows.append(f"""
        <div style="border-left:4px solid {c};padding:12px 16px;margin:0 0 14px;background:#F4F2EB">
          <div style="font-size:17px;font-weight:700;color:#1B1D1C">{it['name']}</div>
          <div style="font-family:monospace;font-size:12px;color:{c};margin:4px 0 10px">
            截止 {due:%Y-%m-%d}　·　剩 {days} 天　·　{it.get('who','')}
          </div>
          <div style="font-size:14px;color:#1B1D1C;margin-bottom:6px"><b>要做什麼：</b>{it.get('action','')}</div>
          <div style="font-size:13px;color:#4B4B45;margin-bottom:6px">{it.get('detail','')}</div>
          <div style="font-size:12px;color:{c}"><b>逾期：</b>{it.get('penalty','')}</div>
          {f'<div style="font-size:13px;color:#A8352A;margin-top:8px">{it["note"]}</div>' if it.get("note") else ''}
        </div>""")

    up = "".join(
        f'<tr><td style="padding:5px 10px;font-family:monospace;font-size:12px;color:#78756C">{d:%m-%d}</td>'
        f'<td style="padding:5px 10px;font-size:13px">{i["name"]}</td>'
        f'<td style="padding:5px 10px;font-size:12px;color:#78756C">{(d-today).days} 天後</td></tr>'
        for i, d in upcoming
    )

    return f"""<div style="font-family:-apple-system,'PingFang TC',sans-serif;max-width:640px;margin:0 auto;padding:24px">
      <div style="font-family:monospace;font-size:11px;letter-spacing:.15em;color:#78756C;text-transform:uppercase">稅務行事曆　·　{company}</div>
      <h2 style="font-size:20px;margin:8px 0 4px;color:#1B1D1C">今天要處理 {len(hits)} 件</h2>
      <div style="font-size:13px;color:#78756C;margin-bottom:20px">{today:%Y-%m-%d}</div>
      {''.join(rows)}
      <div style="margin-top:28px;padding-top:16px;border-top:1px solid #DCD8CD">
        <div style="font-size:13px;font-weight:700;color:#4B4B45;margin-bottom:8px">未來 {HORIZON} 天</div>
        <table style="width:100%;border-collapse:collapse">{up}</table>
      </div>
      <div style="margin-top:24px;padding:12px 14px;background:#F3E4E1;font-size:12px;line-height:1.7;color:#4B4B45">
        <b style="color:#A8352A">申報義務在公司，不在事務所。</b>記帳士代辦不等於你不用管——
        每一次申報後跟他要回執，那是唯一能證明有送出去的東西。
      </div>
    </div>"""


def send(subject, html):
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("新公司 稅務行事曆", ADDR))
    msg["To"] = ADDR
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
        s.login(ADDR, GMAIL_PW)
        s.send_message(msg)


def main():
    raw = os.environ.get("TAX_TODAY", "").strip()
    today = date.fromisoformat(raw) if raw else date.today()

    problems = selfcheck(today)
    if problems:
        print("🔴 自我檢查失敗：", flush=True)
        for p in problems:
            print("  -", p, flush=True)
        sys.exit(1)
    print("✅ 自我檢查通過（營業稅落在單月、一年六次、月底規則正確）", flush=True)

    data = load()
    company = data.get("company", "新公司")
    end = today + timedelta(days=HORIZON)

    hits, upcoming = [], []
    for it in data["items"]:
        rule = it.get("rule", {})
        if rule.get("type") == "annual" and not rule.get("month"):
            continue  # 日期未定（例如食品業者登錄）
        for due in occurrences(rule, today, end):
            if (due - today).days == it.get("notify_before", 7):
                hits.append((it, due))
            upcoming.append((it, due))

    upcoming.sort(key=lambda x: x[1])
    upcoming = upcoming[:12]

    print(f"\n日期：{today}　命中 {len(hits)} 件", flush=True)
    for it, due in hits:
        print(f"  ▸ {it['name']}（截止 {due}，剩 {(due-today).days} 天）", flush=True)

    if not data.get("active"):
        print("\n⏸️  active=false，公司尚未設立，不寄信。", flush=True)
        print("   設立完成後把 tax_calendar.json 的 active 改成 true。", flush=True)
        return
    if not hits:
        print("\n今天沒有要提醒的項目。", flush=True)
        return
    if os.environ.get("TAX_DRYRUN"):
        print("\n（TAX_DRYRUN=1，只印不寄）", flush=True)
        return
    if not GMAIL_PW:
        print("\n⚠️ 未設 GMAIL_APP_PASSWORD，不寄信", flush=True)
        return

    send(f"【稅務行事曆】今天要處理 {len(hits)} 件 - {today:%m/%d}",
         build_html(today, hits, upcoming, company))
    print("\n✅ 已寄出", flush=True)


if __name__ == "__main__":
    main()
