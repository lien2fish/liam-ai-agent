#!/usr/bin/env python3
"""每日 Instagram 海鮮小知識自動發文腳本"""

import json, os, requests, base64, io, time, platform
import sys
from collections import OrderedDict
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "recent_seafood.json"
)
HISTORY_KEEP = 365  # 保留最近 365 天紀錄（一年不重複）

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 文案＋畫圖提示詞由 Claude 生成（Gemini 保留為 fallback）
CLAUDE_MODEL = "claude-sonnet-5"  # 省錢可改 "claude-haiku-4-5"

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


# 龜吼在地漁獲月曆（2026-08-26 依公開資料查證重建，取代先前未經驗證的版本）
# 依據：龜吼漁夫市集官方分季（9-3月萬里蟹／4-8月自家捕撈小卷透抽）、
#       新北市漁業處、農業部食農教育平台、農業知識入口網。
# 「主力」＝自家船與 19 艘共捕船撈得到的；「次要」＝市集常見、可能調貨。
# ⚠️ 文案講「主力」可以說「我們的」；講「次要」只能當知識，不可暗示有貨。
SEASONAL_LOCAL = {
    1: {"主力": ["花蟹", "石蟳", "三點蟹"], "次要": ["白帶魚", "赤鯮", "午仔魚"]},
    2: {"主力": ["花蟹", "石蟳", "三點蟹"], "次要": ["白帶魚", "赤鯮"]},
    3: {"主力": ["花蟹", "三點蟹"], "次要": ["鯖魚", "白帶魚"]},
    4: {"主力": ["小卷", "透抽"], "次要": ["鯖魚", "海膽"]},
    5: {"主力": ["小卷", "透抽"], "次要": ["白帶魚", "海膽"]},
    6: {"主力": ["透抽", "小卷"], "次要": ["白帶魚"]},
    7: {"主力": ["透抽", "小卷"], "次要": ["黃雞魚"]},
    8: {"主力": ["透抽", "小卷", "花枝"], "次要": ["白帶魚", "鯖魚", "黃雞魚"]},
    9: {"主力": ["三點蟹", "花蟹", "透抽"], "次要": ["白帶魚", "鯖魚"]},
    10: {"主力": ["三點蟹", "花蟹", "石蟳"], "次要": ["白帶魚", "黃雞魚", "紅甘"]},
    11: {"主力": ["三點蟹", "花蟹", "石蟳"], "次要": ["午仔魚", "紅甘", "赤鯮"]},
    12: {"主力": ["花蟹", "石蟳", "三點蟹"], "次要": ["午仔魚", "白帶魚"]},
}

# ⚠️ 待 Lien 確認才可放回月曆——先前版本有，但查不到北海岸依據：
#    烏魚（汛期主要在西部南下洄游）、土魠魚（冬季魚且多在澎湖南部，原本卻放 8 月）、
#    牡蠣／蛤蜊／九孔（皆養殖，九孔在貢寮）。
PENDING_CONFIRM = ["烏魚", "土魠魚", "牡蠣", "蛤蜊", "九孔"]

# 四大類各自的角度，用來從歷史紀錄反推某則屬於哪一類
CATEGORY_ANGLES = {
    "海鮮知識": [
        "外觀辨別",
        "食用知識",
        "生態習性",
        "台灣特色",
        "處理與保存",
        "料理法",
        "選購技巧",
        "常見誤解",
        "名稱由來",
        "相似魚種比較",
        "產季與時機",
        "冷知識趣聞",
    ],
    "捕魚知識": ["漁法介紹", "捕魚時機", "漁港文化", "漁民智慧"],
    "漁船知識": ["船種介紹", "漁具設備", "出海作業", "飲食文化"],
    "冷鏈知識": ["冷凍原理", "破除迷思", "冷知識"],
}

