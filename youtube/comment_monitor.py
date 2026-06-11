#!/usr/bin/env python3
"""
YouTube Shorts 留言監控
每日抓取頻道的 Shorts 影片留言，與快取比對找出新留言，
寫入每日報告並寄送 Email 通知。
"""
import json, os, smtplib, urllib.request, urllib.parse, urllib.error
from datetime import datetime
from email.mime.text import MIMEText

API_KEY = os.environ["YT_API_KEY"]
CHANNEL_ID = os.environ["YT_CHANNEL_ID"]
GMAIL_USER = os.environ.get("GMAIL_USER", "lien2fish@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

API_BASE = "https://www.googleapis.com/youtube/v3"

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(ROOT, "monitor_state.json")
REPORTS_DIR = os.path.join(os.path.dirname(ROOT), "reports")

SHORTS_MAX_SECONDS = 60


def api_get(path, params):
    params = {**params, "key": API_KEY}
    url = f"{API_BASE}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read())


def parse_duration(iso_dur):
    """ISO 8601 duration (e.g. PT45S, PT1M30S) -> 秒數"""
    import re

    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_dur)
    h, mnt, s = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mnt * 60 + s


def get_shorts_video_ids():
    ch = api_get("channels", {"part": "contentDetails", "id": CHANNEL_ID})
    uploads_playlist = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    items = api_get(
        "playlistItems",
        {"part": "contentDetails", "playlistId": uploads_playlist, "maxResults": 25},
    )["items"]
    video_ids = [i["contentDetails"]["videoId"] for i in items]
    if not video_ids:
        return []

    videos = api_get(
        "videos", {"part": "contentDetails,snippet", "id": ",".join(video_ids)}
    )["items"]

    shorts = []
    for v in videos:
        seconds = parse_duration(v["contentDetails"]["duration"])
        if seconds <= SHORTS_MAX_SECONDS:
            shorts.append((v["id"], v["snippet"]["title"]))
    return shorts


def get_comments(video_id):
    try:
        result = api_get(
            "commentThreads",
            {
                "part": "snippet",
                "videoId": video_id,
                "order": "time",
                "maxResults": 50,
                "textFormat": "plainText",
            },
        )
    except urllib.error.HTTPError as e:
        if e.code == 403:  # 留言關閉
            return []
        raise
    comments = []
    for item in result.get("items", []):
        c = item["snippet"]["topLevelComment"]["snippet"]
        comments.append(
            {
                "id": item["id"],
                "author": c["authorDisplayName"],
                "text": c["textDisplay"],
                "publishedAt": c["publishedAt"],
            }
        )
    return comments


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_email(subject, body):
    if not GMAIL_APP_PASSWORD:
        print("⚠️ 未設定 GMAIL_APP_PASSWORD，略過寄信")
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    state = load_state()
    seen = state.setdefault("seen_comment_ids", {})

    shorts = get_shorts_video_ids()
    new_comments = []  # (video_title, video_id, comment)

    for video_id, title in shorts:
        seen_ids = set(seen.get(video_id, []))
        comments = get_comments(video_id)
        for c in comments:
            if c["id"] not in seen_ids:
                new_comments.append((title, video_id, c))
                seen_ids.add(c["id"])
        seen[video_id] = list(seen_ids)

    save_state(state)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"youtube_comments_{today}.md")
    lines = [f"# YouTube Shorts 留言通知 {today}\n"]

    if new_comments:
        lines.append(f"共 {len(new_comments)} 則新留言：\n")
        for title, video_id, c in new_comments:
            lines.append(f"## {title}")
            lines.append(f"https://www.youtube.com/shorts/{video_id}")
            lines.append(f"- **{c['author']}**：{c['text']}")
            lines.append(f"  - {c['publishedAt']}")
            lines.append("")
    else:
        lines.append("今日無新留言。\n")

    report = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)

    if new_comments:
        send_email(f"YouTube Shorts 有 {len(new_comments)} 則新留言（{today}）", report)


if __name__ == "__main__":
    main()
