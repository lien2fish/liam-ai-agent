#!/usr/bin/env python3
"""一次性取得 YouTube 上傳用的 refresh token（沿用 Gmail 手動授權流程）。

前置：在 Google Cloud 建立 OAuth 用戶端（桌面型），把下載的 client secret JSON
放到 config/youtube_client.json。

用法：
  1) python3 youtube_auto/oauth_setup.py            → 印出授權 URL
  2) Safari 開啟、登入、允許 → 跳轉 localhost:8888/?code=XXX，複製 code
  3) python3 youtube_auto/oauth_setup.py "貼上code"  → 換取並存 refresh token

不同頻道用 --profile 分開存憑證（授權畫面務必選到對應頻道）：
  python3 youtube_auto/oauth_setup.py --profile lien
  python3 youtube_auto/oauth_setup.py --profile lien "貼上code"
"""
import json, os, sys, urllib.parse, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
CLIENT = os.path.join(REPO, "config", "youtube_client.json")
REDIRECT = "http://localhost:8888"
# readonly 是為了能回查上傳結果（頻道歸屬、影片設定）。
# 只有 upload 的話 videos.list／channels.list 一律 403，出錯只能靠人工到 Studio 看。
SCOPE = " ".join(
    [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]
)
# --write 才加：videos.update 改既有影片設定要它。含刪除權限，非必要不要給。
WRITE_SCOPE = SCOPE + " https://www.googleapis.com/auth/youtube.force-ssl"


def out_path(profile=None):
    name = f"youtube_oauth_{profile}.json" if profile else "youtube_oauth.json"
    return os.path.join(REPO, "config", name)


def _client():
    c = json.load(open(CLIENT))
    c = c.get("installed", c.get("web", c))
    return c["client_id"], c["client_secret"]


def auth_url(write=False):
    cid, _ = _client()
    q = urllib.parse.urlencode(
        {
            "client_id": cid,
            "redirect_uri": REDIRECT,
            "response_type": "code",
            "scope": WRITE_SCOPE if write else SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return "https://accounts.google.com/o/oauth2/v2/auth?" + q


def exchange(code, profile=None):
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
    out = out_path(profile)
    json.dump(
        {
            "client_id": cid,
            "client_secret": csec,
            "refresh_token": r["refresh_token"],
        },
        open(out, "w"),
        indent=2,
    )
    print(f"✅ refresh token 已存到 {out}")
    print("   下一步：把 client_id / client_secret / refresh_token 設成 GitHub Secrets")


if __name__ == "__main__":
    args = sys.argv[1:]
    profile = None
    if "--profile" in args:
        i = args.index("--profile")
        profile = args[i + 1]
        args = args[:i] + args[i + 2 :]
    write = "--write" in args
    if write:
        args.remove("--write")
    if args:
        exchange(args[0].strip(), profile)
    else:
        print(f"授權頻道：{profile or '預設 (The Unknown Hour)'}")
        print("⚠️ 授權畫面請務必選到對應的 YouTube 頻道")
        if write:
            print("⚠️ 這次含寫入權限（可改／可刪影片）\n")
        else:
            print()
        print("在 Safari 開啟以下網址授權：\n")
        print(auth_url(write))
