#!/usr/bin/env python3
"""Instagram Business Login——拿觸及／播放數要走的那條路。

    python3 scripts/ig_insights_login.py          # 印授權網址
    python3 scripts/ig_insights_login.py --code   # 貼 code、換長效 token、驗收

為什麼不是沿用 config/instagram_config.json 那把 token：
發布與留言走 Facebook Login（graph.facebook.com），但這個 app 已經拿不到
Facebook Login 路徑的 instagram_manage_insights（Explorer 與 App Review 兩處都沒有）。
Instagram Login 是官方另一條路，權限叫 instagram_business_manage_insights，
host 是 graph.instagram.com。

⚠️ 兩把 token 各管各的，這支不會動到發布用的那把。
⚠️ 在 Terminal.app 跑——App Secret 與 code 都走隱藏輸入，不進對話框。
"""
import argparse
import getpass
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "config/instagram_insights.json"
SCOPES = "instagram_business_basic,instagram_business_manage_insights"
DEFAULT_REDIRECT = "https://gs-deck.pages.dev/"


def die(msg):
    print(f"\n❌ {msg}")
    sys.exit(1)


def post(url, data):
    try:
        with urllib.request.urlopen(
            url, urllib.parse.urlencode(data).encode(), timeout=30
        ) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        die(f"{url} 回 {e.code}：{e.read().decode()[:300]}")


def get(url, params):
    try:
        with urllib.request.urlopen(
            f"{url}?{urllib.parse.urlencode(params)}", timeout=30
        ) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        die(f"{url} 回 {e.code}：{e.read().decode()[:300]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", action="store_true", help="已經授權完，貼 code 換 token")
    ap.add_argument("--redirect", default=DEFAULT_REDIRECT)
    a = ap.parse_args()

    if not sys.stdin.isatty():
        die("沒有互動終端機。請在 Terminal.app 裡跑。")

    cfg = json.loads(OUT.read_text()) if OUT.exists() else {}
    app_id = (
        cfg.get("ig_app_id")
        or input("Instagram App ID（Dashboard 上那串數字）：").strip()
    )
    if not app_id.isdigit():
        die(
            "App ID 應該是一串數字。在 Instagram → API setup with Instagram login 的第 1 步。"
        )

    if not a.code:
        url = "https://www.instagram.com/oauth/authorize?" + urllib.parse.urlencode(
            {
                "client_id": app_id,
                "redirect_uri": a.redirect,
                "response_type": "code",
                "scope": SCOPES,
            }
        )
        print("\n先確認 Dashboard 的 OAuth redirect URI 完全等於這個（含結尾斜線）：")
        print(f"   {a.redirect}\n")
        print("再用 Safari 開這個網址授權（選 lienstable）：\n")
        print(url)
        print("\n授權後瀏覽器會跳到上面那個網址並帶 ?code=...")
        print("把 code= 後面那段複製起來（結尾的 #_ 不要），然後跑：")
        print("   python3 scripts/ig_insights_login.py --code")
        cfg["ig_app_id"] = app_id
        OUT.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
        return

    secret = getpass.getpass("Instagram App Secret（不會顯示）：").strip()
    code = getpass.getpass("授權 code（不會顯示）：").strip().rstrip("#_")
    if not secret or not code:
        die("App Secret 或 code 沒輸入。")

    print("\n→ 換短效 token…")
    short = post(
        "https://api.instagram.com/oauth/access_token",
        {
            "client_id": app_id,
            "client_secret": secret,
            "grant_type": "authorization_code",
            "redirect_uri": a.redirect,
            "code": code,
        },
    )
    user_id, tok = str(short.get("user_id", "")), short["access_token"]
    print(f"   ✅ IG user id {user_id}")

    print("→ 換 60 天長效 token…")
    long = get(
        "https://graph.instagram.com/access_token",
        {
            "grant_type": "ig_exchange_token",
            "client_secret": secret,
            "access_token": tok,
        },
    )
    tok = long["access_token"]
    expires = (
        datetime.now() + timedelta(seconds=int(long.get("expires_in", 0)))
    ).strftime("%Y-%m-%d")
    print(f"   ✅ 到期日 {expires}")

    print("→ 驗收：實際讀一則貼文的觸及數…")
    me = get(
        "https://graph.instagram.com/v21.0/me/media",
        {"fields": "id,caption", "limit": "1", "access_token": tok},
    )
    items = me.get("data", [])
    if not items:
        die("讀不到任何貼文——權限可能沒勾到 instagram_business_basic。")
    ins = get(
        f"https://graph.instagram.com/v21.0/{items[0]['id']}/insights",
        {"metric": "reach,views", "access_token": tok},
    )
    for d in ins.get("data", []):
        print(f"   ✅ {d['name']}：{d['values'][0]['value']:,}")

    cfg.update(
        {
            "ig_app_id": app_id,
            "ig_user_id": user_id,
            "access_token": tok,
            "token_expires": expires,
            "refreshed_date": datetime.now().strftime("%Y-%m-%d"),
        }
    )
    OUT.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    print(f"\n✅ 已存 {OUT}（config/ 在 .gitignore 內，不會進版控）")
    print("   長效 token 60 天到期，過期前重跑這支即可。")


if __name__ == "__main__":
    main()