# 大類輪替表：模型自己不會平衡（舊版 89% 都落在海鮮知識），所以由程式指定。
# 17 天一循環，比例貼近各類題材池大小（海鮮 8／捕魚 4／漁船 4／冷鏈 1），
# 且海鮮知識不會連續兩天出現。
CATEGORY_ROTATION = [
    # 2026-08-26 Lien 要求提高冷鏈比例。20 天一循環：
    # 海鮮 7（35%）／捕魚 4（20%）／漁船 5（25%）／冷鏈 4（20%）——冷鏈從 6% 提到 20%。
    # 排列讓「同一類別不會連續兩天」，含頭尾相接也不會。
    # 產能檢核（× 365 天 vs 題材池）：
    #   海鮮 128 vs 408 ✅／捕魚 73 vs ~80 ⚠️偏緊／漁船 91 vs ~112 ✅／冷鏈 73 vs ~75 ⚠️偏緊
    # 偏緊的兩類若用完，prompt 已允許改選其他類別。
    "海鮮知識",
    "捕魚知識",
    "漁船知識",
    "海鮮知識",
    "冷鏈知識",
    "捕魚知識",
    "海鮮知識",
    "漁船知識",
    "冷鏈知識",
    "海鮮知識",
    "捕魚知識",
    "漁船知識",
    "海鮮知識",
    "冷鏈知識",
    "捕魚知識",
    "海鮮知識",
    "漁船知識",
    "冷鏈知識",
    "海鮮知識",
    "漁船知識",
]

# 物種群組：主題名不同但觀眾看起來是同一種東西。
# 花蟹/三點蟹/石蟳 連三天就是連三天螃蟹，所以以「群組」而非「主題」做連續管制。
SPECIES_GROUPS = {
    "蟹類": ["花蟹", "三點蟹", "石蟳", "旭蟹", "萬里蟹", "螃蟹", "蟹膏蟹", "帝王蟹"],
    "頭足類": ["小卷", "透抽", "花枝", "軟絲", "章魚", "鎖管", "魷魚"],
    "蝦類": ["草蝦", "白蝦", "九節蝦", "螳螂蝦", "龍蝦", "蝦子"],
    "貝類": ["牡蠣", "文蛤", "蛤蜊", "九孔", "鮑魚", "蚵仔", "海膽", "海參"],
    "白身魚": [
        "白帶魚",
        "黃雞魚",
        "赤鯮",
        "石斑魚",
        "鱸魚",
        "比目魚",
        "鱈魚",
        "午仔魚",
    ],
    "洄游大型魚": ["鮪魚", "黑鮪魚", "旗魚", "劍旗魚", "鬼頭刀", "紅甘", "海鱺"],
    "青背魚": [
        "鯖魚",
        "竹筴魚",
        "正鰹",
        "煙仔魚",
        "秋刀魚",
        "沙丁魚",
        "飛魚",
        "土魠魚",
        "馬鮫魚",
        "烏魚",
    ],
}
SPECIES_GROUP_OF = {n: g for g, names in SPECIES_GROUPS.items() for n in names}

# 連續幾則之內不得出現同一個物種群組
GROUP_COOLDOWN = 3

# 同一主題幾天內不重複。舊版只擋「主題+角度」組合，
# 導致花枝、飛魚相隔 1 天就再次出現。
TOPIC_COOLDOWN_DAYS = 14


