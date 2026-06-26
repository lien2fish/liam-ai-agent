#!/usr/bin/env python3
"""每日 Instagram 海鮮小知識自動發文腳本"""

import json, os, requests, base64, io, time, platform
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "recent_seafood.json"
)
HISTORY_KEEP = 365  # 保留最近 365 天紀錄（一年不重複）

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 文案＋畫圖提示詞由 Claude 生成（Gemini 保留為 fallback）
CLAUDE_MODEL = "claude-sonnet-4-6"  # 省錢可改 "claude-haiku-4-5-20251001"

# 設定來源：GitHub Actions 用環境變數，本機用 config 檔
if os.environ.get("IG_TOKEN"):
    ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    GEMINI_KEY = os.environ.get("GEMINI_KEY", "")
    HF_TOKEN = os.environ["HF_TOKEN"]
    IG_TOKEN = os.environ["IG_TOKEN"]
    IG_ID = os.environ["IG_ID"]
    FB_PAGE_TOKEN = os.environ.get("FB_PAGE_TOKEN", "")
    FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "")
else:
    CONFIG = json.load(open(os.path.join(BASE_DIR, "../config/instagram_config.json")))
    ANTHROPIC_KEY = CONFIG.get("anthropic_api_key", "")
    GEMINI_KEY = CONFIG.get("gemini_api_key", "")
    HF_TOKEN = CONFIG["hf_token"]
    IG_TOKEN = CONFIG["long_lived_user_token"]
    IG_ID = CONFIG["ig_account_id"]
    FB_PAGE_TOKEN = CONFIG.get("fb_page_token", "")
    FB_PAGE_ID = CONFIG.get("fb_page_id", "")

TEMPLATE = os.path.join(BASE_DIR, "template.png")
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

# 字型：macOS 用 PingFang，Linux（GitHub Actions）用 Noto CJK
if platform.system() == "Darwin":
    FONT = "/System/Library/Fonts/PingFang.ttc"
    FONT_IDX = 3
else:
    # 用 fc-list 動態查找 Noto CJK 中文字型（相容各 Ubuntu 版本）
    import subprocess as _sp

    _fc = _sp.run(
        ["fc-list", ":lang=zh", "--format=%{file}\n"], capture_output=True, text=True
    )
    _noto = [l.strip() for l in _fc.stdout.splitlines() if "Noto" in l and "CJK" in l]
    print(f"[font] 找到 Noto CJK 字型：{_noto[:5]}", flush=True)
    if _noto:
        FONT = _noto[0]
        FONT_IDX = 3 if FONT.endswith(".ttc") else 0
    else:
        FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"
        FONT_IDX = 3


def load_recent_seafood():
    """讀取最近發過的主題/角度組合清單，自動遷移舊格式（無/的純主題名）"""
    if os.path.exists(HISTORY_FILE):
        try:
            items = json.load(open(HISTORY_FILE)).get("recent", [])
            return ["/" in item and item or f"{item}/未分類" for item in items]
        except Exception:
            return []
    return []


def save_recent_seafood(recent_list, new_seafood):
    """將新魚種加入歷史並存回 repo（GitHub Actions 用 API，本機直接寫檔）"""
    updated = ([new_seafood] + recent_list)[:HISTORY_KEEP]
    content_str = json.dumps({"recent": updated}, ensure_ascii=False, indent=2)

    if not os.environ.get("GITHUB_TOKEN"):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write(content_str)
        return

    github_token = os.environ["GITHUB_TOKEN"]
    repo = os.environ.get("GITHUB_REPO", "lien2fish/liam-ai-agent")
    filepath = "instagram/recent_seafood.json"
    api_url = f"https://api.github.com/repos/{repo}/contents/{filepath}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    body = {
        "message": f"Update seafood history: {new_seafood}",
        "content": base64.b64encode(content_str.encode()).decode(),
    }
    existing = requests.get(api_url, headers=headers)
    if existing.status_code == 200:
        body["sha"] = existing.json()["sha"]
    requests.put(api_url, headers=headers, json=body)


