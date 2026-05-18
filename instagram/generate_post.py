#!/usr/bin/env python3
"""每日 Instagram 海鮮小知識自動發文腳本"""

import json, os, requests, base64, io, time, platform
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 設定來源：GitHub Actions 用環境變數，本機用 config 檔
if os.environ.get('IG_TOKEN'):
    GEMINI_KEY    = os.environ['GEMINI_KEY']
    HF_TOKEN      = os.environ['HF_TOKEN']
    IG_TOKEN      = os.environ['IG_TOKEN']
    IG_ID         = os.environ['IG_ID']
    FB_PAGE_TOKEN = os.environ.get('FB_PAGE_TOKEN', '')
    FB_PAGE_ID    = os.environ.get('FB_PAGE_ID', '')
else:
    CONFIG        = json.load(open(os.path.join(BASE_DIR, '../config/instagram_config.json')))
    GEMINI_KEY    = CONFIG['gemini_api_key']
    HF_TOKEN      = CONFIG['hf_token']
    IG_TOKEN      = CONFIG['long_lived_user_token']
    IG_ID         = CONFIG['ig_account_id']
    FB_PAGE_TOKEN = CONFIG.get('fb_page_token', '')
    FB_PAGE_ID    = CONFIG.get('fb_page_id', '')

TEMPLATE  = os.path.join(BASE_DIR, 'template.png')
LOGO_PATH = os.path.join(BASE_DIR, 'logo.png')

# 字型：macOS 用 PingFang，Linux（GitHub Actions）用 Noto CJK
if platform.system() == 'Darwin':
    FONT     = '/System/Library/Fonts/PingFang.ttc'
    FONT_IDX = 3
else:
    # 用 fc-list 動態查找 Noto CJK 中文字型（相容各 Ubuntu 版本）
    import subprocess as _sp
    _fc = _sp.run(['fc-list', ':lang=zh', '--format=%{file}\n'],
                  capture_output=True, text=True)
    _noto = [l.strip() for l in _fc.stdout.splitlines()
             if 'Noto' in l and 'CJK' in l]
    print(f"[font] 找到 Noto CJK 字型：{_noto[:5]}", flush=True)
    if _noto:
        FONT = _noto[0]
        FONT_IDX = 3 if FONT.endswith('.ttc') else 0
    else:
        FONT     = '/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc'
        FONT_IDX = 3


def generate_knowledge():
    """Gemini 生成今日海鮮知識（2.5-flash → 1.5-flash fallback）"""
    prompt = """你是台灣海洋達人。生成一則台灣讀者有興趣的知識，JSON格式：
{
  "seafood_zh": "主題名稱（2-5字）",
  "seafood_en": "English name or term",
  "title_zh": "標題（格式：XX的祕密 或 你不知道的XX，10字內）",
  "title_en": "Title in English (under 35 chars)",
  "content": "5到6句有趣知識，繁體中文。每句獨立，加換行符\\n分隔。每句不超過28字。內容要有層次：第一句引起好奇，中間深入說明，最後一句給讀者帶走的亮點。",
  "illustration_prompt": "描述插圖主體的英文句子，用於 AI 繪圖。要能精準對應本則知識內容。格式：Watercolor illustration of [具體主體與場景]，例如：Watercolor illustration of a Taiwanese fisherman sitting on a small wooden boat doing pole-and-line fishing, calm sea, warm morning light"
}
從以下三大類隨機選一個角度，每次都要不同：

【海鮮知識】
- 外觀辨別：野生vs養殖外觀差異、新鮮度判斷、季節產期
- 食用知識：最佳料理方式、哪個部位最美味、營養成分
- 生態習性：棲息地、食性、繁殖、壽命等有趣行為
- 台灣特色：龜吼現流、各地名產、在地飲食文化
題材：鮭魚/鮪魚/石斑/午仔魚/白帶魚/鬼頭刀/烏魚/透抽/花枝/章魚/
      草蝦/白蝦/龍蝦/花蟹/三點蟹/牡蠣/文蛤/九孔/海膽/海參/烏魚子等

【捕魚知識】
- 漁法介紹：一支釣/延繩釣/定置網/拖網/圍網各自特色
- 捕魚時機：魚汛季節、哪個月份捕哪種魚最多
- 漁港文化：龜吼漁港/野柳/澳底等台灣漁港特色
- 漁民智慧：辨別天氣、選釣點、魚群判斷等經驗知識

【漁船知識】
- 船種介紹：膠筏/小漁船/延繩釣船/拖網船/圍網船功能差異
- 漁具設備：集魚燈/聲納/魚探機/漁網材質等
- 出海作業：一次出海多久、如何保鮮、船上生活

注意：不要選潮汐、海流、洋流等自然現象類內容。"""

    for model in ['gemini-2.5-flash', 'gemini-1.5-flash']:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        r = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }, timeout=30)
        data = r.json()
        if 'candidates' in data:
            text = data['candidates'][0]['content']['parts'][0]['text']
            return json.loads(text)
        print(f"[{model}] 失敗：{data}", flush=True)
    raise RuntimeError("所有 Gemini 模型均失敗")


