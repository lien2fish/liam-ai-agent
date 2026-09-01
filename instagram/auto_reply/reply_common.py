#!/usr/bin/env python3
"""IG 與 YouTube 留言回覆共用的護欄與 Gemini 呼叫。

抽出來的原因：原本放在 ig_comment_reply.py，但那支頂層有
`IG_TOKEN, IG_ID, GEMINI_KEY = load_config()`，一 import 就去讀本機 config，
在 GitHub Actions 上直接 FileNotFoundError（2026-09-02 實際炸過一次）。
這支只有純函式，import 不產生任何副作用。

GEMINI_KEY 由呼叫端用環境變數提供。
"""
import json, os, urllib.request

GEMINI_KEY = os.environ.get("GEMINI_KEY", "")
GEMINI_MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-flash-lite-latest"]


def log(m):
    print(m, flush=True)


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


def gemini_reply(text, prompt=None):
    """prompt 不給就用下面這套連老闆人設。YouTube 留言回覆共用這支的模型降級與
    thinkingBudget 處理，只換人設（甜點頻道的主講不是連老闆），避免兩邊分岔。"""
    prompt = prompt or f"""你是連老闆，在新北市龜吼漁港做現流海鮮，跟 19 艘共捕漁船合作，
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
