import os
import hmac
import hashlib
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
APP_SECRET   = os.environ["APP_SECRET"]
IG_TOKEN     = os.environ["IG_TOKEN"]
GEMINI_KEY   = os.environ["GEMINI_KEY"]

FALLBACK_REPLY = "謝謝你的回應！有任何問題歡迎私訊我們 🙏"

BRAND_PROMPT = """你是「鉅鑫管理顧問」旗下品牌的 Instagram 客服助理，品牌包含：
- 鑫酒坊（精品葡萄酒）
- 鑫茶坊（高端茶葉）
- 匠鑫私廚（VIP 私廚接待）
- 龜吼現流活海產（新鮮漁獲）

品牌核心價值：「鉅鑫只提供最高品質」

收到以下 IG 限時動態回覆訊息，請用繁體中文、友善且符合高端品牌調性回覆，控制在 30 字內。
對方訊息：{message}

只輸出回覆內容，不要加任何說明。"""


def verify_signature(payload: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(
        APP_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def gemini_reply(user_message: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    body = {"contents": [{"parts": [{"text": BRAND_PROMPT.format(message=user_message)}]}]}
    try:
        resp = requests.post(url, json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return FALLBACK_REPLY


def send_ig_reply(recipient_id: str, text: str):
    url = f"https://graph.facebook.com/v19.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "access_token": IG_TOKEN,
    }
    requests.post(url, json=payload, timeout=10)


@app.route("/webhook", methods=["GET"])
def webhook_verify():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook_receive():
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(request.data, signature):
        return "Unauthorized", 401

    data = request.json
    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id")
            message   = event.get("message", {})
            text      = message.get("text", "")

            # 只處理純文字 story reply（帶 reply_to 且有 story 欄位）
            reply_to = message.get("reply_to", {})
            is_story_reply = "story" in reply_to

            if sender_id and text and is_story_reply:
                reply_text = gemini_reply(text)
                send_ig_reply(sender_id, reply_text)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
