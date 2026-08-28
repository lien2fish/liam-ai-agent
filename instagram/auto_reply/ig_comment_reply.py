#!/usr/bin/env python3
"""
IG 留言自動回覆 - 輪詢版
本機 cron 或 GitHub Actions 皆可執行
"""

import json
import os
import smtplib
import ssl
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

# ── 路徑設定 ──────────────────────────────────────────────────────
# GitHub Actions 時使用 GITHUB_WORKSPACE，本機用預設路徑
WORKSPACE = Path(
    os.environ.get("GITHUB_WORKSPACE", "/Users/lien/Downloads/Liam AI agent")
)
CONFIG_FILE = WORKSPACE / "config/instagram_config.json"
STATE_FILE = WORKSPACE / "instagram/auto_reply/reply_state.json"
LOG_FILE = Path("/tmp/ig_comment_reply.log")

GRAPH_API = "https://graph.facebook.com/v19.0"
# ⚠️ 不要釘死版本號。2026-08-28 發現 gemini-2.0-flash 與 -flash-lite 都已 404 下架，
#    當時 2.5-flash 又剛好 503，於是整條 fallback 全滅——Claude 一掛就開天窗。
#    用 -latest 別名才不會被下架；503 是暫時性且會在模型間輪動，所以要留多個備援。
GEMINI_MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-flash-lite-latest"]
FALLBACK = "感謝支持 🐟"
MAX_IDS = 2000

GMAIL_PW = os.environ.get("GMAIL_APP_PASSWORD", "")
ADDR = "lien2fish@gmail.com"

# 問到價格、到貨、訂購的留言一律不自動回——AI 看不到照片也不知道當天行情，
# 護欄只能讓它不講錯，沒辦法讓它講對。報錯價格會有商業糾紛。
# 用關鍵字而非 AI 判斷：零成本（不吃 Gemini 額度）、可預測、可稽核。
NEEDS_HUMAN = [
    # 價格
    "多少錢",
    "價格",
    "價錢",
    "怎麼賣",
    "幾錢",
    "報價",
    "費用",
    "單價",
    "一斤多少",
    "多少一斤",
    "行情",
    "優惠",
    "折扣",
    "便宜",
    "貴嗎",
    # 訂購
    "怎麼買",
    "怎麼訂",
    "要買",
    "想買",
    "下單",
    "訂購",
    "預訂",
    "可以訂",
    "團購",
    # 到貨
    "什麼時候",
    "何時",
    "有貨",
    "到貨",
    "還有嗎",
    "缺貨",
    "補貨",
    "現貨",
    # 配送
    "宅配",
    "運費",
    "寄送",
    "出貨",
    "配送",
    "可以寄",
    "冷凍寄",
]


def needs_human(text):
    return any(k in text for k in NEEDS_HUMAN)


# ── 載入設定（env var 優先，本機用 config 檔）────────────────────
def load_config():
    ig_token = os.environ.get("IG_TOKEN")
    ig_id = os.environ.get("IG_ID")
    gemini_key = os.environ.get("GEMINI_KEY")

    if not all([ig_token, ig_id, gemini_key]):
        cfg = json.loads(CONFIG_FILE.read_text())
        ig_token = ig_token or cfg["long_lived_user_token"]
        ig_id = ig_id or cfg["ig_account_id"]
        gemini_key = gemini_key or cfg["gemini_api_key"]

    return ig_token, ig_id, gemini_key


IG_TOKEN, IG_ID, GEMINI_KEY = load_config()

# ── 工具函式 ──────────────────────────────────────────────────────


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    since = (datetime.now(timezone.utc) - timedelta(minutes=6)).strftime(
        "%Y-%m-%dT%H:%M:%S+0000"
    )
    return {"last_checked": since, "replied_ids": [], "notified_ids": []}


def save_state(state):
    state["replied_ids"] = state["replied_ids"][-MAX_IDS:]
    state["notified_ids"] = state.get("notified_ids", [])[-MAX_IDS:]
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def send_pending_mail(pending):
    """把需要人工回覆的留言寄給 Lien。"""
    if not GMAIL_PW:
        log("  ⚠️ 未設 GMAIL_APP_PASSWORD，跳過寄信")
        return

    lines = [
        f"<b>有 {len(pending)} 則留言需要你親自回。</b>",
        "",
        "這些留言問到價格、到貨或訂購，系統<b>沒有自動回覆</b>——",
        "AI 看不到照片也不知道當天行情，答錯價格會有糾紛。",
        "",
        "─" * 30,
    ]
    for p in pending:
        lines += [
            "",
            f"<b>@{p['user']}</b>　{p['time'][:16].replace('T', ' ')}",
            f"「{p['text']}」",
            f'<a href="{p["permalink"]}">→ 到 IG 回覆</a>' if p["permalink"] else "",
            "─" * 30,
        ]

    msg = MIMEText("<br>".join(lines), "html", "utf-8")
    msg["Subject"] = f"🔔 有 {len(pending)} 則 IG 留言要你親自回（問價格／到貨）"
    msg["From"] = formataddr(("IG 留言助理", ADDR))
    msg["To"] = ADDR
    with smtplib.SMTP_SSL(
        "smtp.gmail.com", 465, context=ssl.create_default_context()
    ) as s:
        s.login(ADDR, GMAIL_PW)
        s.send_message(msg)
    log(f"  📧 已寄出人工回覆提醒（{len(pending)} 則）")


def api_get(path, params=None):
    p = dict(params or {})
    p["access_token"] = IG_TOKEN
    url = f"{GRAPH_API}/{path}?{urllib.parse.urlencode(p)}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read())


