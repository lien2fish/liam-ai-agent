#!/usr/bin/env python3
"""中城網路扶輪社社友生日提醒：生日前 14 天寄 Email。

資料來源＝私人 repo liam-workspace 的 rotary/中城網路社友通訊錄.json，
workflow 用 WORKSPACE_PAT checkout 到 workspace/ 後讀取。
⚠️ 本 repo 為 public，社友個資只存私人 repo、只走 Email，不 commit 報告。

觸發邏輯：距生日剛好 TRIGGER_DAYS（14）天 → 寄信；信中附未來 14 天生日總覽。
"""
import json, os, smtplib, ssl
from datetime import date, datetime
from email.mime.text import MIMEText
from email.utils import formataddr

TRIGGER_DAYS = int(os.environ.get("TRIGGER_DAYS", "14"))
JSON_PATH = os.environ.get(
    "ROTARY_JSON", os.path.join(os.getcwd(), "workspace/rotary/中城網路社友通訊錄.json")
)
GMAIL_PW = os.environ.get("GMAIL_APP_PASSWORD", "")
ADDR = "lien2fish@gmail.com"


def next_birthday(birth, today):
    m, d = birth.month, birth.day
    if m == 2 and d == 29:
        d = 28
    nb = date(today.year, m, d)
    if nb < today:
        nb = date(today.year + 1, m, d)
    return nb


def main():
    today = date.today()
    data = json.load(open(JSON_PATH))
    upcoming = []
    for mb in data["members"]:
        if not mb.get("birthday"):
            continue
        b = datetime.strptime(mb["birthday"], "%Y-%m-%d").date()
        nb = next_birthday(b, today)
        days = (nb - today).days
        if days <= TRIGGER_DAYS:
            upcoming.append(
                {
                    "name": mb["name"],
                    "nickname": mb["nickname"],
                    "phone": mb["phone"],
                    "date": nb.isoformat(),
                    "days": days,
                    "age": nb.year - b.year,
                }
            )
    upcoming.sort(key=lambda x: x["days"])
    triggers = [c for c in upcoming if c["days"] == TRIGGER_DAYS]

    lines = [
        f"# 🎂 中城網路扶輪社 社友生日提醒 {today}",
        "",
        f"> 生日前 {TRIGGER_DAYS} 天提醒｜{data['club']}",
    ]
    if triggers:
        names = "、".join(f"{c['name']}（{c['nickname']}）" for c in triggers)
        lines += ["", f"## 🔔 兩週後生日：{names}"]
    if upcoming:
        lines += [
            "",
            f"## 📅 未來 {TRIGGER_DAYS} 天內生日（{len(upcoming)} 位）",
            "",
            "| 社友 | Nickname | 生日 | 還有 | 歲數 | 電話 |",
            "|------|----------|------|------|------|------|",
        ]
        for c in upcoming:
            when = "🎂 今天！" if c["days"] == 0 else f"{c['days']} 天後"
            lines.append(
                f"| {c['name']} | {c['nickname']} | {c['date'][5:]} | {when} "
                f"| {c['age']} 歲 | {c['phone'] or '—'} |"
            )
    else:
        lines.append(f"\n（未來 {TRIGGER_DAYS} 天內無社友生日）")
    report = "\n".join(lines)
    print(report, flush=True)

    if triggers and GMAIL_PW:
        msg = MIMEText(report.replace("\n", "<br>"), "html", "utf-8")
        names = "、".join(f"{c['nickname']}" for c in triggers)
        msg["Subject"] = f"🎂 扶輪社友生日提醒：{names} 兩週後生日（{today}）"
        msg["From"] = formataddr(("中城網路扶輪社 生日提醒", ADDR))
        msg["To"] = ADDR
        with smtplib.SMTP_SSL(
            "smtp.gmail.com", 465, context=ssl.create_default_context()
        ) as s:
            s.login(ADDR, GMAIL_PW)
            s.send_message(msg)
        print(f"✅ Email 已寄出（{len(triggers)} 位觸發）", flush=True)
    elif not triggers:
        print("今日無剛好 14 天後生日的社友，不寄信", flush=True)


if __name__ == "__main__":
    main()