SEASONAL_FISH = {
    1: ["鱈魚", "花蟹", "三點蟹", "牡蠣", "蛤蜊", "九孔", "螳螂蝦"],
    2: ["烏魚", "烏魚子", "花枝", "小卷", "旭蟹", "蚵仔"],
    3: ["鯖魚", "鱸魚", "白帶魚", "透抽", "竹筴魚", "赤鯮"],
    4: ["白帶魚", "午仔魚", "透抽", "小卷", "虱目魚", "海膽"],
    5: ["黑鮪魚", "飛魚", "鬼頭刀", "煙仔魚", "旗魚", "龍蝦"],
    6: ["飛魚", "鬼頭刀", "煙仔魚", "正鰹", "鮪魚", "海鱺"],
    7: ["旗魚", "鮪魚", "鬼頭刀", "劍旗魚", "草蝦", "白蝦"],
    8: ["旗魚", "劍旗魚", "土魠魚", "馬鮫魚", "九節蝦", "花枝"],
    9: ["秋刀魚", "正鰹", "煙仔魚", "白帶魚", "透抽", "花蟹"],
    10: ["土魠魚", "白帶魚", "旗魚", "午仔魚", "三點蟹", "牡蠣"],
    11: ["烏魚", "白帶魚", "赤鯮", "石斑魚", "花蟹", "蛤蜊"],
    12: ["烏魚", "烏魚子", "花蟹", "龍蝦", "蝦類", "鱈魚"],
}


def build_knowledge_prompt(exclude_seafood=None):
    """組合今日知識生成的 prompt（Claude / Gemini 共用）"""
    month = datetime.now().month
    in_season = SEASONAL_FISH.get(month, [])
    season_note = f"\n\n🗓️ 本月（{month}月）當季台灣魚種：{'、'.join(in_season)}。若選擇【海鮮知識】類別，請優先從當季魚種中選題；若近期當季魚種都已發過，才考慮非當季題材。"

    exclude_note = ""
    if exclude_seafood:
        exclude_note = f'\n\n⚠️ 以下「主題/角度」組合近期已發過，本次嚴禁使用（主題相同但角度不同則可以）：{", ".join(exclude_seafood)}'

    return f"""你是台灣海洋達人。生成一則台灣讀者有興趣的知識，JSON格式：
{{
  "seafood_zh": "主題名稱（2-5字）",
  "seafood_en": "English name or term",
  "category": "本則知識的角度分類（從以下選一）：外觀辨別｜食用知識｜生態習性｜台灣特色｜漁法介紹｜捕魚時機｜漁港文化｜漁民智慧｜船種介紹｜漁具設備｜出海作業｜飲食文化",
  "title_zh": "標題（格式：XX的祕密 或 你不知道的XX，10字內）",
  "title_en": "Title in English (under 35 chars)",
  "content": "5到6句有趣知識，繁體中文。每句獨立，加換行符\\n分隔。每句不超過28字。內容要有層次：第一句引起好奇，中間深入說明，最後一句給讀者帶走的亮點。",
  "illustration_prompt": "描述插圖主體的英文句子，用於 AI 繪圖。要能精準對應本則知識內容。格式：Watercolor illustration of [具體主體與場景]，例如：Watercolor illustration of a Taiwanese fisherman sitting on a small wooden boat doing pole-and-line fishing, calm sea, warm morning light"
}}

從以下三大類中選一個主題，再從該類的角度中選一個角度，組合出今日內容。
目標是在365天內不重複相同的「主題+角度」組合。

【海鮮知識】角度：外觀辨別｜食用知識｜生態習性｜台灣特色
魚類（40+）：鮪魚、黑鮪魚、正鰹、煙仔魚、鯖魚、午仔魚、石斑魚、白帶魚、鬼頭刀、烏魚、虱目魚、赤鯮、秋刀魚、沙丁魚、海鱺、旗魚、劍旗魚、土魠魚、馬鮫魚、黃雞魚、肉魚、三牙仔、比目魚、吻仔魚、飛魚、曼波魚、鯊魚、鰻魚、錢鰻、鱸魚、鱈魚、珍珠鱸、油魚、鸚鵡魚、紅甘、鰺魚、竹筴魚、柴魚
頭足類：透抽、小卷、花枝、章魚、鎖管
甲殼類：草蝦、白蝦、九節蝦、螳螂蝦、花蟹、三點蟹、旭蟹、龍蝦、蟹膏蟹
貝類：牡蠣、文蛤、蛤蜊、九孔、海膽、海參、鮑魚、蚵仔
加工品：烏魚子、魚鬆、魚翅、飛魚卵、魚乾、鹽漬魚

【捕魚知識】角度：漁法介紹｜捕魚時機｜漁港文化｜漁民智慧
漁法（10+）：一支釣、延繩釣、定置網、拖網、圍網、流刺網、手釣、魚叉、籠具、夜間集魚燈釣法、曳繩釣
月份魚汛：1月鱈魚蟹、2月烏魚子、3月春鯖、4月白帶魚、5月鮪魚季、6月飛魚季、7月正鰹、8月旗魚、9月秋刀魚、10月土魠魚、11月烏魚、12月冬蝦
漁港（8+）：龜吼漁港、野柳漁港、澳底漁港、基隆正濱漁港、南方澳漁港、新港漁港、成功漁港、東港漁港、興達漁港

【漁船知識】角度：船種介紹｜漁具設備｜出海作業｜飲食文化
船種：膠筏、小漁船、延繩釣船、拖網船、圍網船、遠洋漁船、娛樂漁船
設備：集魚燈、聲納魚探機、GPS定位、冰艙保鮮技術、漁網材質與選擇、無線電通訊
生活：出海時間週期、船上生活分工、惡劣天氣應對、討海人的飲食習慣、漁村文化與信仰

注意：若涉及潮汐、海流、洋流等自然現象，必須結合漁民作業或捕魚技術來說明，不可單純介紹自然現象本身。{season_note}{exclude_note}

只輸出 JSON 物件本身，不要加任何說明文字、註解或 markdown 程式碼框。"""


