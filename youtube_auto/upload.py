#!/usr/bin/env python3
"""用 OAuth refresh token 上傳影片到 YouTube（Data API v3 resumable upload）。

憑證來源：環境變數 YT_OAUTH_CLIENT_ID / YT_OAUTH_CLIENT_SECRET / YT_OAUTH_REFRESH_TOKEN
（本機 fallback：config/youtube_oauth.json）。只用 urllib，不加 google client 依賴。
"""
import json, os, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)


def _creds():
    e = os.environ
    if e.get("YT_OAUTH_REFRESH_TOKEN"):
        return (
            e["YT_OAUTH_CLIENT_ID"],
            e["YT_OAUTH_CLIENT_SECRET"],
            e["YT_OAUTH_REFRESH_TOKEN"],
        )
    cfg = os.path.join(REPO, "config", "youtube_oauth.json")
    c = json.load(open(cfg))
    return c["client_id"], c["client_secret"], c["refresh_token"]


def access_token():
    cid, csec, refresh = _creds()
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


def upload(video_path, title, description, tags, privacy="private", category="27"):
    """回傳 video_id。privacy: private/unlisted/public。category 27=教育, 24=娛樂"""
    token = access_token()
    meta = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": category,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
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
    print(f"✅ 已上傳：https://youtu.be/{vid}（{privacy}）", flush=True)
    return vid


if __name__ == "__main__":
    import sys

    p = sys.argv[1]
    upload(p, "Test upload", "test", ["test"], privacy="private")
