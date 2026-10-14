#!/usr/bin/env python3
"""回購提醒：掃描全品牌客戶總表，找出超過門檻天數未回購的客戶，Email 通知。

- 門檻天數 REPURCHASE_DAYS（預設 60），可用環境變數調整
- 只提醒「曾購買過、但距今超過門檻」的客戶（回購對象）
- 認證沿用既有系統：NOTION_TOKEN / GMAIL_APP_PASSWORD（與保單提醒同一套）

## 2026-10-13 新增：每日行動隊列（改版階段 1）

原本「從未消費」是一整區 29 位的參考清單，**等於沒有行動指示**——
一人公司收到 29 位名單會一位都不做。改成每天只給 3 位、推到 LINE。

| 項目 | 規則 |
|---|---|
| 挑人 | `最後購買日` 空 且 `接觸狀態` = 未接觸 且 `拒絕行銷` 未勾 |
| 排序 | 建檔日最舊優先（Notion 的 `created_time`） |
| 上限 | 每天 **3 位**（`QUEUE_LIMIT` 可調）|
| 通知 | **LINE 推播**，不是 Email——要當天做的事必須推到手機 |
| 額度 | 每天 1 則 × 30 天 = 30 則／月，在輕用量 200 則／月內 |

⚠️ 隊列內容含客戶姓名，**只走 LINE 推播與本機報告，不 commit**
（workflow 刻意不 commit 報告，見 .github/workflows/repurchase_reminder.yml）。
"""
import urllib.request, json, os, smtplib, ssl, sys
from datetime import datetime, date
from email.mime.text import MIMEText
from email.utils import formataddr

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))
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
QUEUE_LIMIT = int(os.environ.get("QUEUE_LIMIT", "3"))


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
    if t == "checkbox":
        return bool(v)
    return ""


def build_queue(rows):
    """每日行動隊列：從未成交且未接觸過的人，建檔最舊的前 N 位。

    `拒絕行銷` 勾選者永久排除——那是個資法 §20 II 的要求，不是偏好設定。
    """
    pool = []
    for row in rows:
        p = row["properties"]
        g = lambda k: val(p[k]) if k in p else ""
        if g("最後購買日"):
            continue
        if g("接觸狀態") not in ("", "未接觸"):
            continue
        if g("拒絕行銷") is True:
            continue
        pool.append(
            {
                "name": g("客戶姓名"),
                "brand": g("品牌"),
                "phone": g("聯絡電話"),
                "created": (row.get("created_time") or "")[:10],
                "action": "補電話" if not g("聯絡電話") else "首次接觸",
            }
        )
    pool.sort(key=lambda x: x["created"] or "9999")
    return pool[:QUEUE_LIMIT], len(pool)


def queue_message(queue, pool_size, today):
    head = f"📋 今日行動隊列 {today}　{len(queue)}/{pool_size} 位"
    body = []
    for i, c in enumerate(queue, 1):
        body.append(
            f"{i}. {c['name']}（{c['brand']}）\n"
            f"   建檔 {c['created'] or '—'}　→ {c['action']}"
        )
    tail = "填完請把 Notion 的「接觸狀態」改掉，否則明天還是同三位。"
    return "\n".join([head, ""] + body + ["", tail])


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
    rows = query_all(CUST_DB)
    # 已移轉旭和的客人改由旭和聯繫，鉅鑫這邊不提醒，避免兩家公司重複找同一位（2026-10-14）
    rows = [
        r
        for r in rows
        if "已移轉旭和" not in r["properties"] or not val(r["properties"]["已移轉旭和"])
    ]
    due = []
    for row in rows:
        p = row["properties"]
        g = lambda k: val(p[k]) if k in p else ""
        last = g("最後購買日")
        if not last:
            continue
        d = (today - datetime.strptime(last[:10], "%Y-%m-%d").date()).days
        if d > REMINDER_DAYS:
            due.append(
                {
                    "name": g("客戶姓名"),
                    "brand": g("品牌"),
                    "phone": g("聯絡電話"),
                    "level": g("會員等級"),
                    "days": d,
                }
            )
    due.sort(key=lambda x: -x["days"])
    queue, pool_size = build_queue(rows)

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
    lines += [
        "",
        f"## 📋 今日行動隊列（{len(queue)}/{pool_size} 位，每天上限 {QUEUE_LIMIT}）",
    ]
    if queue:
        lines += [
            "",
            "| # | 客戶 | 品牌 | 建檔日 | 建議動作 |",
            "|---|------|------|--------|---------|",
        ]
        for i, c in enumerate(queue, 1):
            lines.append(
                f"| {i} | {c['name']} | {c['brand']} | {c['created'] or '—'} | **{c['action']}** |"
            )
        lines += [
            "",
            "> 做完請改 Notion 的「接觸狀態」，否則明天還是同三位。",
        ]
    else:
        lines.append("\n（沒有待接觸的人——未成交名單都已接觸過或已排除）")
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