def knowledge_via_claude(prompt):
    """Claude 生成今日知識＋畫圖提示詞（用 assistant prefill 強制 JSON 輸出）"""
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 1024,
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "{"},
            ],
        },
        timeout=60,
    )
    data = r.json()
    if "content" not in data:
        raise RuntimeError(f"Claude 回傳異常：{data}")
    return json.loads("{" + data["content"][0]["text"])


def knowledge_via_gemini(prompt):
    """Gemini fallback（2.5-flash → 2.0-flash → 2.0-flash-lite）"""
    for model in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        r = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"},
            },
            timeout=30,
        )
        data = r.json()
        if "candidates" in data:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        print(f"[{model}] 失敗：{data}", flush=True)
    raise RuntimeError("所有 Gemini 模型均失敗")


def generate_knowledge(exclude_seafood=None):
    """今日知識生成：Claude 為主，Gemini 為 fallback"""
    prompt = build_knowledge_prompt(exclude_seafood)
    if ANTHROPIC_KEY:
        try:
            return knowledge_via_claude(prompt)
        except Exception as e:
            print(f"[Claude] 失敗，改用 Gemini fallback：{e}", flush=True)
    return knowledge_via_gemini(prompt)


def generate_illustration(illustration_prompt):
    """Hugging Face FLUX.1-schnell 生成水彩插圖"""
    url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    prompt = (
        f"{illustration_prompt}, pure white background, "
        "traditional natural history watercolor illustration style, "
        "soft warm color palette, highly detailed, beautiful, no text, no shadow, centered composition"
    )
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {HF_TOKEN}"},
        json={"inputs": prompt},
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"HF 插圖生成失敗：{r.status_code} {r.text[:200]}")
    return Image.open(io.BytesIO(r.content)).convert("RGBA")


def wrap_text(draw, text, font, max_width):
    """中文自動換行（依字元切割）"""
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for ch in paragraph:
            test = line + ch
            w = draw.textbbox((0, 0), test, font=font)[2]
            if w > max_width and line:
                lines.append(line)
                line = ch
            else:
                line = test
        if line:
            lines.append(line)
    return lines


def fit_body_font(draw, content, max_w, avail_h, font_path):
    """依內文多寡自動選最大能塞進去的字型大小"""
    for size in range(100, 58, -4):
        font = ImageFont.truetype(font_path, size, index=FONT_IDX)
        lines = wrap_text(draw, content, font, max_w)
        line_h = int(size * 1.55)
        if len(lines) * line_h <= avail_h:
            return font, lines, line_h
    font = ImageFont.truetype(font_path, 60, index=FONT_IDX)
    return font, wrap_text(draw, content, font, max_w), 93