def build_knowledge_prompt(exclude_seafood=None):
    """組合今日知識生成的 prompt（Claude / Gemini 共用）"""
    month = datetime.now().month
    season = SEASONAL_LOCAL.get(month, {})
    season_note = (
        f"\n\n🗓️ 本月（{month}月）龜吼在地漁獲——"
        f"**主力（自家船與 19 艘共捕船撈得到，可以講「我們的」）**：{'、'.join(season.get('主力', []))}；"
        f"**次要（市集常見、可能調貨，只能當知識講，不可暗示有貨）**：{'、'.join(season.get('次要', []))}。"
        "選【海鮮知識】類別時優先從主力選題。"
    )

    # 冷卻中的主題（最近 14 天發過的，連同任何角度整個擋掉）
    cooling = []
    for item in (exclude_seafood or [])[:TOPIC_COOLDOWN_DAYS]:
        t = item.split("/")[0]
        if t not in cooling:
            cooling.append(t)

    cooldown_note = ""
    if cooling:
        cooldown_note = (
            f"\n\n🚫 以下主題在最近 {TOPIC_COOLDOWN_DAYS} 天內已經發過，"
            f"**本次連同任何角度一律不可使用**（這是硬性規定，不是偏好）："
            f"{'、'.join(cooling)}"
        )

    # 一年內的已用組合。依主題分組並略過冷卻中的主題——
    # 那些主題已被上面整個擋掉，再列它們用過哪些角度是純冗餘。
    # 逐筆平列在滿載 365 筆時約 3,650 字元，這樣寫約 1,300，且不損失任何資訊。
    used = OrderedDict()
    cooling_set = set(cooling)
    for item in exclude_seafood or []:
        topic, _, angle = item.partition("/")
        if topic in cooling_set:
            continue
        used.setdefault(topic, [])
        if angle and angle not in used[topic]:
            used[topic].append(angle)

    # 今日大類由程式指定，不交給模型自己平衡
    day_index = datetime.now().timetuple().tm_yday
    today_category = CATEGORY_ROTATION[day_index % len(CATEGORY_ROTATION)]
    category_note = (
        f"\n\n🎯 **本次指定類別：【{today_category}】**（由排程輪替決定，用來讓四大類平均穿插）。"
        f"角度只能從該類的清單裡選。"
        f"若該類主題全部在冷卻中或組合已用完，才可改選其他類，"
        f"並優先挑選最近較少出現的類別。"
    )

    # 物種群組連續管制：主題名不同但同類的（花蟹/三點蟹/石蟳）不可連著出現
    recent_groups = []
    for item in (exclude_seafood or [])[:GROUP_COOLDOWN]:
        g = SPECIES_GROUP_OF.get(item.split("/")[0])
        if g and g not in recent_groups:
            recent_groups.append(g)

    group_note = ""
    if recent_groups:
        examples = "；".join(
            f"{g}（{'、'.join(SPECIES_GROUPS[g][:6])}…）" for g in recent_groups
        )
        group_note = (
            f"\n\n🚫 最近 {GROUP_COOLDOWN} 則已出現過這些**物種群組**，本次一律不可再選：{examples}。"
            f"理由：主題名字不同但觀眾看起來是同一種東西，連著發會顯得題材貧乏。"
        )

    exclude_note = ""
    if used:
        pairs = "；".join(f"{t}：{'、'.join(a)}" for t, a in used.items())
        exclude_note = (
            "\n\n⚠️ 以下主題的這些角度一年內已發過，本次不可重複相同組合"
            f"（同一主題換沒用過的角度則可以）：{pairs}"
        )

    return f"""你是台灣海洋達人。生成一則台灣讀者有興趣的知識，JSON格式：
{{
  "seafood_zh": "主題名稱（2-5字）",
  "seafood_en": "English name or term",
  "category": "本則知識的角度分類（從以下選一）：外觀辨別｜食用知識｜生態習性｜台灣特色｜處理與保存｜料理法｜選購技巧｜常見誤解｜名稱由來｜相似魚種比較｜產季與時機｜冷知識趣聞｜漁法介紹｜捕魚時機｜漁港文化｜漁民智慧｜船種介紹｜漁具設備｜出海作業｜飲食文化｜冷凍原理｜破除迷思｜冷知識",
  "title_zh": "標題（格式：XX的祕密 或 你不知道的XX，10字內）",
  "title_en": "Title in English (under 35 chars)",
  "content": "5到6句有趣知識，繁體中文。每句獨立，加換行符\\n分隔。每句不超過28字。內容要有層次：第一句引起好奇，中間深入說明，最後一句給讀者帶走的亮點。",
  "illustration_prompt": "描述插圖主體的英文句子，用於 AI 繪圖。要能精準對應本則知識內容。格式：Watercolor illustration of [具體主體與場景]，例如：Watercolor illustration of a Taiwanese fisherman sitting on a small wooden boat doing pole-and-line fishing, calm sea, warm morning light"
}}

從以下四大類中選一個主題，再從該類的角度中選一個角度，組合出今日內容。
目標是在365天內不重複相同的「主題+角度」組合。

【海鮮知識】角度（12）：外觀辨別｜食用知識｜生態習性｜台灣特色｜處理與保存｜料理法｜選購技巧｜常見誤解｜名稱由來｜相似魚種比較｜產季與時機｜冷知識趣聞
▸ 龜吼在地（優先，可以講「我們的」「船上」）：
  花蟹、三點蟹、石蟳（合稱萬里蟹）、小卷、透抽、花枝、軟絲、
  白帶魚、黃雞魚、紅甘、赤鯮、午仔魚、鯖魚、海膽
▸ 台灣其他產地（可講，但**必須明講產地**，例如「東港的黑鮪」「澎湖的土魠」，
  絕不可寫成好像我們有貨）：黑鮪魚、旗魚、劍旗魚、鬼頭刀、鮪魚、正鰹、飛魚、
  秋刀魚、烏魚子、土魠魚、虱目魚、石斑魚、牡蠣、文蛤、九孔
▸ 全球性（純科普，**絕不可暗示供貨**）：鮭魚、鱈魚、帝王蟹、鯡魚、龍蝦

【捕魚知識】角度（4）：漁法介紹｜捕魚時機｜漁港文化｜漁民智慧
龜吼實際使用（可以講「我們」）：棒受網、刺網、一支釣、延繩釣、拖網、蟹籠、手釣、潛水採集
▸ 龜吼的實務細節（在地，很好講）：棒受網先用集魚燈聚魚再收攏光源、
  透抽一支釣用 5-6 只假餌並依潮水調整深度、避開滿月出海（月光強不利釣況）、
  農曆下旬出海作業約三週
▸ 國際漁法（**必須講明是遠洋／國際，不可寫成我們的船**）：
  延繩釣幹線 20-100 公里、1,000-5,000 個鉤、鉤距 30-50 公尺；
  魷釣船的集魚燈亮到衛星（NASA VIIRS）看得見，南大西洋離岸 300-500 公里會出現「光之城」
其他漁法：定置網、圍網、流刺網、魚叉、曳繩釣
漁港：龜吼漁港（主場）、野柳漁港、富基漁港、基隆正濱漁港、澳底漁港、南方澳漁港

【漁船知識】角度（4）：船種介紹｜漁具設備｜出海作業｜飲食文化
船種：膠筏、小漁船、延繩釣船、拖網船、圍網船、娛樂漁船
設備原理（**一般人不知道的，優先選這些**）：
  魚探機看到的其實是「魚鰾裡的空氣」不是魚本身——肌肉密度和水幾乎一樣不反射聲波，
  魚鰾是空氣才形成強反射；運作頻率 20-200 kHz；不同魚種魚鰾形狀不同回波也不同；
  螢幕上呈弧形是因為魚游過聲波錐形範圍時距離先近後遠
  集魚燈、GPS定位、無線電通訊、漁網材質
船上保鮮：碎冰（表面積大降溫快，適合短時間與陳列）、塊冰（融得慢，適合長時間）、
  冷海水RSW（省人力但魚倒進去瞬間水溫會被拉高）、泥狀冰（包覆每條魚，最溫和）
生活：出海時間週期、船上分工、惡劣天氣應對、討海人飲食、漁村文化與信仰

【冷鏈知識】角度（3）：冷凍原理｜破除迷思｜冷知識
原理：急速與慢速冷凍的差別、最大冰晶生成帶、解凍滴液、冰衣（glazing）、凍燒、
  真空包裝在防什麼、魚油氧化與酸敗、脂肪含量與風味期限、清洗用水的滲透壓
破除迷思：安全與品質是兩件事、保存期限是風味期限不是安全大限、
  冷凍魚上那層冰不是偷斤減兩、二次冷凍（冷藏室解凍再冷凍是安全的，代價是滴液）、
  「現流一定比冷凍好吃」不一定
冷知識：**生魚片鮪魚要凍到 −60°C**——鮪魚的紅色來自肌紅蛋白，自氧化成變性肌紅蛋白
  就會褐變，只有 −60°C 以下能真正止住；日本處理的鮪魚約八成走超低溫冷凍。
  凍融一次約流失 5% 重量的滴液。冷鏈有幾個環節、家用冰箱與商用冷凍庫的差別

🔴 【冷鏈知識】的硬性限制（涉及食品安全，違反等於發出錯誤的食安資訊）：
  1. **只准使用這些已查證的數字**：−18°C（冷凍保存）、−1～−5°C（最大冰晶生成帶）、
     −60°C（鮪魚超低溫）、5%（凍融一次的滴液）、八成（日本鮪魚超低溫比例、
     最大冰晶生成帶結冰的水分比例）。
     **其他任何溫度、天數、月數、小時數一律不准出現。** 不確定就講原理，不要給數字。
  2. **絕對不可出現「生食級」「可生食」「生魚片等級」**——涉及食品標示規範。
  3. **不可給保存期限**。要講就講「取決於溫度、包裝方式與魚的脂肪含量」。
  4. 講二次冷凍時**條件不可拆開**：冷藏室解凍再冷凍是安全的，室溫解凍不是。

🔴 【捕魚知識】與【漁船知識】的規模界線：
  國際／遠洋的數字（延繩釣百公里、衛星看得見的集魚燈）**必須明講是遠洋或國際漁業**。
  龜吼是近海小船，**同樣的原理可以講，規模不可以混為一談**。
  寫成「我們的船衛星看得到」就是產地造假。

🔴 防編造紅線（**這是整個品牌最重要的一條，違反的傷害大於文案平庸**）：
  1. **不可編造「龜吼漁民怎麼做」的具體做法、口訣、判斷竅門。**
     像「龜吼漁民靠觸鬚長度一眼辨識」這種句子——聽起來很內行，但那是編的，
     而且**只有老闆本人知道實際做法**，寫錯會被同行一眼看穿。
     要提在地做法，只能用已經寫在上面的（棒受網先聚魚再收攏光源、
     透抽一支釣用 5-6 只假餌、避開滿月出海）。
  2. **不可講具體價格、到貨時間、當天有沒有貨。**
  3. **不確定的辨別方法不要給。** 可以說「看體型大小」這種明確的，
     不要編造「看某個部位的某個特徵」這種具體到像是內行才知道的細節。
  4. **不確定的產季、規格、重量一律不提。**
  寧可寫得平淡，也不能講錯——講錯一次被轉述出去，整個產地真實性就垮了。

注意：若涉及潮汐、海流、洋流等自然現象，必須結合漁民作業或捕魚技術來說明，不可單純介紹自然現象本身。{season_note}{category_note}{group_note}{exclude_note}{cooldown_note}

只輸出 JSON 物件本身，不要加任何說明文字、註解或 markdown 程式碼框。"""