def api_post(path, data=None):
    d = dict(data or {})
    d["access_token"] = IG_TOKEN
    req = urllib.request.Request(
        f"{GRAPH_API}/{path}", data=urllib.parse.urlencode(d).encode(), method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def gemini_reply(text):
    prompt = f"""你是連老闆，在新北市龜吼漁港做現流海鮮，跟 19 艘共捕漁船合作，
每天在碼頭看漁獲上岸。有人在你的 Instagram 貼文或 Reels 下方留言。

用繁體中文回一句，**像在跟朋友分享，不是在做客服**：
- 字數 15～25 字之間
- 講人話。可以直接、可以有自己的看法，不用客套也不用敬語
- 有相關的產地細節就順口提一句（什麼季節、怎麼分好壞、當天現場如何），沒有就單純回應
- 加 1 個相關 emoji
- 只輸出回覆內容本身，不要加引號或任何前綴說明

**絕對不要**做這些事：
- 不要推銷、不要引導私訊或購買
- 不要用「歡迎來訊討論」「有需求歡迎詢問」「歡迎私訊」這類收尾
- 不要說「感謝您的留言」這種客服開場
- 不要自稱「我們」或「本店」

**絕對不要編造事實**（這比語氣重要，寧可回得平淡也不能講錯）：
- **不講具體價格**——你不知道今天賣多少
- **不講具體日期、月份或到貨時間**——你不知道什麼時候有貨
- **不講留言裡沒提到的魚種名稱**——你看不到照片，不知道那是什麼
- 不確定的產季、規格、重量一律不提
- 問價格或到貨時間的，就照實說「這要看當天船況」之類，不要給數字

留言內容：{text}"""

    for model in GEMINI_MODELS:
        # 思考型模型（3.x / 2.5）關閉思考模式，避免 token 被內部推理佔光
        is_thinking_model = any(x in model for x in ["3.5", "3.1", "3-", "2.5"])
        config_extra = (
            {"thinkingConfig": {"thinkingBudget": 0}} if is_thinking_model else {}
        )

        payload = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": 256,
                    "temperature": 0.75,
                    **config_extra,
                },
            }
        ).encode()

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        req = urllib.request.Request(
            api_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            candidate = data["candidates"][0]
            reply = candidate["content"]["parts"][0]["text"].strip()
            if candidate.get("finishReason") == "MAX_TOKENS" or len(reply) < 8:
                log(f"  {model} 回覆不完整，切換下一個模型")
                continue
            return reply
        except urllib.request.HTTPError as e:
            if e.code in (429, 503):
                log(f"  {model} 失敗（{e.code}），切換下一個模型")
                continue
            raise
    raise Exception("所有 Gemini 模型均無法使用")


# ── 主流程 ────────────────────────────────────────────────────────


def main():
    state = load_state()
    since_ts = state["last_checked"]
    replied_ids = set(state["replied_ids"])
    notified_ids = set(state.get("notified_ids", []))
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
    new_replies = 0
    pending = []

    try:
        media_list = api_get(
            f"{IG_ID}/media", {"fields": "id,timestamp,permalink", "limit": "20"}
        ).get("data", [])
    except Exception as e:
        log(f"❌ 取得貼文列表失敗：{e}")
        sys.exit(1)

    log(f"查詢 {len(media_list)} 篇貼文（since {since_ts[:16]}）")

    for media in media_list:
        media_id = media["id"]
        try:
            comments = api_get(
                f"{media_id}/comments",
                {"fields": "id,text,from,timestamp", "limit": "50"},
            ).get("data", [])
        except Exception as e:
            log(f"  貼文 {media_id} 取留言失敗：{e}")
            continue

        new_comments = [
            c
            for c in comments
            if c.get("timestamp", "") > since_ts
            and c.get("from", {}).get("id") != IG_ID
            and c["id"] not in replied_ids
            and c["id"] not in notified_ids
            and c.get("text", "").strip()
        ]

        for c in new_comments:
            cid = c["id"]
            text = c["text"].strip()

            # 問價格／到貨／訂購的留給人工，並記進 notified_ids 避免每 5 分鐘重複寄信
            if needs_human(text):
                pending.append(
                    {
                        "cid": cid,
                        "user": c.get("from", {}).get("username", "（不明）"),
                        "text": text,
                        "time": c.get("timestamp", ""),
                        "permalink": media.get("permalink", ""),
                    }
                )
                notified_ids.add(cid)
                log(f"  🔔 留給人工：{text[:30]}")
                continue

            try:
                reply = gemini_reply(text)
            except Exception as e:
                log(f"  Gemini 失敗：{e}，使用備用回覆")
                reply = FALLBACK

            try:
                api_post(f"{cid}/replies", {"message": reply})
                replied_ids.add(cid)
                new_replies += 1
                log(f"  ✅ {text[:25]}… → {reply[:40]}…")
            except Exception as e:
                log(f"  ❌ 回覆失敗：{e}")

    if pending:
        try:
            send_pending_mail(pending)
        except Exception as e:
            # 寄信失敗就把它們退回未通知，下次再試，不要默默吞掉
            for p in pending:
                notified_ids.discard(p.get("cid", ""))
            log(f"  ❌ 寄信失敗：{e}")

    state["last_checked"] = now_ts
    state["replied_ids"] = list(replied_ids)
    state["notified_ids"] = list(notified_ids)
    save_state(state)
    log(f"完成，自動回覆 {new_replies} 則，留給人工 {len(pending)} 則")


if __name__ == "__main__":
    main()
