#!/usr/bin/env python3
"""壽險客戶固定拜訪提醒：讀 Notion 名單，算下次拜訪日，本週到期則 Email。

上次拜訪日 + 拜訪週期(每季3/每半年6/每年12) = 下次拜訪日。
上次拜訪日空 = 待首次安排。到期窗口 REMINDER_DAYS（預設7）。
⚠️ repo 為 public，報告只寄 Email、不寫入 repo。
"""
import json, os, smtplib, ssl, urllib.request
from datetime import date, datetime, timedelta
from email.mime.text import MIMEText
from email.utils import formataddr

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "visit_config.json")))
DBID = CFG["life_clients_db"]
REMINDER_DAYS = int(os.environ.get("VISIT_REMINDER_DAYS", CFG.get("reminder_days", 7)))
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
MONTHS = {"每季": 3, "每半年": 6, "每年": 12}


def val(prop):
    t = prop["type"]
    v = prop[t]
    if t in ("title", "rich_text"):
        return "".join(x["plain_text"] for x in v)
    if t in ("phone_number",):
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
        body = {"page_size": 100}
        if cur:
            body["start_cursor"] = cur
        req = urllib.request.Request(
            f"https://api.notion.com/v1/databases/{DBID}/query",
            data=json.dumps(body).encode(),
            headers=H,
            method="POST",
        )
        d = json.load(urllib.request.urlopen(req))
        out += d["results"]
        if not d.get("has_more"):
            break
        cur = d["next_cursor"]
    return out


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
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        data=json.dumps(
            {"properties": {"下次拜訪日": {"date": {"start": iso}}}}
        ).encode(),
        headers=H,
        method="PATCH",
    )
    urllib.request.urlopen(req)


def main():
    today = date.today()
    due, never = [], 0
    for row in query_all():
        p = row["properties"]
        g = lambda k: val(p[k]) if k in p else ""
        name, phone = g("姓名"), g("手機電話")
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
        f"> 到期窗口：{REMINDER_DAYS} 天內｜週期預設每半年｜資料來源：Notion 壽險客戶名單",
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
        msg["From"] = formataddr(("磊山保經 拜訪系統", ADDR))
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