def knowledge_via_claude(prompt):
    """Claude 生成今日知識＋畫圖提示詞，從回應中擷取 JSON 物件"""
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            # ⚠️ 2048 不夠。Sonnet 5 預設開 adaptive thinking，thinking 會先吃掉一部分
            #    預算，剩下的寫不完 JSON 就被截斷，於是 rfind("}") 找不到收尾括號、
            #    判定「未含 JSON」而退到 Gemini——每天默默用備援產文案卻沒人發現
            #    （通知這件事的 LINE 推播在 2026-08-28 之前也是壞的）。
            #    youtube_auto 早就用 8192，這裡對齊到 4096。
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=90,
    )
    data = r.json()
    if "content" not in data:
        raise RuntimeError(f"Claude 回傳異常：{data}")
    # Sonnet 5 預設開 adaptive thinking，content[0] 可能是 thinking block
    text = next((b["text"] for b in data["content"] if b.get("type") == "text"), "")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        # 分清楚「沒產出 JSON」與「產了但被截斷」——兩者的處置完全不同，
        # 而原本的訊息一律說「未含 JSON」，看 log 的人會往錯的方向查。
        why = (
            "被 max_tokens 截斷（stop_reason=%s）" % data.get("stop_reason")
            if start != -1
            else "回應未含 JSON"
        )
        raise RuntimeError(f"Claude {why}：{text[:200]}")
    return json.loads(text[start : end + 1])


