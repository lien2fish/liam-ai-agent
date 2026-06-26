#!/usr/bin/env python3
"""回購提醒：掃描全品牌客戶總表，找出超過門檻天數未回購的客戶，Email 通知。

- 門檻天數 REPURCHASE_DAYS（預設 60），可用環境變數調整
- 只提醒「曾購買過、但距今超過門檻」的客戶（回購對象）
- 從未消費（無最後購買日）的客戶另列一區參考，不算逾期
- 認證沿用既有系統：NOTION_TOKEN / GMAIL_APP_PASSWORD（與保單提醒同一套）
"""
import urllib.request, json, os, smtplib, ssl
from datetime import datetime, date
from email.mime.text import MIMEText
from email.utils import formataddr

BASE = os.path.dirname(os.path.abspath(__file__))
TOKEN = (
    os.environ.get("NOTION_TOKEN")
    or open(os.path.expanduser("~/.config/notion_token")).read().strip()
)
H = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
CFG = json.load(open(os.path.join(BASE, "config.json")))
CUST_DB = CFG["customer_db"]
REMINDER_DAYS = int(os.environ.get("REPURCHASE_DAYS", "60"))
GMAIL_PW = os.environ.get("GMAIL_APP_PASSWORD", "")
ADDR = "lien2fish@gmail.com"


def val(prop):
    t = prop["type"]
    v = prop[t]
    if t in ("title", "rich_text"):
        return "".join(x["plain_text"] for x in v)
    if t in ("phone_number", "email"):
        return v or ""
    if t == "number":
        return v
    if t == "select":
        return v["name"] if v else ""
    if t == "date":
        return v["start"] if v else ""
    return ""


def query_all(dbid):
    out, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        req = urllib.request.Request(
            f"https://api.notion.com/v1/databases/{dbid}/query",
            data=json.dumps(body).encode(),
            headers=H,
            method="POST",
        )
        d = json.load(urllib.request.urlopen(req))
        out += d["results"]
        if not d.get("has_more"):
            break
        cursor = d["next_cursor"]
    return out


def main():
    today = date.today()
    due, never = [], []
    for row in query_all(CUST_DB):
        p = row["properties"]
        g = lambda k: val(p[k]) if k in p else ""
        name, brand = g("客戶姓名"), g("品牌")
        last = g("最後購買日")
        info = {
            "name": name,
            "brand": brand,
            "phone": g("聯絡電話"),
            "level": g("會員等級"),
            "spend": g("累計消費"),
            "last": last,
        }
        if not last:
            never.append(info)
            continue
        d = (today - datetime.strptime(last[:10], "%Y-%m-%d").date()).days
        if d > REMINDER_DAYS:
            info["days"] = d
            due.append(info)
    due.sort(key=lambda x: -x["days"])

    lines = [
        f"# 🔔 回購提醒 {today}",
        "",
        f"> 門檻：超過 **{REMINDER_DAYS} 天**未回購｜資料來源：全品牌客戶總表",
        "",
        f"## ⏰ 待回購客戶（{len(due)} 位）",
    ]
    if due:
        lines += [
            "",
            "| 客戶 | 品牌 | 距上次購買 | 等級 | 電話 |",
            "|------|------|-----------|------|------|",
        ]
        for c in due:
            lines.append(
                f"| {c['name']} | {c['brand']} | **{c['days']} 天** | {c['level'] or '—'} | {c['phone'] or '—'} |"
            )
    else:
        lines.append("\n（目前無超過門檻的客戶）")
    lines += ["", f"## 💤 從未消費客戶（{len(never)} 位，參考）"]
    if never:
        lines += ["", "| 客戶 | 品牌 | 等級 | 電話 |", "|------|------|------|------|"]
        for c in never:
            lines.append(
                f"| {c['name']} | {c['brand']} | {c['level'] or '—'} | {c['phone'] or '—'} |"
            )
    report = "\n".join(lines)

    out = os.path.join(BASE, "..", "reports", f"回購提醒_{today}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"報告已寫入 {out}")
    print(f"待回購 {len(due)} 位、從未消費 {len(never)} 位")

    if due and GMAIL_PW:
        html = report.replace("\n", "<br>")
        msg = MIMEText(html, "html", "utf-8")
        msg["Subject"] = f"🔔 回購提醒：{len(due)} 位客戶待跟進（{today}）"
        msg["From"] = formataddr(("鉅鑫 CRM", ADDR))
        msg["To"] = ADDR
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
            s.login(ADDR, GMAIL_PW)
            s.send_message(msg)
        print(f"✅ 已寄出回購提醒 Email 給 {ADDR}")
    elif not due:
        print("無待回購客戶，不寄信")
    else:
        print("⚠️ 未設 GMAIL_APP_PASSWORD，跳過寄信（本機測試正常）")


if __name__ == "__main__":
    main()
