#!/usr/bin/env python3
"""炘和客戶生日提醒：讀 Notion「炘和客戶」，未來 N 天內生日的客戶 → Email。

2026-11-16 起改讀炘和客戶（含磊山保經匯入的保險客戶），原本讀鉅鑫 CRM 下的壽險名單。
所有客戶都列入；只有勾了「拒絕行銷」的人跳過（個資法第 20 條：客人拒絕就要停止）。
窗口 BIRTHDAY_DAYS（預設 7）。
⚠️ repo 為 public，客戶資料只寄 Email、不寫入 repo。
"""
import os
import smtplib
import ssl
import sys
from datetime import date, datetime
from email.mime.text import MIMEText
from email.utils import formataddr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xinhe_crm.notion import getter, query_all  # noqa: E402

WINDOW = int(os.environ.get("BIRTHDAY_DAYS", "7"))
GMAIL_PW = os.environ.get("GMAIL_APP_PASSWORD", "")
ADDR = "lien2fish@gmail.com"


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


def table(rows):
    out = [
        "",
        "| 客戶 | 生日 | 還有 | 歲數 | 來源 | 電話 |",
        "|------|------|------|------|------|------|",
    ]
    for c in rows:
        when = "🎂 今天！" if c["days"] == 0 else f"{c['days']} 天後"
        out.append(
            f"| {c['name']} | {c['date'][5:]} | {when} | {c['age']} 歲 | {c['source'] or '—'} | {c['phone'] or '—'} |"
        )
    return out


def main():
    today = date.today()
    hits = []
    for row in query_all("customer_db"):
        g = getter(row)
        bday = g("生日")
        if not bday or g("拒絕行銷") is True:
            continue
        try:
            b = datetime.strptime(bday[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        nb = next_birthday(b, today)
        days = (nb - today).days
        if days <= WINDOW:
            hits.append(
                {
                    "name": g("姓名"),
                    "phone": g("手機"),
                    "source": g("來源"),
                    "date": nb.isoformat(),
                    "days": days,
                    "age": nb.year - b.year,
                }
            )
    hits.sort(key=lambda x: x["days"])

    lines = [
        f"# 🎂 炘和客戶生日提醒 {today}",
        "",
        f"> 未來 {WINDOW} 天內生日｜資料來源：Notion 炘和客戶",
        "",
        f"## 🎉 即將生日（{len(hits)} 位）",
    ]
    lines += table(hits) if hits else ["", f"（未來 {WINDOW} 天內無客戶生日）"]
    report = "\n".join(lines)
    print(report, flush=True)

    if hits and GMAIL_PW:
        msg = MIMEText(report.replace("\n", "<br>"), "html", "utf-8")
        msg["Subject"] = f"🎂 炘和客戶生日提醒：{len(hits)} 位即將生日（{today}）"
        msg["From"] = formataddr(("炘和 CRM 生日提醒", ADDR))
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