def compose_image(knowledge, illustration):
    """PIL 合成最終貼文圖片"""
    base = Image.open(TEMPLATE).convert("RGBA")
    W, H = base.size  # 2700 x 3375

    draw = ImageDraw.Draw(base)
    DARK_BLUE = (45, 65, 105)
    GOLD = (180, 160, 120)

    font_date = ImageFont.truetype(FONT, 100, index=FONT_IDX)
    font_en = ImageFont.truetype(FONT, 72, index=FONT_IDX)
    font_body = ImageFont.truetype(FONT, 90, index=FONT_IDX)
    font_tag = ImageFont.truetype(FONT, 62, index=FONT_IDX)

    # 卡面金框內側邊界
    CARD_L, CARD_R = 520, 2180
    MAX_W = CARD_R - CARD_L

    # 動態計算插圖大小：先估文字高度，剩餘空間給插圖
    import numpy as np

    ILLUS_Y = 880
    CARD_BOTTOM = 3100  # 文字必須在此 y 以上結束
    HEADER_H = 335  # LINE_Y 到文字起始的固定高度（分隔線+日期+英文+第二條線）
    GAP = 50  # 插圖底部到 LINE_Y 的間距

    font_est = ImageFont.truetype(FONT, 100, index=FONT_IDX)
    est_lines = wrap_text(draw, knowledge["content"], font_est, MAX_W)
    est_text_h = len(est_lines) * int(100 * 1.55)

    TOTAL_AVAIL = CARD_BOTTOM - ILLUS_Y - GAP - HEADER_H  # 插圖+文字總可用高度
    ILLUS_SIZE = min(1600, max(900, TOTAL_AVAIL - est_text_h))

    # 插圖：去白背景 → 自動裁切主體 → 填滿插圖區域
    arr = np.array(illustration.convert("RGBA"), dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    arr[:, :, 3] = np.where(
        (r > 228) & (g > 228) & (b > 228) & (np.abs(r - g) < 25), 0, arr[:, :, 3]
    )
    illus = Image.fromarray(arr.astype(np.uint8))
    bbox = illus.getbbox()
    if bbox:
        illus = illus.crop(bbox)
    ratio = min(ILLUS_SIZE / illus.width, ILLUS_SIZE / illus.height)
    new_w, new_h = int(illus.width * ratio), int(illus.height * ratio)
    illus = illus.resize((new_w, new_h), Image.LANCZOS)
    base.paste(illus, ((W - new_w) // 2, ILLUS_Y + (ILLUS_SIZE - new_h) // 2), illus)

    # 分隔線 + 日期標題
    today = datetime.now().strftime("%Y.%m.%d")
    LINE_Y = ILLUS_Y + ILLUS_SIZE + GAP
    draw.line([(CARD_L, LINE_Y), (CARD_R, LINE_Y)], fill=GOLD, width=4)
    draw.text(
        (CARD_L, LINE_Y + 60),
        f"{today}　|　{knowledge['title_zh']}",
        font=font_date,
        fill=DARK_BLUE,
    )
    draw.text(
        (CARD_L, LINE_Y + 178),
        f"（{knowledge['title_en']}）",
        font=font_en,
        fill=(130, 110, 80),
    )
    draw.line([(CARD_L, LINE_Y + 268), (CARD_R, LINE_Y + 268)], fill=GOLD, width=3)

    # 內文：自動選最大可容納字型
    TEXT_START = LINE_Y + 335
    TEXT_AVAIL = 3100 - TEXT_START
    font_body, lines, line_h = fit_body_font(
        draw, knowledge["content"], MAX_W, TEXT_AVAIL, FONT
    )
    for i, line in enumerate(lines):
        draw.text(
            (CARD_L, TEXT_START + i * line_h), line, font=font_body, fill=DARK_BLUE
        )

    # 標語：整張圖右下角木桌區域
    tagline = "每日一則，探索鮮味"
    bbox = draw.textbbox((0, 0), tagline, font=font_tag)
    tag_w = bbox[2] - bbox[0]
    draw.text((W - tag_w - 160, H - 160), tagline, font=font_tag, fill=(160, 140, 110))

    # Logo：整張圖左下角木桌區域
    logo = Image.open(LOGO_PATH).convert("RGBA")
    LOGO_H = 130
    LOGO_W = int(logo.width * LOGO_H / logo.height)
    logo_r = logo.resize((LOGO_W, LOGO_H), Image.LANCZOS)
    base.paste(logo_r, (130, H - 178), logo_r)

    # 合成卡片（1080×1350）
    card = Image.new("RGB", (W, H), (255, 255, 255))
    card.paste(base, mask=base.split()[3])
    card = card.resize((1080, 1350), Image.LANCZOS)

    # 套入 9:16 Story 畫布（1080×1920），上下填木桌背景色
    story = Image.new("RGB", (1080, 1920), (88, 65, 38))
    pad_y = (1920 - 1350) // 2  # = 285
    story.paste(card, (0, pad_y))
    return story


def upload_image(image):
    """上傳圖片到 GitHub repo，回傳 raw.githubusercontent.com 公開 URL"""
    github_token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPO", "lien2fish/liam-ai-agent")
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = f"instagram/posts/{today}.jpg"

    buf = io.BytesIO()
    image.save(buf, "JPEG", quality=95)
    content_b64 = base64.b64encode(buf.getvalue()).decode()

    api_url = f"https://api.github.com/repos/{repo}/contents/{filepath}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # 若同名檔已存在，需帶 sha 才能更新
    existing = requests.get(api_url, headers=headers)
    body = {"message": f"Add IG post {today}", "content": content_b64}
    if existing.status_code == 200:
        body["sha"] = existing.json()["sha"]

    r = requests.put(api_url, headers=headers, json=body)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"GitHub 上傳失敗：{r.status_code} {r.text[:300]}")

    return f"https://raw.githubusercontent.com/{repo}/main/{filepath}"


def post_to_instagram(image_url, knowledge):
    """發限時動態到 Instagram，同時 cross_post 到已連結的 FB 粉絲專頁"""
    post_data = {
        "image_url": image_url,
        "media_type": "STORIES",
        "access_token": IG_TOKEN,
    }
    if FB_PAGE_ID:
        post_data["cross_post_ids"] = FB_PAGE_ID

    r1 = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_ID}/media", data=post_data
    )
    data1 = r1.json()
    if "id" not in data1:
        raise RuntimeError(f"建立 container 失敗：{data1}")

    container_id = data1["id"]

    # 等待 Meta 處理圖片（最多 60 秒）
    for _ in range(12):
        time.sleep(5)
        st = requests.get(
            f"https://graph.facebook.com/v19.0/{container_id}",
            params={"fields": "status_code", "access_token": IG_TOKEN},
        ).json()
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"Container 處理失敗：{st}")

    r2 = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_ID}/media_publish",
        data={"creation_id": container_id, "access_token": IG_TOKEN},
    )
    return r2.json()