def knowledge_via_gemini(prompt):
    """Gemini fallback（2.5-flash → 2.0-flash → 2.0-flash-lite）"""
    # ⚠️ 不要釘死版本號。2026-08-28 發現 gemini-2.0-flash 與 -flash-lite 都已 404 下架，
    #    當時 2.5-flash 又剛好 503，於是整條 fallback 全滅——Claude 一掛就開天窗。
    #    用 -latest 別名才不會被下架；503 是暫時性且會在模型間輪動，所以要留多個備援。
    for model in [
        "gemini-flash-latest",
        "gemini-2.5-flash",
        "gemini-flash-lite-latest",
    ]:
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


def _fallback_reason(err):
    """把例外翻成「你該做什麼」，而不是只丟原始錯誤。"""
    t = str(err)
    if "401" in t or "authentication" in t.lower():
        return "金鑰失效——到 platform.claude.com 建新的，再跑 scripts/set_secret.py"
    if "credit" in t.lower() or "billing" in t.lower():
        return "餘額不足——到 platform.claude.com 儲值"
    if "429" in t or "rate" in t.lower():
        return "被限流，通常隔天自己會好"
    if "529" in t or "overloaded" in t.lower() or "500" in t:
        return "Claude 服務暫時異常，通常自己會好"
    return t[:120]


