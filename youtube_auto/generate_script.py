#!/usr/bin/env python3
"""用 Claude Sonnet 4.6 生成一支英文「歷史/未解之謎」YouTube Shorts 腳本。

輸出 JSON：title / narration / scenes / description / tags / topic
複用 instagram/generate_post.py 的 Claude 呼叫寫法（單一 user message + JSON 擷取）。
"""
import json, os, urllib.request, base64

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
RECENT_FILE = os.path.join(BASE, "recent_topics.json")
RECENT_KEEP = 120

CLAUDE_MODEL = "claude-sonnet-4-6"


def _load_key():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    cfg = os.path.join(REPO, "config", "instagram_config.json")
    if os.path.exists(cfg):
        return json.load(open(cfg)).get("anthropic_api_key", "")
    return ""


ANTHROPIC_KEY = _load_key()


def load_recent():
    if os.path.exists(RECENT_FILE):
        try:
            return json.load(open(RECENT_FILE)).get("recent", [])
        except Exception:
            return []
    return []


def save_recent(recent, new_topic):
    updated = ([new_topic] + recent)[:RECENT_KEEP]
    content = json.dumps({"recent": updated}, ensure_ascii=False, indent=2)
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


def build_prompt(recent):
    avoid = ""
    if recent:
        avoid = (
            "\n\nAvoid these recently-used topics (pick something different): "
            + ", ".join(recent[:60])
        )
    return f"""You are a gentle YouTube Shorts writer creating SOOTHING, HEALING animated content for a global audience who watch to relax, feel comforted, and calm their minds before sleep or after a hard day.

Generate ONE 30-45 second cozy healing Short. Output ONLY a JSON object, no markdown, no commentary:
{{
  "topic": "short unique kebab-case slug for de-duplication, e.g. rainy-window-tea",
  "title": "warm, gentle, inviting English title under 70 characters (cozy/calming vibe, not clickbait)",
  "sentences": [{{"en": "one soft spoken English sentence", "zh": "對應的繁體中文（溫柔、口語、療癒）"}}],
  "scenes": ["4 to 6 soft animated illustration prompts in English, one per beat. Cozy, dreamy, gentle storybook scenes (a sleepy cat by a rainy window, a tiny cottage under stars, warm tea steam, a fox curled in autumn leaves). Soft pastel, kawaii, Studio-Ghibli-like."],
  "description": "2-3 gentle sentence YouTube description followed by 4-6 calming hashtags",
  "tags": ["8-12 lowercase search tags, no # symbol"]
}}

The "sentences" array is the spoken narration split sentence by sentence (6-9 short sentences, ~70-110 English words total — slow and unhurried). Tone is warm, tender, reassuring, like a soft bedtime voice. It can be a tiny comforting micro-story, a gentle reflection, or soothing affirmations of self-kindness, rest, and hope. Each item pairs the English sentence ("en", for voiceover) with its Traditional Chinese translation ("zh", for on-screen subtitles). NO stage directions, NO emojis.

Pick cozy, healing, heart-warming themes (rest, self-compassion, slowing down, small joys, comfort, gentle hope, nature's calm). Keep it sincere and softly poetic.{avoid}"""


def generate(recent=None):
    recent = recent if recent is not None else load_recent()
    prompt = build_prompt(recent)
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(
            {
                "model": CLAUDE_MODEL,
                "max_tokens": 1500,
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
    text = data["content"][0]["text"]
    s, e = text.find("{"), text.rfind("}")
    script = json.loads(text[s : e + 1])
    # 由 sentences 推導英文旁白（TTS 用）與中文字幕清單
    sents = script.get("sentences", [])
    script["narration"] = " ".join(x["en"] for x in sents)
    script["subtitles_zh"] = [x["zh"] for x in sents]
    return script


if __name__ == "__main__":
    script = generate()
    print(json.dumps(script, ensure_ascii=False, indent=2))