def post_to_facebook(image_url, knowledge):
    """FB 限時動態已透過 post_to_instagram 的 cross_post_ids 跨發，此函式保留備用"""
    if not FB_PAGE_ID:
        print("[FB] 未設定 FB_PAGE_ID，跳過", flush=True)
        return None
    print(f"[FB] 限時動態已透過 IG cross_post_ids 跨發到 Page {FB_PAGE_ID}", flush=True)
    return {"cross_posted": True, "page_id": FB_PAGE_ID}


if __name__ == "__main__":
    log = lambda msg: print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)

    recent_seafood = load_recent_seafood()
    if recent_seafood:
        log(f"近期已發（最新10筆）：{', '.join(recent_seafood[:10])}")

    log("生成今日海鮮知識...")
    knowledge = generate_knowledge(exclude_seafood=recent_seafood)
    topic_angle = f"{knowledge['seafood_zh']}/{knowledge.get('category', '未分類')}"
    log(f"主題：{topic_angle} ─ {knowledge['title_zh']}")

    log("生成水彩插圖...")
    illustration = generate_illustration(knowledge["illustration_prompt"])
    log("插圖完成")

    log("合成圖片...")
    image = compose_image(knowledge, illustration)
    log("合成完成")

    log("上傳圖片...")
    url = upload_image(image)
    log(f"圖片 URL：{url}")

    log("發文到 Instagram...")
    result = post_to_instagram(url, knowledge)
    log(f"IG 完成：{result}")

    log("發文到 Facebook...")
    fb_result = post_to_facebook(url, knowledge)
    log(f"FB 完成：{fb_result}")

    log("更新歷史紀錄...")
    save_recent_seafood(recent_seafood, topic_angle)
    log(f"已記錄：{topic_angle}")
