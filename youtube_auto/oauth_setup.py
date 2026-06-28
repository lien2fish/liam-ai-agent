#!/usr/bin/env python3
"""一次性取得 YouTube 上傳用的 refresh token（沿用 Gmail 手動授權流程）。

前置：在 Google Cloud 建立 OAuth 用戶端（桌面型），把下載的 client secret JSON
放到 config/youtube_client.json。

用法：
  1) python3 youtube_auto/oauth_setup.py            → 印出授權 URL
  2) Safari 開啟、登入、允許 → 跳轉 localhost:8888/?code=XXX，複製 code
  3) python3 youtube_auto/oauth_setup.py "貼上code"  → 換取並存 refresh token
"""
import json, os, sys, urllib.parse, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
CLIENT = os.path.join(REPO, "config", "youtube_client.json")
OUT = os.path.join(REPO, "config", "youtube_oauth.json")
REDIRECT = "http://localhost:8888"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def _client():
    c = json.load(open(CLIENT))
    c = c.get("installed", c.get("web", c))
    return c["client_id"], c["client_secret"]


def auth_url():
    cid, _ = _client()
    q = urllib.parse.urlencode(
        {
            "client_id": cid,
            "redirect_uri": REDIRECT,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return "https://accounts.google.com/o/oauth2/v2/auth?" + q


def exchange(code):
    cid, csec = _client()
    data = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": cid,
            "client_secret": csec,
            "redirect_uri": REDIRECT,
            "grant_type": "authorization_code",
        }
    ).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=data, method="POST"
    )
    r = json.load(urllib.request.urlopen(req))
    if "refresh_token" not in r:
        raise RuntimeError(f"未取得 refresh_token（請確認 prompt=consent）：{r}")
    json.dump(
        {
            "client_id": cid,
            "client_secret": csec,
            "refresh_token": r["refresh_token"],
        },
        open(OUT, "w"),
        indent=2,
    )
    print(f"✅ refresh token 已存到 {OUT}")
    print("   下一步：把 client_id / client_secret / refresh_token 設成 GitHub Secrets")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        exchange(sys.argv[1].strip())
    else:
        print("在 Safari 開啟以下網址授權：\n")
        print(auth_url())
