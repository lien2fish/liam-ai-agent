#!/usr/bin/env python3
"""YouTube 留言自動回覆——只回知識與閒聊，購買／價格／到貨類原樣留給人工。

護欄與 Gemini 呼叫直接沿用 IG 那套（instagram/auto_reply/ig_comment_reply.py），
不另外抄一份，免得兩邊的紅線分岔。人設 prompt 依頻道切換。

⚠️ 判斷「回過沒有」用的是「這串底下有沒有本頻道的回覆」，不是狀態檔。
狀態檔一旦沒存成功就會整批重回一次，而 YouTube 的回覆刪不掉。
直接問 API 現況才是唯一可靠的依據。

用法：
  python3 youtube/comment_reply.py --profile lien [--dry-run] [--max 5]
"""
import argparse, json, os, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "instagram", "auto_reply"))
sys.path.insert(0, os.path.join(ROOT, "youtube_auto"))
import ig_comment_reply as ig  # noqa: E402  護欄與 Gemini 降級邏輯的單一來源
import upload as yt  # noqa: E402  OAuth access token

API = "https://www.googleapis.com/youtube/v3"

PERSONA = {
    "lien": """你是連老闆，在新北市龜吼漁港做現流海鮮，跟 19 艘共捕漁船合作，
每天在碼頭看漁獲上岸。有人在你的 YouTube 影片下方留言。""",
    "dessert": """你是一位 2007 年入行的專業甜點師，在自己家的廚房做甜點給大家看，
會講業界不太願意講的實話。有人在你的 YouTube 影片下方留言。""",
}

RULES = """
用繁體中文回一句，**像在跟朋友分享，不是在做客服**：
- 字數 15～25 字之間
- 講人話。可以直接、可以有自己的看法，不用客套也不用敬語
- 加 1 個相關 emoji
- 只輸出回覆內容本身，不要加引號或任何前綴說明

**絕對不要**做這些事：
- 不要推銷、不要引導私訊或購買
- 不要用「歡迎來訊討論」「有需求歡迎詢問」這類收尾
- 不要說「感謝您的留言」這種客服開場
- 不要自稱「我們」或「本店」

**絕對不要編造事實**（這比語氣重要，寧可回得平淡也不能講錯）：
- **不講具體價格**、**不講具體日期或到貨時間**
- **不講留言裡沒提到的品項名稱**——你看不到照片
- 不確定的產季、規格、重量一律不提

留言內容：{text}"""


# ── 輸出護欄 ──────────────────────────────────────────────────────
# 2026-09-02 首次 dry-run，三則回覆全部踩線：「三點蟹正肥、花蟹也快跟上」
# （產季＋留言沒提到的魚種）、「今天大豐收」（編造當天漁獲）、「這個季節很多蟹」。
# prompt 裡已經明文禁止，Gemini 照樣講——光靠交代不夠，輸出端一定要擋。
BANNED_OUT = [
    # 產季與當下狀況：AI 最愛編，而且錯了會被同行與老饕抓到
    "正肥", "當季", "這個季節", "產季", "盛產", "大豐收", "快跟上",
    "剛上岸", "現在正是", "最近都", "這幾天", "正是時候", "剛好是",
    # 價格與到貨：這兩類本來就該留給人工
    "塊錢", "特價", "優惠", "到貨", "明天", "下週", "月底",
]

# 回覆若冒出留言裡沒有的品項名，就是憑空生出來的
ITEM_NAMES = [
    "三點蟹", "花蟹", "石蟳", "紅蟳", "沙公", "沙母", "白蝦", "草蝦", "虎蝦",
    "胭脂蝦", "龍蝦", "鮑魚", "干貝", "生蠔", "牡蠣", "石斑", "龍膽", "龍虎斑",
    "白帶魚", "土魠", "紅喉", "赤鯮", "黑鮪", "鮭魚", "鯖魚", "秋刀魚", "小卷",
    "透抽", "軟絲", "章魚", "海鱺", "真鯛", "吳郭魚", "台灣鯛", "虱目魚", "比目魚",
    "扁鱈", "圓鱈", "香螺", "螺肉", "九孔",
]


