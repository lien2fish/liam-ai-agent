#!/usr/bin/env python3
"""
產險保單到期提醒
每日讀取 insurance/active_policies.json（已去重複的有效保單清單），
找出「下次續保日」落在接下來 14 天內的保單，寫報告 + 寄信通知。
"""
import json
import os
import smtplib
from datetime import date, datetime
from email.mime.text import MIMEText
from pathlib import Path

GMAIL_USER = os.environ.get("GMAIL_USER", "lien2fish@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

WORKSPACE = Path(
    os.environ.get("GITHUB_WORKSPACE", Path(__file__).resolve().parent.parent)
)
POLICIES_PATH = WORKSPACE / "insurance" / "active_policies.json"
REPORTS_DIR = WORKSPACE / "reports"

REMINDER_WINDOW_DAYS = 14


def parse_date(s: str) -> date:
    y, m, d = map(int, s.split("-"))
    return date(y, m, d)


def next_renewal(effective_date_str: str, today: date) -> date:
    d = parse_date(effective_date_str)
    try:
        nd = d.replace(year=today.year)
    except ValueError:
        nd = d.replace(year=today.year, day=28)
    while nd < today:
        try:
            nd = nd.replace(year=nd.year + 1)
        except ValueError:
            nd = nd.replace(year=nd.year + 1, day=28)
    return nd


def send_email(subject, body):
    if not GMAIL_APP_PASSWORD:
        print("⚠️ 未設定 GMAIL_APP_PASSWORD，略過寄信")
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)


def main():
    today = date.today()
    if not POLICIES_PATH.exists():
        print(f"⚠️ 找不到 {POLICIES_PATH}，略過檢查")
        return

    policies = json.loads(POLICIES_PATH.read_text(encoding="utf-8"))

    due = []
    for p in policies:
        renewal = next_renewal(p["生效日"], today)
        days_left = (renewal - today).days
        if 0 <= days_left <= REMINDER_WINDOW_DAYS:
            due.append({**p, "下次續保日": renewal.isoformat(), "剩餘天數": days_left})

    due.sort(key=lambda x: x["剩餘天數"])

    lines = [f"# 📋 產險保單到期提醒 {today.isoformat()}", ""]
    if not due:
        lines.append("接下來 14 天內沒有保單需要續保。")
    else:
        lines.append(f"接下來 14 天內共有 {len(due)} 筆保單即將續保：")
        lines.append("")
        lines.append(
            "| 要保人 | 被保險人 | 保險公司 | 保單號碼 | 下次續保日 | 剩餘天數 |"
        )
        lines.append("|--------|---------|---------|---------|-----------|---------|")
        for p in due:
            lines.append(
                f"| {p['要保人']} | {p['被保險人']} | {p['保險公司']} | {p['保單號碼']} "
                f"| {p['下次續保日']} | {p['剩餘天數']} 天 |"
            )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"產險到期提醒_{today.isoformat()}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"報告已輸出：{report_path}")

    if due:
        body = "\n".join(
            f"{p['要保人']}（{p['被保險人']}）| {p['保險公司']} | {p['保單號碼']} "
            f"| 續保日 {p['下次續保日']}（剩 {p['剩餘天數']} 天）"
            for p in due
        )
        send_email(f"📋 產險保單到期提醒 - {len(due)} 筆即將續保", body)
        print(f"提醒信已處理，共 {len(due)} 筆")
    else:
        print("無到期保單，不寄信")


if __name__ == "__main__":
    main()