def generate_illustration(illustration_prompt):
    """Hugging Face FLUX.1-schnell 生成水彩插圖"""
    url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    prompt = (
        f"{illustration_prompt}, pure white background, "
        "traditional natural history watercolor illustration style, "
        "soft warm color palette, highly detailed, beautiful, no text, no shadow, centered composition"
    )
    r = requests.post(url,
        headers={"Authorization": f"Bearer {HF_TOKEN}"},
        json={"inputs": prompt},
        timeout=120
    )
    if r.status_code != 200:
        raise RuntimeError(f"HF 插圖生成失敗：{r.status_code} {r.text[:200]}")
    return Image.open(io.BytesIO(r.content)).convert('RGBA')


def wrap_text(draw, text, font, max_width):
    """中文自動換行（依字元切割）"""
    lines = []
    for paragraph in text.split('\n'):
        line = ''
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
    base = Image.open(TEMPLATE).convert('RGBA')
    W, H = base.size  # 2700 x 3375

    draw = ImageDraw.Draw(base)
    DARK_BLUE = (45, 65, 105)
    GOLD      = (180, 160, 120)

    font_date = ImageFont.truetype(FONT, 100, index=FONT_IDX)
    font_en   = ImageFont.truetype(FONT, 72, index=FONT_IDX)
    font_body = ImageFont.truetype(FONT, 90, index=FONT_IDX)
    font_tag  = ImageFont.truetype(FONT, 62, index=FONT_IDX)

    # 卡面金框內側邊界
    CARD_L, CARD_R = 520, 2180
    MAX_W = CARD_R - CARD_L

    # 動態計算插圖大小：先估文字高度，剩餘空間給插圖
    import numpy as np
    ILLUS_Y = 880
    CARD_BOTTOM = 3100  # 文字必須在此 y 以上結束
    HEADER_H = 335      # LINE_Y 到文字起始的固定高度（分隔線+日期+英文+第二條線）
    GAP = 50            # 插圖底部到 LINE_Y 的間距

    font_est = ImageFont.truetype(FONT, 100, index=FONT_IDX)
    est_lines = wrap_text(draw, knowledge['content'], font_est, MAX_W)
    est_text_h = len(est_lines) * int(100 * 1.55)

    TOTAL_AVAIL = CARD_BOTTOM - ILLUS_Y - GAP - HEADER_H   # 插圖+文字總可用高度
    ILLUS_SIZE = min(1600, max(900, TOTAL_AVAIL - est_text_h))

    # 插圖：去白背景 → 自動裁切主體 → 填滿插圖區域
    arr = np.array(illustration.convert('RGBA'), dtype=np.float32)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    arr[:,:,3] = np.where((r > 228) & (g > 228) & (b > 228) & (np.abs(r-g) < 25), 0, arr[:,:,3])
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
    draw.text((CARD_L, LINE_Y + 60), f"{today}　|　{knowledge['title_zh']}", font=font_date, fill=DARK_BLUE)
    draw.text((CARD_L, LINE_Y + 178), f"（{knowledge['title_en']}）", font=font_en, fill=(130, 110, 80))
    draw.line([(CARD_L, LINE_Y + 268), (CARD_R, LINE_Y + 268)], fill=GOLD, width=3)

    # 內文：自動選最大可容納字型
    TEXT_START = LINE_Y + 335
    TEXT_AVAIL = 3100 - TEXT_START
    font_body, lines, line_h = fit_body_font(draw, knowledge['content'], MAX_W, TEXT_AVAIL, FONT)
    for i, line in enumerate(lines):
        draw.text((CARD_L, TEXT_START + i * line_h), line, font=font_body, fill=DARK_BLUE)

    # 標語：整張圖右下角木桌區域
    tagline = "每日一則，探索鮮味"
    bbox = draw.textbbox((0, 0), tagline, font=font_tag)
    tag_w = bbox[2] - bbox[0]
    draw.text((W - tag_w - 160, H - 160), tagline, font=font_tag, fill=(160, 140, 110))

    # Logo：整張圖左下角木桌區域
    logo = Image.open(LOGO_PATH).convert('RGBA')
    LOGO_H = 130
    LOGO_W = int(logo.width * LOGO_H / logo.height)
    logo_r = logo.resize((LOGO_W, LOGO_H), Image.LANCZOS)
    base.paste(logo_r, (130, H - 178), logo_r)

    # 合成卡片（1080×1350）
    card = Image.new('RGB', (W, H), (255, 255, 255))
    card.paste(base, mask=base.split()[3])
    card = card.resize((1080, 1350), Image.LANCZOS)

    # 套入 9:16 Story 畫布（1080×1920），上下填木桌背景色
    story = Image.new('RGB', (1080, 1920), (88, 65, 38))
    pad_y = (1920 - 1350) // 2  # = 285
    story.paste(card, (0, pad_y))
    return story


