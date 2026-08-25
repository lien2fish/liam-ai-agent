#!/usr/bin/env python3
"""
IG／FB Token 到期與失效檢查

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

SKILL_HINT = (
    "修法：載入 <b>ig-fb-auto</b> skill 走〈IG Token 更新步驟〉——"
    "Graph API Explorer 勾滿六項權限、走完授權對話框、換長效、"
    "寫回 config/instagram_config.json 與 GitHub Secret IG_TOKEN。<br>"
    "⚠️ fb_exchange_token 換發救不了被作廢的 session，也不會延長資料存取權。"
)


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


def send_line(broken, warn):
    """LINE 只給結論與該做什麼，細節看 Email。push 計入 200 則／月額度。"""
    if broken:
        lines = [f"🔴 IG／FB Token 出問題（{len(broken)} 項）"]
        lines += [f"・{b}" for b in broken]
        lines += [
            "",
            "每日發文／留言回覆／限動預告三套已停擺。",
            "要用電腦走一次授權對話框，手機做不到。",
        ]
    else:
        lines = ["🟡 IG／FB Token 快到期"]
        lines += [f"・{w}" for w in warn]
        lines += ["", "重新授權要用電腦，手機做不到，找時間處理。"]
    notify("\n".join(lines))


def send_mail(broken, warn):
    if not GMAIL_PW:
        print("⚠️ 未設 GMAIL_APP_PASSWORD，跳過寄信")
        return

    if broken:
        subject = f"🔴 IG／FB Token 出問題（{len(broken)} 項）——自動化已經停擺"
    else:
        soonest = min(int(w.split("剩 ")[1].split(" 天")[0]) for w in warn)
        subject = f"🟡 IG／FB Token 剩 {soonest} 天到期，該重新授權了"

    lines = []
    if broken:
        lines += ["<b>🔴 已經壞了，現在就要修：</b>", ""]
        lines += [f"• {b}" for b in broken]
        lines += ["", "影響：每日發文、留言自動回覆、限動預告<b>三套一起停</b>。", ""]
    if warn:
        lines += ["<b>🟡 還能用，但快到期：</b>", ""]
        lines += [f"• {w}" for w in warn]
        lines += [""]
    lines += ["─" * 30, "", SKILL_HINT]

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

    for b in broken:
        print("🔴", b)
    for w in warn:
        print("🟡", w)
    if not broken and not warn:
        print("✅ Token 全部正常，且沒有接近到期")

    if broken or warn:
        send_mail(broken, warn)
        send_line(broken, warn)

    # 壞掉就讓 Actions 變紅，GitHub App 才會推播
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
