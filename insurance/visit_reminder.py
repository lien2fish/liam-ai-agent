#!/usr/bin/env python3
"""壽險客戶固定拜訪提醒：讀 Notion 炘和客戶，算下次拜訪日，本週到期則 Email。

2026-11-16 起改讀「炘和客戶」中有「保單類型」的人（磊山保經匯入），原本讀鉅鑫 CRM 下的壽險名單。
上次拜訪日 + 拜訪週期(每季3/每半年6/每年12) = 下次拜訪日。
上次拜訪日空 = 待首次安排。到期窗口 REMINDER_DAYS（預設7）。
⚠️ repo 為 public，報告只寄 Email、不寫入 repo。
"""
import os, smtplib, ssl, sys
from datetime import date, datetime
from email.mime.text import MIMEText
from email.utils import formataddr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xinhe_crm.notion import call, getter, query_all  # noqa: E402

REMINDER_DAYS = int(os.environ.get("VISIT_REMINDER_DAYS", "7"))
GMAIL_PW = os.environ.get("GMAIL_APP_PASSWORD", "")
ADDR = "lien2fish@gmail.com"
MONTHS = {"每季": 3, "每半年": 6, "每年": 12}


def add_months(d, m):
    y, mo = d.year + (d.month - 1 + m) // 12, (d.month - 1 + m) % 12 + 1
    day = min(
        d.day,
        [
            31,
            29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][mo - 1],
    )
    return date(y, mo, day)


def patch_next(page_id, iso):
    call(
        "PATCH",
        f"/pages/{page_id}",
        {"properties": {"下次拜訪日": {"date": {"start": iso}}}},
    )


def main():
    today = date.today()
    due, never = [], 0
    for row in query_all("customer_db"):
        g = getter(row)
        if not g("保單類型"):  # 只算保險客戶；海鮮／酒／茶客戶沒有拜訪排程
            continue
        name, phone = g("姓名"), g("手機")
        last, cyc, status = g("上次拜訪日"), g("拜訪週期") or "每半年", g("拜訪狀態")
        if status == "暫緩":
            continue
        if not last:
            never += 1
            continue
        nxt = add_months(
            datetime.strptime(last[:10], "%Y-%m-%d").date(), MONTHS.get(cyc, 6)
        )
        try:
            patch_next(row["id"], nxt.isoformat())
        except Exception:
            pass
        days = (nxt - today).days
        if days <= REMINDER_DAYS:
            due.append(
                {
                    "name": name,
                    "phone": phone,
                    "next": nxt.isoformat(),
                    "days": days,
                    "cyc": cyc,
                    "last": last,
                }
            )
    due.sort(key=lambda x: x["days"])

    lines = [
        f"# 🛡️ 壽險客戶固定拜訪提醒 {today}",
        "",
        f"> 到期窗口：{REMINDER_DAYS} 天內｜週期預設每半年｜資料來源：Notion 炘和客戶（有保單類型者）",
        "",
        f"## 📅 本週待拜訪（{len(due)} 位）",
    ]
    if due:
        lines += [
            "",
            "| 客戶 | 下次拜訪日 | 距今 | 週期 | 電話 |",
            "|------|-----------|------|------|------|",
        ]
        for c in due:
            tag = f"**逾期{-c['days']}天**" if c["days"] < 0 else f"{c['days']}天後"
            lines.append(
                f"| {c['name']} | {c['next']} | {tag} | {c['cyc']} | {c['phone'] or '—'} |"
            )
    else:
        lines.append("\n（本週無到期拜訪）")
    lines += [
        "",
        f"## 🆕 待首次安排（{never} 位）",
        "尚未填「上次拜訪日」的客戶，拜訪後在 Notion 填日期，系統即自動接手排程。",
    ]
    report = "\n".join(lines)
    print(report, flush=True)

    if due and GMAIL_PW:
        msg = MIMEText(report.replace("\n", "<br>"), "html", "utf-8")
        msg["Subject"] = f"🛡️ 壽險客戶拜訪提醒：{len(due)} 位本週待拜訪（{today}）"
        msg["From"] = formataddr(("炘和 CRM 拜訪提醒", ADDR))
        msg["To"] = ADDR
        with smtplib.SMTP_SSL(
            "smtp.gmail.com", 465, context=ssl.create_default_context()
        ) as s:
            s.login(ADDR, GMAIL_PW)
            s.send_message(msg)
        print(f"✅ 已寄拜訪提醒 Email（{len(due)} 位）", flush=True)
    elif not due:
        print("本週無到期拜訪，不寄信", flush=True)
    else:
        print("⚠️ 未設 GMAIL_APP_PASSWORD，跳過寄信", flush=True)


if __name__ == "__main__":
    main()
