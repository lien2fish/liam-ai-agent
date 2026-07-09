#!/usr/bin/env python3
"""營收衝刺 週報：每週一 Email 本週壽險該接觸的客戶名單＋話術。

A組＝未來 14 天內生日的待拜訪客戶（生日祝賀切入）。
B組＝壽產/壽產團待拜訪客戶，依週次輪替每週 6 位（保單健檢＋交叉銷售），避免每週重複同一批。
⚠️ repo 為 public，含客戶姓名/電話，只寄 Email、不寫入 repo。
"""
import json, os, smtplib, ssl, urllib.request
from datetime import date
from email.mime.text import MIMEText
from email.utils import formataddr

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "visit_config.json")))
DBID = CFG["life_clients_db"]
BDAY_WINDOW = 14
B_PER_WEEK = 6
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


def days_to_birthday(bday, today):
    if not bday:
        return None
    try:
        _, m, d = (int(x) for x in bday[:10].split("-"))
    except ValueError:
        return None
    for yy in (today.year, today.year + 1):
        try:
            nb = date(yy, m, d)
        except ValueError:
            nb = date(yy, m, 28)
        if nb >= today:
            return (nb - today).days
    return None


def main():
    today = date.today()
    week = today.isocalendar()[1]
    clients = []
    for row in query_all():
        p = row["properties"]
        g = lambda k: val(p[k]) if k in p else ""
        if g("拜訪狀態") == "暫緩":
            continue
        if g("上次拜訪日"):  # 已排過拜訪，交給每日拜訪提醒系統
            continue
        phone = g("手機電話")
        if not phone:
            continue
        clients.append(
            {
                "name": g("姓名"),
                "phone": phone,
                "type": g("保單類型"),
                "age": g("年齡"),
                "bday": g("生日"),
                "d2b": days_to_birthday(g("生日"), today),
            }
        )

    a_list = sorted(
        [c for c in clients if c["d2b"] is not None and c["d2b"] <= BDAY_WINDOW],
        key=lambda x: x["d2b"],
    )
    a_names = {c["name"] for c in a_list}
    b_pool = sorted(
        [
            c
            for c in clients
            if c["type"] in ("壽產", "壽產團") and c["name"] not in a_names
        ],
        key=lambda x: x["name"],
    )
    b_list = []
    if b_pool:
        start = (week * B_PER_WEEK) % len(b_pool)
        b_list = [
            b_pool[(start + i) % len(b_pool)]
            for i in range(min(B_PER_WEEK, len(b_pool)))
        ]

    html = build_html(today, week, a_list, b_list)
    print(f"A組生日切入 {len(a_list)} 位、B組保單健檢 {len(b_list)} 位", flush=True)

    if GMAIL_PW and (a_list or b_list):
        msg = MIMEText(html, "html", "utf-8")
        msg["Subject"] = f"📋 營收衝刺週報 · 本週壽險名單（{today}）"
        msg["From"] = formataddr(("鉅鑫 營收衝刺", ADDR))
        msg["To"] = ADDR
        with smtplib.SMTP_SSL(
            "smtp.gmail.com", 465, context=ssl.create_default_context()
        ) as s:
            s.login(ADDR, GMAIL_PW)
            s.send_message(msg)
        print("✅ 已寄營收衝刺週報 Email", flush=True)
    elif not GMAIL_PW:
        print("⚠️ 未設 GMAIL_APP_PASSWORD，跳過寄信（以下為預覽）\n", flush=True)
        print(html, flush=True)


def _rows_a(a_list):
    out = []
    for i, c in enumerate(a_list):
        bg = "#DEEAF1" if i % 2 else "#fff"
        note = (
            " ⚠️打家長" if isinstance(c["age"], (int, float)) and c["age"] < 18 else ""
        )
        out.append(
            f'<tr style="background:{bg}"><td align="center"><b>{c["d2b"]}天</b></td>'
            f'<td>{c["name"]}{note}</td><td align="center">{c["type"]}</td>'
            f'<td align="center">{c["bday"][:10]}</td><td>{c["phone"]}</td></tr>'
        )
    return "".join(out)


def _rows_b(b_list):
    out = []
    for i, c in enumerate(b_list):
        bg = "#DEEAF1" if i % 2 else "#fff"
        out.append(
            f'<tr style="background:{bg}"><td>{c["name"]}</td>'
            f'<td align="center">{c["type"]}</td><td align="center">{c["age"]}</td>'
            f'<td>{c["phone"]}</td></tr>'
        )
    return "".join(out)


def build_html(today, week, a_list, b_list):
    a_section = (
        f"""<h3 style="color:#1F4E79;border-bottom:2px solid #DEEAF1;padding-bottom:4px">A組 · 生日祝賀切入（未來 {BDAY_WINDOW} 天生日）</h3>
<table style="border-collapse:collapse;width:100%;font-size:14px">
<tr style="background:#1F4E79;color:#fff"><th style="padding:6px">倒數</th><th>姓名</th><th>保單</th><th>生日</th><th>電話</th></tr>
{_rows_a(a_list)}</table>"""
        if a_list
        else '<h3 style="color:#1F4E79">A組 · 生日祝賀切入</h3><p>本週無 14 天內生日客戶。</p>'
    )
    b_section = (
        f"""<h3 style="color:#1F4E79;border-bottom:2px solid #DEEAF1;padding-bottom:4px;margin-top:24px">B組 · 保單健檢＋交叉銷售（壽產，本週輪替）</h3>
<table style="border-collapse:collapse;width:100%;font-size:14px">
<tr style="background:#1F4E79;color:#fff"><th style="padding:6px">姓名</th><th>保單</th><th>齡</th><th>電話</th></tr>
{_rows_b(b_list)}</table>"""
        if b_list
        else ""
    )
    return f"""<div style="font-family:-apple-system,'PingFang TC',sans-serif;max-width:640px;color:#222;line-height:1.6">
<h2 style="color:#1F4E79;margin-bottom:4px">📈 營收衝刺週報 · 第 {week} 週</h2>
<p style="color:#888;margin-top:0">{today}｜誘因：喬遷慶全品牌 85 折</p>
{a_section}
{b_section}
<h3 style="color:#1F4E79;margin-top:24px">🗣 話術</h3>
<p><b>A組·生日切入</b><br>「〇〇您好，我是鉅鑫連傳正。看您這兩天生日，先跟您說聲<b>生日快樂</b>！剛好年中，順便關心一下您保單這半年有沒有需要調整。另外公司剛喬遷，想送您一份龜吼現流海鮮嚐鮮、全品牌也有喬遷慶 85 折，改天拿給您順便聊聊。」</p>
<p><b>B組·保單健檢</b><br>「〇〇您好，我是連傳正。年中幫老客戶做個<b>保單健檢</b>，看您壽險加產險保障夠不夠、有沒有重複或缺口，約 15 分鐘幫您對一下？順便跟您說公司喬遷了，喬遷慶全品牌 85 折。」</p>
<p style="color:#888;font-size:13px;margin-top:20px">打完後在 Notion 壽險DB 填「上次拜訪日」，系統自動接手排下次拜訪。<br>— Liam AI Agent</p>
</div>"""


if __name__ == "__main__":
    main()