def output_violates(reply, comment):
    """回覆送出前的最後一道。擋下就寧可不回——回錯比不回傷得多。"""
    for w in BANNED_OUT:
        if w in reply:
            return f"提到「{w}」"
    for f in ITEM_NAMES:
        if f in reply and f not in comment:
            return f"冒出留言沒提到的「{f}」"
    if any(ch.isdigit() for ch in reply):
        return "出現數字（價格／規格／日期都不能給）"
    return None


SAFE_REPLIES = ["謝謝 🙏", "感謝支持 🙏", "謝謝你 🙏"]


def low_signal(text):
    """純 emoji 或極短留言沒有資訊量，硬要 AI 生成就會開始編產季。"""
    import re as _re
    return len(_re.findall(r"[\u4e00-\u9fffA-Za-z]", text)) < 4


def log(m):
    print(m, flush=True)


def api(tok, path, **params):
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def post_reply(tok, parent_id, text):
    body = json.dumps(
        {"snippet": {"parentId": parent_id, "textOriginal": text}}
    ).encode()
    req = urllib.request.Request(
        f"{API}/comments?part=snippet",
        data=body,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def already_replied(thread, my_id):
    """這串底下已經有本頻道的回覆就不再回——不依賴狀態檔，天然防重複。"""
    for c in thread.get("replies", {}).get("comments", []):
        if c["snippet"].get("authorChannelId", {}).get("value") == my_id:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, choices=sorted(PERSONA))
    ap.add_argument("--max", type=int, default=5, help="單次最多回幾則")
    ap.add_argument("--dry-run", action="store_true", help="只印出要回什麼，不送出")
    a = ap.parse_args()

    tok = yt.access_token(a.profile)
    me = api(tok, "channels", part="id", mine="true")["items"][0]["id"]
    log(f"頻道：{me}｜profile={a.profile}{'｜dry-run' if a.dry_run else ''}")

    threads = api(
        tok, "commentThreads", part="snippet,replies",
        allThreadsRelatedToChannelId=me, maxResults=100, textFormat="plainText",
    ).get("items", [])  # fmt: skip
    log(f"留言串 {len(threads)} 則")

    done = skipped = human = 0
    replied_authors = set()  # 同一個人連丟五則 emoji，全部回「謝謝」會很機械
    for t in threads:
        top = t["snippet"]["topLevelComment"]
        sn = top["snippet"]
        text = sn["textDisplay"].strip()

        if sn.get("authorChannelId", {}).get("value") == me:
            skipped += 1
            continue
        if already_replied(t, me):
            skipped += 1
            continue
        if ig.needs_human(text):
            human += 1
            log(f"  🙋 留給人工：{text[:34]}")
            continue
        author = sn.get("authorChannelId", {}).get("value", sn["authorDisplayName"])
        if author in replied_authors:
            skipped += 1
            continue
        if done >= a.max:
            continue

        if low_signal(text):
            import random

            reply = random.choice(SAFE_REPLIES)
        else:
            prompt = PERSONA[a.profile] + RULES.format(text=text)
            try:
                reply = ig.gemini_reply(text, prompt=prompt)
            except Exception as e:
                log(f"  ⚠️ 產不出回覆（{type(e).__name__}），跳過：{text[:24]}")
                continue
            bad = output_violates(reply, text)
            if bad:
                log(f"  🚫 擋下（{bad}）：{reply}")
                continue

        log(f"  💬 {sn['authorDisplayName']}：{text[:34]}")
        log(f"     → {reply}")
        if not a.dry_run:
            try:
                post_reply(tok, top["id"], reply)
            except urllib.error.HTTPError as e:
                log(f"     ❌ 送出失敗 {e.code}：{e.read()[:120]}")
                continue
            time.sleep(1)
        replied_authors.add(author)
        done += 1

    log(f"\n回覆 {done} 則｜留給人工 {human} 則｜已回過或自己的 {skipped} 則")


if __name__ == "__main__":
    main()
