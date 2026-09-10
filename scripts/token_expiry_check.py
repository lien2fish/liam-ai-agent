#!/usr/bin/env python3
"""
金鑰失效與到期檢查（IG／FB／Notion）

不寫死到期日——每天向 debug_token 問實際狀態，所以換發後不用改程式。
順便涵蓋 2026-08-25 那次的死法：session 被作廢（190/460），跟到期日無關。
"""

import json, os, smtplib, ssl, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.utils import formataddr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from line_assistant.notify import notify

GRAPH_API = "https://graph.facebook.com/v19.0"
GMAIL_PW = os.environ.get("GMAIL_APP_PASSWORD", "")
ADDR = "lien2fish@gmail.com"

IG_TOKEN = os.environ.get("IG_TOKEN", "")
IG_ID = os.environ.get("IG_ID", "")
FB_PAGE_TOKEN = os.environ.get("FB_PAGE_TOKEN", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")

NOTION_API = "https://api.notion.com/v1"

# Notion 有兩種死法，只驗 token 有效只抓得到第一種：
#   ① secret 被撤銷或 integration 被刪 → 每次呼叫都 401
#   ② integration 還在、token 也有效，但被移出頁面 → 業務查詢全部 404
# 2026-09-10 那次是 ①＋②（integration 整個被刪），六個 workflow 與 LINE 助理一起停。
# 所以要實際打真正在用的資料庫，不能只打 users/me。
NOTION_PROBES = {
    "全品牌客戶總表": "38bf4149a6aa816e9850f3dfbbb925ec",
    "全品牌銷售紀錄": "38bf4149a6aa81db9b89c47410857a2c",
    "壽險客戶名單": "390f4149a6aa81bf98e1c3bffc0caad2",
}

# 重新授權要本人開瀏覽器，不能等到最後一天才說
NOTIFY_DAYS = {30, 21, 14, 10, 7, 5, 3, 2, 1}

REQUIRED_SCOPES = [
    "instagram_basic",
    "instagram_content_publish",
    "instagram_manage_comments",
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
]

HINT_IGFB = (
    "修法：載入 <b>ig-fb-auto</b> skill 走〈IG Token 更新步驟〉——"
    "Graph API Explorer 勾滿六項權限、走完授權對話框、換長效、"
    "寫回 config/instagram_config.json 與 GitHub Secret IG_TOKEN。<br>"
    "⚠️ fb_exchange_token 換發救不了被作廢的 session，也不會延長資料存取權。"
)

HINT_NOTION = (
    "修法：載入 <b>secrets-ops</b> skill——到 notion.so/profile/integrations 的"
    "〈連接〉分頁（不是〈個人存取權杖〉）確認 integration 還在，"
    "重產 Internal Integration Secret（<code>ntn_</code> 開頭）。<br>"
    "⚠️ 授權靠父頁面繼承：把 integration 連上「鉅鑫管理顧問 CRM」即涵蓋底下全部資料庫。<br>"
    "⚠️ <b>GitHub Secret 與 Cloudflare Worker 兩邊都要換</b>，只換一邊 LINE 助理會靜默失效。"
)

IMPACT = {
    "IG_TOKEN": "每日發文、留言自動回覆、限動預告<b>三套一起停</b>",
    "FB_PAGE_TOKEN": "目前沒有腳本真的在用（FB 跨發走 IG 的 cross_post_ids），影響最小",
    "NOTION_TOKEN": (
        "壽險生日與拜訪提醒、回購提醒、市場日報、漁獲行情、Notion 月報，"
        "<b>＋LINE 助理的 /客戶 /買 /庫存</b>"
    ),
}


def impacted(items):
    return [v for k, v in IMPACT.items() if any(x.startswith(k) for x in items)]


def graph(path, params):
    url = f"{GRAPH_API}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=25) as r:
        return json.loads(r.read())


def err_detail(e):
    try:
        d = json.loads(e.read().decode())["error"]
        sub = f" / subcode {d['error_subcode']}" if d.get("error_subcode") else ""
        return f"code {d.get('code')}{sub}：{d.get('message', '')}"
    except Exception:
        return f"HTTP {e.code}"


def days_left(ts):
    """回傳剩餘天數；0 代表永不過期，回 None。"""
    if not ts:
        return None
    delta = datetime.fromtimestamp(ts, timezone.utc) - datetime.now(timezone.utc)
    return delta.days


def check_expiry(label, name, ts, broken, warn):
    d = days_left(ts)
    if d is None:
        return
    when = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
    if d < 0:
        broken.append(f"{label} 的 {name} 已經過期（{when}）")
    elif d == 0:
        broken.append(f"{label} 的 {name} 今天就到期（{when}）")
    elif d in NOTIFY_DAYS:
        warn.append(f"{label} 的 {name} 剩 {d} 天（{when} 到期）")


def check_token(label, token, smoke_path, broken, warn, need_scopes=False):
    if not token:
        broken.append(f"{label} 沒有設定——workflow 的 secret 是空的")
        return

    try:
        data = graph("debug_token", {"input_token": token, "access_token": token})[
            "data"
        ]
    except urllib.error.HTTPError as e:
        broken.append(f"{label} 已失效——{err_detail(e)}")
        return

    if not data.get("is_valid"):
        broken.append(f"{label} 被判定為 invalid")
        return

    if need_scopes:
        missing = [s for s in REQUIRED_SCOPES if s not in data.get("scopes", [])]
        if missing:
            broken.append(f"{label} 缺少權限：{'、'.join(missing)}")

    # debug_token 說沒事不代表真的能用，實際打一次才算數
    try:
        graph(smoke_path, {"fields": "id", "limit": "1", "access_token": token})
    except urllib.error.HTTPError as e:
        broken.append(f"{label} 實際呼叫失敗——{err_detail(e)}")
        return

    check_expiry(
        label, "token 本身（expires_at）", data.get("expires_at"), broken, warn
    )
    check_expiry(
        label,
        "資料存取權（data_access_expires_at）",
        data.get("data_access_expires_at"),
        broken,
        warn,
    )


def notion_get(path):
    req = urllib.request.Request(
        f"{NOTION_API}/{path}",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def check_notion(broken):
    """integration secret 沒有到期日，只會突然失效，所以不做 warn。"""
    label = "NOTION_TOKEN"
    if not NOTION_TOKEN:
        broken.append(f"{label} 沒有設定——workflow 的 secret 是空的")
        return

    try:
        notion_get("users/me")
    except urllib.error.HTTPError as e:
        broken.append(
            f"{label} 已失效（HTTP {e.code}）——secret 被撤銷或 integration 被刪除"
        )
        return

    lost = []
    for name, did in NOTION_PROBES.items():
        try:
            notion_get(f"databases/{did}")
        except urllib.error.HTTPError as e:
            lost.append(f"{name}（HTTP {e.code}）")

    if lost:
        broken.append(
            f"{label} 本身有效，但讀不到 {len(lost)} 個資料庫："
            f"{'、'.join(lost)}——integration 沒有連上父頁面"
        )


def send_line(broken, warn):
    """LINE 只給結論與該做什麼，細節看 Email。push 計入 200 則／月額度。"""
    if broken:
        lines = [f"🔴 金鑰出問題（{len(broken)} 項）"]
        lines += [f"・{b}" for b in broken]
        impact = [i.replace("<b>", "").replace("</b>", "") for i in impacted(broken)]
        if impact:
            lines += [""] + [f"影響：{i}" for i in impact]
        lines += ["", "修復要用電腦，手機做不到。"]
    else:
        lines = ["🟡 Token 快到期"]
        lines += [f"・{w}" for w in warn]
        lines += ["", "重新授權要用電腦，手機做不到，找時間處理。"]
    notify("\n".join(lines))


def send_mail(broken, warn):
    if not GMAIL_PW:
        print("⚠️ 未設 GMAIL_APP_PASSWORD，跳過寄信")
        return

    if broken:
        subject = f"🔴 金鑰出問題（{len(broken)} 項）——自動化已經停擺"
    else:
        soonest = min(int(w.split("剩 ")[1].split(" 天")[0]) for w in warn)
        subject = f"🟡 Token 剩 {soonest} 天到期，該重新授權了"

    lines = []
    if broken:
        lines += ["<b>🔴 已經壞了，現在就要修：</b>", ""]
        lines += [f"• {b}" for b in broken]
        lines += [""] + [f"影響：{i}。" for i in impacted(broken)] + [""]
    if warn:
        lines += ["<b>🟡 還能用，但快到期：</b>", ""]
        lines += [f"• {w}" for w in warn]
        lines += [""]
    hints = []
    if any(x.startswith(("IG_TOKEN", "FB_PAGE_TOKEN")) for x in broken + warn):
        hints.append(HINT_IGFB)
    if any(x.startswith("NOTION_TOKEN") for x in broken):
        hints.append(HINT_NOTION)
    lines += ["─" * 30, "", "<br>".join(hints)]

    msg = MIMEText("<br>".join(lines), "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("Token 到期提醒", ADDR))
    msg["To"] = ADDR
    with smtplib.SMTP_SSL(
        "smtp.gmail.com", 465, context=ssl.create_default_context()
    ) as s:
        s.login(ADDR, GMAIL_PW)
        s.send_message(msg)
    print(f"📧 已寄出（壞 {len(broken)} 項、快到期 {len(warn)} 項）")


def main():
    broken, warn = [], []

    check_token("IG_TOKEN", IG_TOKEN, f"{IG_ID}/media", broken, warn, need_scopes=True)
    check_token("FB_PAGE_TOKEN", FB_PAGE_TOKEN, "me", broken, warn)
    check_notion(broken)

    for b in broken:
        print("🔴", b)
    for w in warn:
        print("🟡", w)
    if not broken and not warn:
        print("✅ IG／FB／Notion 全部正常，且沒有接近到期")

    if broken or warn:
        send_mail(broken, warn)
        send_line(broken, warn)

    # 壞掉就讓 Actions 變紅，GitHub App 才會推播
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
