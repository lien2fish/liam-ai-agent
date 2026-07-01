#!/usr/bin/env python3
"""壽險客戶生日提醒：讀 Notion 壽險名單，未來 N 天內生日的客戶 → Email。

沿用 visit_config.json 的 life_clients_db。窗口 BIRTHDAY_DAYS（預設 7）。
⚠️ repo 為 public，客戶資料只寄 Email、不寫入 repo。
"""
import json, os, smtplib, ssl, urllib.request
from datetime import date, datetime
from email.mime.text import MIMEText
from email.utils import formataddr

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "visit_config.json")))
DBID = CFG["life_clients_db"]
WINDOW = int(os.environ.get("BIRTHDAY_DAYS", CFG.get("birthday_days", 7)))
TOKEN = (
    os.environ.get("NOTION_TOKEN")
    or open(os.path.expanduser("~/.config/notion_token")).read().strip()
)
H = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
GMAIL_PW = os.environ.get("GMAIL_APP_PASSWORD", "")
ADDR = "lien2fish@gmail.com"


def val(prop):
    t = prop["type"]
    v = prop[t]
    if t in ("title", "rich_text"):
        return "".join(x["plain_text"] for x in v)
    if t == "phone_number":
        return v or ""
    if t == "number":
        return v
    if t == "select":
        return v["name"] if v else ""
    if t == "date":
        return v["start"] if v else ""
    return ""


def query_all():
    out, cur = [], None
    while True:
        b = {"page_size": 100}
        if cur:
            b["start_cursor"] = cur
        req = urllib.request.Request(
            f"https://api.notion.com/v1/databases/{DBID}/query",
            data=json.dumps(b).encode(),
            headers=H,
            method="POST",
        )
        d = json.load(urllib.request.urlopen(req))
        out += d["results"]
        if not d.get("has_more"):
            break
        cur = d["next_cursor"]
    return out


def next_birthday(birth, today):
    m, d = birth.month, birth.day
    if m == 2 and d == 29:  # 非閏年落到 2/28

        def leap(y):
            return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)

        for y in (today.year, today.year + 1):
            dd = 29 if leap(y) else 28
            cand = date(y, 2, dd)
            if cand >= today:
                return cand
        return date(today.year, 2, 28)
    nb = date(today.year, m, d)
    if nb < today:
        nb = date(today.year + 1, m, d)
    return nb


def main():
    today = date.today()
    hits = []
    for row in query_all():
        p = row["properties"]
        g = lambda k: val(p[k]) if k in p else ""
        bday, name, phone = g("生日"), g("姓名"), g("手機電話")
        if not bday:
            continue
        try:
            b = datetime.strptime(bday[:10], "%Y-%m-%d").date()
        except Exception:
            continue
        nb = next_birthday(b, today)
        days = (nb - today).days
        if days <= WINDOW:
            hits.append(
                {
                    "name": name,
                    "phone": phone,
                    "date": nb.isoformat(),
                    "days": days,
                    "age": nb.year - b.year,
                }
            )
    hits.sort(key=lambda x: x["days"])

    lines = [
        f"# 🎂 壽險客戶生日提醒 {today}",
        "",
        f"> 未來 {WINDOW} 天內生日｜資料來源：Notion 壽險客戶名單",
        "",
        f"## 🎉 即將生日（{len(hits)} 位）",
    ]
    if hits:
        lines += [
            "",
            "| 客戶 | 生日 | 還有 | 歲數 | 電話 |",
            "|------|------|------|------|------|",
        ]
        for c in hits:
            when = "🎂 今天！" if c["days"] == 0 else f"{c['days']} 天後"
            lines.append(
                f"| {c['name']} | {c['date'][5:]} | {when} | {c['age']} 歲 | {c['phone'] or '—'} |"
            )
    else:
        lines.append("\n（未來 " + str(WINDOW) + " 天內無客戶生日）")
    report = "\n".join(lines)
    print(report, flush=True)

    if hits and GMAIL_PW:
        msg = MIMEText(report.replace("\n", "<br>"), "html", "utf-8")
        msg["Subject"] = f"🎂 壽險客戶生日提醒：{len(hits)} 位即將生日（{today}）"
        msg["From"] = formataddr(("磊山保經 生日提醒", ADDR))
        msg["To"] = ADDR
        with smtplib.SMTP_SSL(
            "smtp.gmail.com", 465, context=ssl.create_default_context()
        ) as s:
            s.login(ADDR, GMAIL_PW)
            s.send_message(msg)
        print(f"✅ 已寄生日提醒 Email（{len(hits)} 位）", flush=True)
    elif not hits:
        print("窗口內無生日，不寄信", flush=True)
    else:
        print("⚠️ 未設 GMAIL_APP_PASSWORD，跳過寄信", flush=True)


if __name__ == "__main__":
    main()