def notify_fallback(err):
    """降級到 Gemini 時推一則 LINE。

    ⚠️ 這個 fallback 原本完全靜默——不開天窗，但代價是你只會覺得
    「最近文案怪怪的」卻找不到原因。2026-08-26 補上通知。
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from line_assistant.notify import notify

        notify(
            "⚠️ 今天的 IG 文案是 Gemini 產的，不是 Claude\n"
            f"原因：{_fallback_reason(err)}\n\n"
            "貼文照常發出，但品質會比平常差。"
        )
    except Exception as e:  # 通知失敗絕不能連累發文
        print(f"[notify] 推播失敗（不影響發文）：{e}", flush=True)


def notify_no_illustration(err):
    """插圖生成失敗、改用 logo 頂替時推一則 LINE。

    ⚠️ 2026-08-28 補：原本 generate_illustration 失敗會直接往上拋，
    整條發文就斷了——文案那段明明有 Gemini fallback，插圖這段卻沒有，
    等於 OpenAI 一斷天窗就開。不開天窗優先，但一定要讓人知道。
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from line_assistant.notify import notify

        notify(
            "⚠️ 今天的 IG 貼文沒有插圖，出的是純文字版面\n"
            f"原因：{_fallback_reason(err)}\n\n"
            "貼文照常發出。要補正常版：重跑 daily_post，或手動換圖重發。"
        )
    except Exception as e:  # 通知失敗絕不能連累發文
        print(f"[notify] 推播失敗（不影響發文）：{e}", flush=True)


def illustration_or_none(illustration_prompt):
    """插圖生成失敗就出純文字版面——寧可樸素，也不要斷掉每日不缺席的節奏。

    ⚠️ 不要拿 LOGO 頂替：logo.png 是深色底，而合成時的去背只吃掉接近白的像素，
    結果會是一塊黑方塊壓在米色卡紙上，還蓋住模板的標題（2026-08-28 實際試過）。
    """
    try:
        return generate_illustration(illustration_prompt)
    except Exception as e:
        print(f"⚠️ 插圖生成失敗，改出純文字版面：{e}", flush=True)
        notify_no_illustration(e)
        return None


