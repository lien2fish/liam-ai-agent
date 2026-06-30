#!/usr/bin/env python3
"""The Unknown Hour 頻道每日表現日報：近期影片觀看/讚/留言數 + 新留言，Email 通知。

用 YT_API_KEY 讀公開資料（不需 OAuth）。頻道以 handle 或 channel id 指定。
"""
import json, os, smtplib, urllib.request, urllib.parse, urllib.error
from datetime import datetime
from email.mime.text import MIMEText

API_KEY = os.environ["YT_API_KEY"]
HANDLE = os.environ.get("YT_REPORT_HANDLE", "UnknownHourCosmos")
CHANNEL_ID = os.environ.get("YT_REPORT_CHANNEL_ID", "")
GMAIL_USER = os.environ.get("GMAIL_USER", "lien2fish@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

API_BASE = "https://www.googleapis.com/youtube/v3"
ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(ROOT, "report_state.json")
REPORTS_DIR = os.path.join(os.path.dirname(ROOT), "reports")


def api_get(path, params):
    url = f"{API_BASE}/{path}?{urllib.parse.urlencode({**params, 'key': API_KEY})}"
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read())


def resolve_channel():
    if CHANNEL_ID:
        ch = api_get(
            "channels", {"part": "contentDetails,snippet,statistics", "id": CHANNEL_ID}
        )
    else:
        ch = api_get(
            "channels",
            {"part": "contentDetails,snippet,statistics", "forHandle": HANDLE},
        )
    it = ch["items"][0]
    return (
        it["id"],
        it["snippet"]["title"],
        it["contentDetails"]["relatedPlaylists"]["uploads"],
        it.get("statistics", {}),
    )


def recent_videos(uploads, n=15):
    try:
        items = api_get(
            "playlistItems",
            {"part": "contentDetails", "playlistId": uploads, "maxResults": n},
        )["items"]
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):  # 尚無公開影片
            return []
        raise
    ids = [i["contentDetails"]["videoId"] for i in items]
    if not ids:
        return []
    vids = api_get(
        "videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(ids)}
    )["items"]
    out = []
    for v in vids:
        st = v.get("statistics", {})
        out.append(
            {
                "id": v["id"],
                "title": v["snippet"]["title"],
                "published": v["snippet"]["publishedAt"][:10],
                "views": int(st.get("viewCount", 0)),
                "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)),
            }
        )
    return out


def get_comments(video_id):
    try:
        res = api_get(
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
        if e.code in (403, 404):
            return []
        raise
    return [
        {
            "id": it["id"],
            "author": it["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
            "text": it["snippet"]["topLevelComment"]["snippet"]["textDisplay"],
        }
        for it in res.get("items", [])
    ]


def load_state():
    if os.path.exists(STATE_PATH):
        try:
            return json.load(open(STATE_PATH))
        except Exception:
            return {}
    return {}


def save_state(state):
    json.dump(state, open(STATE_PATH, "w"), ensure_ascii=False, indent=2)


def send_email(subject, body):
    if not GMAIL_APP_PASSWORD:
        print("⚠️ 無 GMAIL_APP_PASSWORD，略過寄信", flush=True)
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        s.send_message(msg)


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    cid, name, uploads, ch_stats = resolve_channel()
    vids = recent_videos(uploads)

    state = load_state()
    seen = state.setdefault("seen_comment_ids", {})
    new_comments = []
    for v in vids:
        if v["comments"] == 0:
            continue
        seen_ids = set(seen.get(v["id"], []))
        for c in get_comments(v["id"]):
            if c["id"] not in seen_ids:
                new_comments.append((v["title"], v["id"], c))
                seen_ids.add(c["id"])
        seen[v["id"]] = list(seen_ids)
    save_state(state)

    subs = ch_stats.get("subscriberCount", "?")
    total_views = ch_stats.get("viewCount", "?")
    lines = [
        f"# 📺 {name} 頻道日報 {today}",
        "",
        f"> 訂閱數 **{subs}**｜頻道總觀看 **{total_views}**",
        "",
        "## 近期影片表現",
        "",
        "| 影片 | 發布 | 觀看 | 讚 | 留言 |",
        "|------|------|------|----|----|",
    ]
    for v in vids[:12]:
        t = v["title"][:38]
        lines.append(
            f"| {t} | {v['published']} | {v['views']:,} | {v['likes']:,} | {v['comments']:,} | https://youtu.be/{v['id']}"
        )
    lines += ["", f"## 💬 新留言（{len(new_comments)} 則）"]
    if new_comments:
        for title, vid, c in new_comments:
            lines.append(f"- **{c['author']}**（{title[:24]}）：{c['text']}")
            lines.append(f"  https://youtu.be/{vid}")
    else:
        lines.append("（今日無新留言）")
    report = "\n".join(lines)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    open(
        os.path.join(REPORTS_DIR, f"yt頻道日報_{today}.md"), "w", encoding="utf-8"
    ).write(report)
    print(report, flush=True)

    send_email(f"📺 {name} 頻道日報（{today}）｜新留言 {len(new_comments)}", report)


if __name__ == "__main__":
    main()
