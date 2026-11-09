#!/usr/bin/env python3
"""
創業紀錄 IG（@firstbefore40）授權——走「Instagram 登入」，不需要 FB 粉絲專頁。在 Terminal.app 跑：

    python3 scripts/ig2_auth.py

把 Meta 開發者後台「產生權杖」拿到的 token 用隱藏輸入貼進來（不回顯、不進 shell history），
驗證是 @firstbefore40 之後，寫進 config/ig_firstbefore40.json 與 GitHub Secret IG2_TOKEN／IG2_ID。
過程中不印出 token。之後由 token_expiry_check 每天自動續期（60 天期限）。

⚠️ 跟連老闆的 IG_TOKEN 完全分開，改 FB 密碼不會影響這把。
"""

import base64
import getpass
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from set_secret import api, pat  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config/ig_firstbefore40.json"
GRAPH = "https://graph.instagram.com/v23.0"
USERNAME = "firstbefore40"


def die(msg):
    print(f"\n❌ {msg}")
    sys.exit(1)


def ig(path, params):
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        die(f"IG API 拒絕（HTTP {e.code}）：{e.read().decode()[:300]}")


def put_secret(gh, name, value):
    from nacl import encoding, public

    st, key = api("actions/secrets/public-key", gh)
    if st != 200:
        die(f"取 GitHub 公鑰失敗（HTTP {st}）")
    box = public.SealedBox(
        public.PublicKey(key["key"].encode(), encoding.Base64Encoder)
    )
    enc = base64.b64encode(box.encrypt(value.encode())).decode()
    st, resp = api(
        f"actions/secrets/{name}",
        gh,
        "PUT",
        {"encrypted_value": enc, "key_id": key["key_id"]},
    )
    if st not in (201, 204):
        die(f"寫入 {name} 失敗（HTTP {st}）：{resp}")
    print(f"✅ GitHub Secret {name} 已更新")


def main():
    if not sys.stdin.isatty():
        die("沒有互動終端機——請到 Terminal.app 跑，不要在 Claude Code 對話框裡跑。")
    tok = getpass.getpass("貼上 @firstbefore40 的 token（不會顯示）：").strip()
    if not tok:
        die("沒有輸入")

    me = ig("me", {"fields": "user_id,username,account_type", "access_token": tok})
    if me.get("username") != USERNAME:
        die(f"這把 token 是 @{me.get('username')}，不是 @{USERNAME}，沒有寫入任何東西")
    uid = me["user_id"]
    print(f"✅ 帳號 @{me['username']}（{me.get('account_type')}），ID {uid}")
    lim = ig(
        f"{uid}/content_publishing_limit",
        {"fields": "quota_usage,config", "access_token": tok},
    )
    print(f"✅ 發布權限可用（今日已用 {lim['data'][0].get('quota_usage', 0)} 則）")

    if CONFIG.exists():
        bak = CONFIG.with_name(CONFIG.name + ".bak")
        bak.write_text(CONFIG.read_text())
        bak.chmod(0o600)
    CONFIG.write_text(json.dumps({
        "username": USERNAME, "user_id": uid, "token": tok,
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2))  # fmt: skip
    CONFIG.chmod(0o600)
    print(f"✅ 已寫入 {CONFIG.relative_to(ROOT)}")

    gh = pat()
    put_secret(gh, "IG2_TOKEN", tok)
    put_secret(gh, "IG2_ID", str(uid))
    print("\n完成。回到 Claude Code 說一聲就好。")


main()