def generate_knowledge(exclude_seafood=None):
    """今日知識生成：Claude 為主，Gemini 為 fallback"""
    prompt = build_knowledge_prompt(exclude_seafood)
    if ANTHROPIC_KEY:
        try:
            return knowledge_via_claude(prompt)
        except Exception as e:
            print(f"[Claude] 失敗，改用 Gemini fallback：{e}", flush=True)
            notify_fallback(e)
    else:
        print("[Claude] 沒有設定 ANTHROPIC_API_KEY，直接用 Gemini", flush=True)
        notify_fallback("ANTHROPIC_API_KEY 沒有設定")
    return knowledge_via_gemini(prompt)


def generate_illustration(illustration_prompt):
    """OpenAI 生成水彩插圖；Pollinations 於 2026-08 改付費制且 flux 下架"""
    prompt = (
        f"{illustration_prompt}, pure white background, "
        "traditional natural history watercolor illustration style, "
        "soft warm color palette, highly detailed, beautiful, no text, no shadow, centered composition"
    )
    body = {
        "model": os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1-mini"),
        "prompt": prompt,
        "size": "1024x1024",
        "quality": os.environ.get("OPENAI_IMAGE_QUALITY", "low"),
        "n": 1,
    }
    last = None
    # 3 次而非 6 次：每次 timeout 180 秒＋遞增等待，6 次最壞約 20 分鐘，
    # 會超過 workflow 的 timeout-minutes 而被砍在半路——重試等於白設。
    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                json=body,
                timeout=180,
            )
            if r.status_code == 200:
                data = base64.b64decode(r.json()["data"][0]["b64_json"])
                return Image.open(io.BytesIO(data)).convert("RGBA")
            last = f"HTTP {r.status_code} {r.text[:200]}"
            if r.status_code not in (408, 429, 500, 502, 503, 504):
                break
        except Exception as e:
            last = e
        time.sleep(min(5 + attempt * 5, 30))
    raise RuntimeError(f"插圖生成失敗：{last}")


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


def compose_image(
    knowledge,
    illustration,
    illus_alpha=255,
    show_header=True,
    max_lines=None,
    stats=None,
):
    """PIL 合成最終貼文圖片。

    後三個參數只給影片版逐格取用（`card_video.py`）——**版面永遠用完整內容計算**，
    它們只決定「這一格畫到哪」，所以每一格都跟最終靜態圖對得上。
    預設值等同原本行為，靜態圖走的是同一條路。
    """
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
    ILLUS_SIZE = (
        0 if illustration is None else min(1600, max(900, TOTAL_AVAIL - est_text_h))
    )

    # 插圖：去白背景 → 自動裁切主體 → 填滿插圖區域（沒有插圖就整段跳過）
    if illustration is not None:
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
        if illus_alpha < 255:
            illus.putalpha(
                illus.getchannel("A").point(lambda v: v * illus_alpha // 255)
            )
        base.paste(
            illus, ((W - new_w) // 2, ILLUS_Y + (ILLUS_SIZE - new_h) // 2), illus
        )

    # 分隔線 + 日期標題
    today = datetime.now().strftime("%Y.%m.%d")
    LINE_Y = ILLUS_Y + ILLUS_SIZE + GAP

    # 內文先排版——字型與行數決定整組的高度，置中才算得出來
    font_body, lines, line_h = fit_body_font(
        draw, knowledge["content"], MAX_W, CARD_BOTTOM - (LINE_Y + HEADER_H), FONT
    )
    if stats is not None:
        stats["lines"] = len(lines)  # 影片版要靠行數排節奏，不另外重算一次排版
    if illustration is None:
        # 純文字版面文字通常填不滿，整組垂直置中，免得下半張開天窗
        block_h = HEADER_H + len(lines) * line_h
        LINE_Y += max(0, (CARD_BOTTOM - LINE_Y - block_h) // 2)

    if show_header:
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

    # 內文
    TEXT_START = LINE_Y + HEADER_H
    for i, line in enumerate(lines if max_lines is None else lines[:max_lines]):
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
    illustration = illustration_or_none(knowledge["illustration_prompt"])
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
