#!/usr/bin/env python3
"""用 Claude Sonnet 4.6 生成一支英文「歷史/未解之謎」YouTube Shorts 腳本。

輸出 JSON：title / narration / scenes / description / tags / topic
複用 instagram/generate_post.py 的 Claude 呼叫寫法（單一 user message + JSON 擷取）。
"""
import json, os, random, urllib.request, base64

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
RECENT_FILE = os.path.join(BASE, "recent_topics.json")
RECENT_KEEP = 120
ANGLE_KEEP = 6

CLAUDE_MODEL = "claude-sonnet-5"

# 旁白語言：zh＝繁中（2026-08-26 起的預設）、en＝英文。與 build_video 同一個環境變數
NARRATION_LANG = os.environ.get("YT_NARRATION_LANG", "zh")

# 每支影片隨機挑一個敘事框架，讓結構不重複、且必須帶編輯觀點——
# YouTube 2026 inauthentic content 政策點名「量產樣板＋逐字朗讀」，靠這個脫離該形態。
ANGLES = [
    (
        "contrarian",
        "Challenge a widely-repeated claim about this subject: state what most people believe, then show why the real evidence is weaker, stranger or more interesting than the popular version.",
    ),
    (
        "detective",
        "Open on one concrete anomaly — a single odd measurement, artefact or observation — and reason forward from it step by step, like an investigation.",
    ),
    (
        "connection",
        "Link two things the audience would never put together (two eras, two disciplines, two discoveries) and argue why that connection matters.",
    ),
    (
        "human",
        "Tell it through the person who found it: what they were actually looking for, what it cost them, and what they never lived to know.",
    ),
    (
        "scale",
        "Rebuild the viewer's intuition through contrasts of size, time or number, until something familiar starts to feel alien.",
    ),
    (
        "failure",
        "Start from a theory that turned out wrong or was abandoned, and show what its collapse revealed that the correct answer never would have.",
    ),
    (
        "absence",
        "Focus on what is missing — evidence that should exist and does not — and argue what that silence implies.",
    ),
    (
        "method",
        "Make the method the mystery: how could anyone possibly know this? Walk through the ingenuity of the measurement itself.",
    ),
    (
        "reframe",
        "Argue that the question everyone asks about this mystery is the wrong question, and propose a sharper one.",
    ),
    (
        "legacy",
        "Begin with something that still shapes our world today, then trace it back to its unresolved origin.",
    ),
]

_LAST_ANGLE = None


GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]


def _load_key(env_name, cfg_name):
    if os.environ.get(env_name):
        return os.environ[env_name]
    cfg = os.path.join(REPO, "config", "instagram_config.json")
    if os.path.exists(cfg):
        return json.load(open(cfg)).get(cfg_name, "")
    return ""


ANTHROPIC_KEY = _load_key("ANTHROPIC_API_KEY", "anthropic_api_key")
GEMINI_KEY = _load_key("GEMINI_KEY", "gemini_api_key")


def _load_state():
    if os.path.exists(RECENT_FILE):
        try:
            return json.load(open(RECENT_FILE))
        except Exception:
            return {}
    return {}


def load_recent():
    return _load_state().get("recent", [])


def load_recent_angles():
    return _load_state().get("recent_angles", [])


def save_recent(recent, new_topic):
    updated = ([new_topic] + recent)[:RECENT_KEEP]
    angles = load_recent_angles()
    if _LAST_ANGLE:
        angles = ([_LAST_ANGLE] + angles)[:ANGLE_KEEP]
    content = json.dumps(
        {"recent": updated, "recent_angles": angles}, ensure_ascii=False, indent=2
    )
    if not os.environ.get("GITHUB_TOKEN"):
        open(RECENT_FILE, "w", encoding="utf-8").write(content)
        return
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ.get("GITHUB_REPO", "lien2fish/liam-ai-agent")
    path = "youtube_auto/recent_topics.json"
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    body = {
        "message": f"yt: recent topic {new_topic}",
        "content": base64.b64encode(content.encode()).decode(),
    }
    try:
        existing = json.load(
            urllib.request.urlopen(urllib.request.Request(url, headers=headers))
        )
        body["sha"] = existing["sha"]
    except Exception:
        pass
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=headers, method="PUT"
    )
    urllib.request.urlopen(req)