def upload_image(image):
    """上傳圖片到 GitHub repo，回傳 raw.githubusercontent.com 公開 URL"""
    github_token = os.environ.get('GITHUB_TOKEN', '')
    repo = os.environ.get('GITHUB_REPO', 'lien2fish/liam-ai-agent')
    today = datetime.now().strftime('%Y-%m-%d')
    filepath = f'instagram/posts/{today}.jpg'

    buf = io.BytesIO()
    image.save(buf, 'JPEG', quality=95)
    content_b64 = base64.b64encode(buf.getvalue()).decode()

    api_url = f'https://api.github.com/repos/{repo}/contents/{filepath}'
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # 若同名檔已存在，需帶 sha 才能更新
    existing = requests.get(api_url, headers=headers)
    body = {'message': f'Add IG post {today}', 'content': content_b64}
    if existing.status_code == 200:
        body['sha'] = existing.json()['sha']

    r = requests.put(api_url, headers=headers, json=body)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"GitHub 上傳失敗：{r.status_code} {r.text[:300]}")

    return f'https://raw.githubusercontent.com/{repo}/main/{filepath}'


def post_to_instagram(image_url, knowledge):
    """發限時動態到 Instagram"""
    r1 = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_ID}/media",
        data={'image_url': image_url, 'media_type': 'STORIES', 'access_token': IG_TOKEN}
    )
    data1 = r1.json()
    if 'id' not in data1:
        raise RuntimeError(f"建立 container 失敗：{data1}")

    container_id = data1['id']

    # 等待 Meta 處理圖片（最多 60 秒）
    for _ in range(12):
        time.sleep(5)
        st = requests.get(
            f"https://graph.facebook.com/v19.0/{container_id}",
            params={'fields': 'status_code', 'access_token': IG_TOKEN}
        ).json()
        if st.get('status_code') == 'FINISHED':
            break
        if st.get('status_code') == 'ERROR':
            raise RuntimeError(f"Container 處理失敗：{st}")

    r2 = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_ID}/media_publish",
        data={'creation_id': container_id, 'access_token': IG_TOKEN}
    )
    return r2.json()


def post_to_facebook(image_url, knowledge):
    """發限時動態到 Facebook 粉絲專頁"""
    if not FB_PAGE_TOKEN or not FB_PAGE_ID:
        print("[FB] 未設定 FB_PAGE_TOKEN / FB_PAGE_ID，跳過", flush=True)
        return None

    r = requests.post(
        f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photo_stories",
        data={'url': image_url, 'access_token': FB_PAGE_TOKEN}
    )
    return r.json()


if __name__ == '__main__':
    log = lambda msg: print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)

    log("生成今日海鮮知識...")
    knowledge = generate_knowledge()
    log(f"主題：{knowledge['seafood_zh']} ─ {knowledge['title_zh']}")

    log("生成水彩插圖...")
    illustration = generate_illustration(knowledge['illustration_prompt'])
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
