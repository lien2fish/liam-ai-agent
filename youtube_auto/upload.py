#!/usr/bin/env python3
"""用 OAuth refresh token 上傳影片到 YouTube（Data API v3 resumable upload）。

憑證來源：環境變數 YT_OAUTH_CLIENT_ID / YT_OAUTH_CLIENT_SECRET / YT_OAUTH_REFRESH_TOKEN
（本機 fallback：config/youtube_oauth.json）。只用 urllib，不加 google client 依賴。
"""
import json, os, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)


def _creds(profile=None):
    """profile=None＝預設頻道（The Unknown Hour）。
    給 profile（如 "lien"）則改讀 YT_LIEN_OAUTH_* 環境變數／config/youtube_oauth_lien.json，
    讓同一支上傳邏輯能服務不同頻道。"""
    e = os.environ
    prefix = f"YT_{profile.upper()}_OAUTH_" if profile else "YT_OAUTH_"
    if e.get(prefix + "REFRESH_TOKEN"):
        return (
            e[prefix + "CLIENT_ID"],
            e[prefix + "CLIENT_SECRET"],
            e[prefix + "REFRESH_TOKEN"],
        )
    name = f"youtube_oauth_{profile}.json" if profile else "youtube_oauth.json"
    cfg = os.path.join(REPO, "config", name)
    c = json.load(open(cfg))
    return c["client_id"], c["client_secret"], c["refresh_token"]


def access_token(profile=None):
    cid, csec, refresh = _creds(profile)
    data = urllib.parse.urlencode(
        {
            "client_id": cid,
            "client_secret": csec,
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=data, method="POST"
    )
    return json.load(urllib.request.urlopen(req))["access_token"]


def upload(
    video_path,
    title,
    description,
    tags,
    privacy="private",
    category="27",
    publish_at=None,
    synthetic_media=False,
    profile=None,
):
    """回傳 video_id。privacy: private/unlisted/public。
    publish_at（RFC3339 UTC，如 2026-06-29T10:00:00Z）有給時＝排程發布：
    先設 private，YouTube 屆時自動轉公開。category 27=教育, 24=娛樂
    synthetic_media=True＝揭露為 AI 生成/變造內容（等同 Studio 的「變造或合成內容」勾選）
    profile＝憑證組（None＝The Unknown Hour；"lien"＝連老闆-產地到餐桌）"""
    token = access_token(profile)
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    if synthetic_media:
        status["containsSyntheticMedia"] = True
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    meta = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": category,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": status,
    }
    size = os.path.getsize(video_path)

    # 1) 起始 resumable session，取得上傳 URL
    init = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=json.dumps(meta).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/*",
            "X-Upload-Content-Length": str(size),
        },
        method="POST",
    )
    with urllib.request.urlopen(init) as r:
        upload_url = r.headers["Location"]

    # 2) 上傳影片內容
    with open(video_path, "rb") as f:
        body = f.read()
    put = urllib.request.Request(
        upload_url,
        data=body,
        headers={"Content-Type": "video/*", "Content-Length": str(size)},
        method="PUT",
    )
    resp = json.load(urllib.request.urlopen(put))
    vid = resp["id"]
    when = f"排程 {publish_at} 自動公開" if publish_at else privacy
    ai = "，已揭露 AI 生成" if synthetic_media else ""
    print(f"✅ 已上傳：https://youtu.be/{vid}（{when}{ai}）", flush=True)
    return vid


def set_thumbnail(video_id, image_path, profile=None):
    """設定自訂縮圖（需頻道已完成驗證；scope youtube.upload 即可）"""
    token = access_token(profile)
    data = open(image_path, "rb").read()
    req = urllib.request.Request(
        f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "image/png"},
        method="POST",
    )
    urllib.request.urlopen(req)
    print("✅ 已設定自訂縮圖", flush=True)


if __name__ == "__main__":
    import sys

    p = sys.argv[1]
    upload(p, "Test upload", "test", ["test"], privacy="private")