def build_prompt(recent, mode="long", angle=None):
    zh = NARRATION_LANG == "zh"
    if mode == "short":
        dur, n_sent, n_scene = ("punchy 45-55 second Short", "6-8 sentences", "4 to 6")
        words = "約 200-240 個中文字" if zh else "~75-110 English words"
        struct = "First sentence = an instant gripping hook; build ONE single fascinating mystery fast; last sentence = a haunting open question. Keep it tight and punchy."
    else:
        dur, n_sent, n_scene = ("2-3 minute video", "18-24 sentences", "10 to 14")
        words = "約 640-750 個中文字" if zh else "~290-380 English words"
        struct = "First sentence = a gripping hook that sparks curiosity; the middle builds the mystery with fascinating facts and unanswered questions; the last sentence leaves the viewer with a haunting open question or sense of wonder."
    if zh:
        title_spec = '"title": "繁體中文標題，14-22 字。必須具體點出這支片真正的那一個發現或矛盾，不要抽象名詞堆疊；可以留懸念，但不准誇大或編造（禁用「震驚」「你不知道的」「史上最」這類套路）"'
        intro_spec = '"intro_zh": "開場卡上的一句話，18-32 字。必須把標題再往前推一步，不可以只是換句話重講 title"'
        cover_spec = '"cover_zh": "封面上的短句，4-8 個字，一眼就讀完的鉤子（像「地圖畫錯了嗎」），不是把標題縮寫"'
        sent_spec = '"sentences": [{"zh": "一句用來唸出來的繁體中文旁白（口語、精煉、留神秘感；不要翻譯腔、不要書面語）"}]'
        desc_spec = (
            '"description": "2-3 句繁體中文影片說明，結尾接 4-6 個繁體中文 hashtag"'
        )
        tags_spec = (
            '"tags": ["8-12 個繁體中文搜尋關鍵字，專有名詞可保留英文，不要 # 符號"]'
        )
        lang_note = f'The "sentences" array is the spoken narration in TRADITIONAL CHINESE ({n_sent}, {words}). It is BOTH the voiceover and the on-screen subtitle, so every sentence must sound natural read aloud. {struct} NO stage directions, NO emojis. Write the title, intro_zh, sentences, description and tags ALL in Traditional Chinese; keep "topic" and "scenes" in English.'
    else:
        title_spec = '"title": "intriguing, curiosity-driven English title under 60 characters (evokes wonder, not clickbait lies) — shown on the opening title card"'
        intro_spec = '"intro_zh": "一句吸引人的繁體中文開場白，點出這支影片要探討的謎團是什麼（約 18-32 字，勾起好奇，顯示在開場標題卡）"'
        cover_spec = '"cover_en": "3-5 word phrase for the thumbnail — readable at a glance, not an abbreviated title"'
        sent_spec = '"sentences": [{"en": "one spoken English sentence", "zh": "對應的繁體中文（口語、精煉、保留神秘感）"}]'
        desc_spec = '"description": "2-3 sentence YouTube description followed by 4-6 relevant hashtags"'
        tags_spec = '"tags": ["8-12 lowercase search tags, no # symbol"]'
        lang_note = f'The "sentences" array is the spoken narration split sentence by sentence ({n_sent}, {words} total). {struct} Each item pairs the English sentence ("en", for voiceover) with its Traditional Chinese translation ("zh", for on-screen subtitles). NO stage directions, NO emojis.'

    avoid = ""
    if recent:
        avoid = (
            "\n\nAvoid these recently-used topics (pick something different): "
            + ", ".join(recent[:60])
        )
    angle_block = ""
    if angle:
        angle_block = f"""

EDITORIAL ANGLE — build this specific video on this framing, not a generic overview:
{angle[1]}
The title, the hook and the closing line must all follow from this angle."""
    return f"""You are a captivating YouTube narrator creating awe-inspiring videos about the GREATEST UNSOLVED MYSTERIES OF THE UNIVERSE and ANCIENT CIVILISATIONS, for a curious global audience who love wonder, the unknown, and "what if" questions.

Generate ONE {dur}. Output ONLY a JSON object, no markdown, no commentary:
{{
  "topic": "short unique kebab-case slug for de-duplication, e.g. dark-matter or gobekli-tepe",
  {title_spec},
  "thesis": "one English sentence stating the original argument this specific video makes — a claim you are asserting, NOT a topic label. Bad: 'The mystery of dark matter.' Good: 'Dark matter's best evidence is not what it explains, but what it fails to.'",
  {intro_spec},
  {cover_spec},
  {sent_spec},
  "scenes": ["{n_scene} cinematic image-generation prompts in English, one per beat. Epic, awe-inspiring, atmospheric scenes (deep space nebulae, black holes, ancient stone ruins, lost pyramids, mysterious artefacts, vast cosmic vistas). Photoreal, dramatic lighting, cinematic."],
  {desc_spec},
  {tags_spec}
}}

{lang_note}

Pick genuinely fascinating themes: unsolved cosmic mysteries (dark matter, black holes, the edge of the universe, the Fermi paradox, what came before the Big Bang) and ancient civilisation enigmas (Göbekli Tepe, lost cities, unexplained megaliths, vanished peoples, undeciphered scripts). Be factual; where unproven, frame it honestly as an open mystery that invites wonder.{angle_block}

ORIGINALITY — this matters more than any other instruction:
- Do NOT write an encyclopedia summary. Every sentence of narration must serve the thesis above.
- Carry a point of view: your own reading of what the evidence means, what you find genuinely unsettling about it, and where the honest limits of current knowledge lie.
- Say plainly when something is disputed, when a popular claim is overstated, and when the honest answer is "nobody knows". Never invent findings, quotes, dates or studies — the wonder must come from what is actually true.
- Never open with a worn formula such as "Have you ever wondered", "Imagine this", "Picture a world" or "Scientists were baffled". Open on something concrete and specific.
- Avoid the flat "fact, fact, fact, rhetorical question" rhythm. Let the argument build and turn.{avoid}"""


