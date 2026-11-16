#!/usr/bin/env python3
"""回購提醒：掃描炘和客戶，找出超過門檻天數未回購的客戶，Email 通知。

2026-11-16 起改讀 Notion「炘和客戶」（原本讀鉅鑫全品牌客戶總表）。
- 門檻天數 REPURCHASE_DAYS（預設 60），可用環境變數調整
- 只提醒「曾購買過、但距今超過門檻」的客戶（回購對象）
- 所有客戶都列入；勾了「拒絕行銷」的人跳過（個資法第 20 條：客人拒絕就要停止）

## 每日行動隊列（2026-10-13 起，11-16 改炘和版）

| 項目 | 規則 |
|---|---|
| 挑人 | `最後下單日` 空 且 `拒絕行銷` 未勾 |
| 排序 | 建檔日最舊優先（Notion 的 `created_time`） |
| 上限 | 每天 **3 位**（`QUEUE_LIMIT` 可調）|
| 通知 | **LINE 推播**，不是 Email——要當天做的事必須推到手機 |

⚠️ 內容含客戶姓名，**只走 LINE 推播、Email 與本機報告，不 commit**
（workflow 刻意不 commit 報告，見 .github/workflows/repurchase_reminder.yml）。
"""
import os, smtplib, ssl, sys
from datetime import datetime, date
from email.mime.text import MIMEText
from email.utils import formataddr

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))
from xinhe_crm.notion import getter, query_all  # noqa: E402

REMINDER_DAYS = int(os.environ.get("REPURCHASE_DAYS", "60"))
GMAIL_PW = os.environ.get("GMAIL_APP_PASSWORD", "")
ADDR = "lien2fish@gmail.com"
QUEUE_LIMIT = int(os.environ.get("QUEUE_LIMIT", "3"))


def build_queue(rows):
    """每日行動隊列：從未下單、且沒拒絕行銷的人，建檔最舊的前 N 位。"""
    pool = []
    for row in rows:
        g = getter(row)
        if g("最後下單日") or g("拒絕行銷") is True:
            continue
        pool.append(
            {
                "name": g("姓名"),
                "lines": "、".join(g("品類") or []) or g("來源") or "—",
                "phone": g("手機"),
                "created": (row.get("created_time") or "")[:10],
                "action": "補電話" if not g("手機") else "首次接觸",
            }
        )
    pool.sort(key=lambda x: x["created"] or "9999")
    return pool[:QUEUE_LIMIT], len(pool)


def queue_message(queue, pool_size, today):
    head = f"📋 今日行動隊列 {today}　{len(queue)}/{pool_size} 位"
    body = []
    for i, c in enumerate(queue, 1):
        body.append(
            f"{i}. {c['name']}（{c['lines']}）\n"
            f"   建檔 {c['created'] or '—'}　→ {c['action']}"
        )
    tail = "聯繫過就在 Notion 備註記一筆；下單後會自動離開隊列。"
    return "\n".join([head, ""] + body + ["", tail])


def due_table(rows):
    out = [
        "",
        "| 客戶 | 品類 | 距上次下單 | 類型 | 電話 |",
        "|------|------|-----------|------|------|",
    ]
    for c in rows:
        out.append(
            f"| {c['name']} | {c['lines'] or '—'} | **{c['days']} 天** | {c['kind'] or '—'} | {c['phone'] or '—'} |"
        )
    return out


def main():
    today = date.today()
    rows = query_all("customer_db")
    due = []
    for row in rows:
        g = getter(row)
        last = g("最後下單日")
        if not last or g("拒絕行銷") is True:
            continue
        d = (today - datetime.strptime(last[:10], "%Y-%m-%d").date()).days
        if d > REMINDER_DAYS:
            due.append(
                {
                    "name": g("姓名"),
                    "lines": "、".join(g("品類") or []),
                    "phone": g("手機"),
                    "kind": g("客戶類型"),
                    "days": d,
                }
            )
    due.sort(key=lambda x: -x["days"])
    queue, pool_size = build_queue(rows)

    lines = [
        f"# 🔔 炘和回購提醒 {today}",
        "",
        f"> 門檻：超過 **{REMINDER_DAYS} 天**未回購｜資料來源：Notion 炘和客戶",
        "",
        f"## ⏰ 待回購客戶（{len(due)} 位）",
    ]
    lines += due_table(due) if due else ["", "（目前無超過門檻的客戶）"]
    lines += [
        "",
        f"## 📋 今日行動隊列（{len(queue)}/{pool_size} 位，每天上限 {QUEUE_LIMIT}）",
    ]
    if queue:
        lines += [
            "",
            "| # | 客戶 | 品類／來源 | 建檔日 | 建議動作 |",
            "|---|------|-----------|--------|---------|",
        ]
        for i, c in enumerate(queue, 1):
            lines.append(
                f"| {i} | {c['name']} | {c['lines']} | {c['created'] or '—'} | **{c['action']}** |"
            )
    else:
        lines.append("\n（沒有還沒下過單、且未拒絕行銷的人）")
    report = "\n".join(lines)

    out = os.path.join(BASE, "..", "reports", f"回購提醒_{today}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"報告已寫入 {out}")
    print(f"待回購 {len(due)} 位、行動隊列 {len(queue)}/{pool_size} 位")

    if queue:
        from line_assistant.notify import notify

        if notify(queue_message(queue, pool_size, today)):
            print(f"✅ 已推 LINE：{len(queue)} 位行動隊列")
        else:
            print("⚠️ 未設 LINE_NOTIFY_URL／TOKEN，跳過推播（本機測試正常）")

    if due and GMAIL_PW:
        html = report.replace("\n", "<br>")
        msg = MIMEText(html, "html", "utf-8")
        msg["Subject"] = f"🔔 炘和回購提醒：{len(due)} 位客戶待跟進（{today}）"
        msg["From"] = formataddr(("炘和 CRM", ADDR))
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