def _extract_json(text):
    s, e = text.find("{"), text.rfind("}")
    if s < 0 or e < 0:
        raise ValueError(f"回應未含 JSON：{text[:200]}")
    return json.loads(text[s : e + 1])


def _call_claude(prompt):
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(
            {
                "model": CLAUDE_MODEL,
                "max_tokens": 8192,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode(),
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    data = json.load(urllib.request.urlopen(req))
    if "content" not in data:
        raise RuntimeError(f"Claude 回傳異常：{data}")
    # Sonnet 5 預設開 adaptive thinking，content[0] 可能是 thinking block
    text = next((b["text"] for b in data["content"] if b.get("type") == "text"), "")
    return _extract_json(text)


def _call_gemini(prompt):
    """Claude 不可用時的備援；思考型模型須關掉 thinking，否則輸出被截斷。"""
    last = None
    for model in GEMINI_MODELS:
        cfg = {"response_mime_type": "application/json", "maxOutputTokens": 8192}
        if any(t in model for t in ("2.5", "3.1", "3.5", "3-")):
            cfg["thinkingConfig"] = {"thinkingBudget": 0}
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}",
            data=json.dumps(
                {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": cfg}
            ).encode(),
            headers={"content-type": "application/json"},
            method="POST",
        )
        try:
            data = json.load(urllib.request.urlopen(req))
            return _extract_json(data["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as e:
            last = e
            print(f"[gemini/{model}] 失敗：{e}", flush=True)
    raise RuntimeError(f"所有 Gemini 模型均失敗：{last}")


def _finalize(script):
    sents = script.get("sentences", [])
    if not sents:
        raise ValueError("無 sentences")
    script["narration"] = " ".join(x["en"] for x in sents)
    script["subtitles_zh"] = [x["zh"] for x in sents]
    return script


def pick_angle():
    used = load_recent_angles()
    pool = [a for a in ANGLES if a[0] not in used] or ANGLES
    return random.choice(pool)


def generate(recent=None, mode="long"):
    global _LAST_ANGLE
    recent = recent if recent is not None else load_recent()
    angle = pick_angle()
    _LAST_ANGLE = angle[0]
    print(f"[generate] 敘事框架：{angle[0]}", flush=True)
    prompt = build_prompt(recent, mode, angle)
    last = None
    if ANTHROPIC_KEY:
        for _ in range(3):  # Claude 偶爾吐不合法/截斷 JSON，重試生成
            try:
                return _finalize(_call_claude(prompt))
            except Exception as e:
                last = e
                print(f"[claude] 解析失敗，重試：{e}", flush=True)
    if GEMINI_KEY:
        print(f"[generate] Claude 不可用，改用 Gemini fallback（{last}）", flush=True)
        try:
            return _finalize(_call_gemini(prompt))
        except Exception as e:
            last = e
    raise RuntimeError(f"腳本生成失敗（Claude 與 Gemini 皆不可用）：{last}")


if __name__ == "__main__":
    script = generate()
    print(json.dumps(script, ensure_ascii=False, indent=2))
