#!/usr/bin/env python3
"""
IG／FB Token 重新授權——在 Terminal.app 跑，token 不經過任何對話框。

    python3 scripts/ig_reauth.py

短效 token 用隱藏輸入貼進來（不回顯、不進 shell history、不留暫存檔），
之後換長效、驗到期日、寫回 config、更新 GitHub Secret、實際打一次 API 驗收，
全部一次做完。過程中不會印出任何金鑰的值。

⚠️ 不要在 Claude Code 的對話框裡跑——那裡沒有互動終端機，getpass 讀不到東西。
"""

import base64
import getpass
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config/instagram_config.json"
GRAPH = "https://graph.facebook.com/v19.0"
REPO = "lien2fish/liam-ai-agent"

REQUIRED_SCOPES = [
    "instagram_basic",
    "instagram_content_publish",
    "instagram_manage_comments",
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
]

# 只影響數據分析（觸及／播放／儲存／分享），發布與留言都用不到。
# 刻意不列進 REQUIRED——IG token 到期時三個發布系統會一起掛，
# 不能讓「報表權限勾不到」擋住 token 更新本身。
OPTIONAL_SCOPES = ["instagram_manage_insights"]


def die(msg):
    print(f"\n❌ {msg}")
    sys.exit(1)


def graph(path, params):
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read().decode()).get("error", {})
        sub = f" / subcode {err['error_subcode']}" if err.get("error_subcode") else ""
        die(f"Graph API 失敗（code {err.get('code')}{sub}）：{err.get('message', '')}")


def when(ts):
    if not ts:
        return "永不過期"
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def github_secret(name, value, pat):
    def api(path, method="GET", body=None):
        req = urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/{path}",
            data=json.dumps(body).encode() if body else None,
            headers={
                "Authorization": f"Bearer {pat}",
                "Accept": "application/vnd.github+json",
            },
            method=method,
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})

    from nacl import encoding, public

    _, key = api("actions/secrets/public-key")
    box = public.SealedBox(
        public.PublicKey(key["key"].encode(), encoding.Base64Encoder)
    )
    enc = base64.b64encode(box.encrypt(value.encode())).decode()
    st, _ = api(
        f"actions/secrets/{name}",
        "PUT",
        {"encrypted_value": enc, "key_id": key["key_id"]},
    )
    if st not in (201, 204):
        die(f"更新 GitHub Secret {name} 失敗（HTTP {st}）")
    print(f"   ✅ GitHub Secret {name} 已更新")


def main():
    if not sys.stdin.isatty():
        die("沒有互動終端機。請在 Terminal.app 裡跑，不要在 Claude Code 對話框跑。")

    cfg = json.loads(CONFIG.read_text())
    explorer = f"https://developers.facebook.com/tools/explorer/{cfg['app_id']}/"

    print("=" * 60)
    print("IG／FB Token 重新授權")
    print("=" * 60)
    print(f"\n1. 開這個網址：\n   {explorer}\n")
    print(f"2. Permissions 勾滿這 {len(REQUIRED_SCOPES)} 項：")
    for sc in REQUIRED_SCOPES:
        print(f"   - {sc}")
    print("   再加這項（讀觸及／播放數用，勾不到也能繼續）：")
    for sc in OPTIONAL_SCOPES:
        print(f"   - {sc}")
    print("\n3. Generate Access Token → 走完授權對話框")
    print("   ⚠️ 若它直接跳過沒問權限，點「編輯先前的設定」逐項確認都開著。")
    print("   ⚠️ session 被作廢（190/460）時，只有真的走完對話框才救得回來。\n")

    if input("要現在幫你開瀏覽器嗎？[Y/n] ").strip().lower() in ("", "y"):
        subprocess.run(["open", "-a", "Safari", explorer])

    short = getpass.getpass("\n把短效 token 貼上（不會顯示，貼完按 Enter）：").strip()
    if not short:
        die("沒有輸入 token。")

    print("\n→ 換長效 token…")
    res = graph(
        "oauth/access_token",
        {
            "grant_type": "fb_exchange_token",
            "client_id": cfg["app_id"],
            "client_secret": cfg["app_secret"],
            "fb_exchange_token": short,
        },
    )
    long_tok = res["access_token"]

    print("→ 驗證…")
    d = graph("debug_token", {"input_token": long_tok, "access_token": long_tok})[
        "data"
    ]
    if not d.get("is_valid"):
        die("換出來的 token 被判定為 invalid。")

    granted = d.get("scopes", [])
    missing = [s for s in REQUIRED_SCOPES if s not in granted]
    if missing:
        die(
            "缺少權限："
            + "、".join(missing)
            + f"\n   回 Explorer 勾齊 {len(REQUIRED_SCOPES)} 項再跑一次。"
        )
    missing_opt = [s for s in OPTIONAL_SCOPES if s not in granted]

    old_dae = cfg.get("data_access_expires", "（無紀錄）")
    new_dae = when(d.get("data_access_expires_at"))
    new_exp = when(d.get("expires_at"))
    print(f"   必要權限 {len(REQUIRED_SCOPES)} 項齊全")
    if missing_opt:
        print("   ⚠️ 沒拿到：" + "、".join(missing_opt) + "（觸及／播放數會讀不到）")
    print(f"   expires_at            ：{new_exp}")
    print(f"   data_access_expires_at：{old_dae} → {new_dae}")

    # 驗收條件就是這個日期有往後推。沒推代表沒真的走完授權對話框。
    if new_dae == old_dae:
        print("\n⚠️ data_access_expires_at 沒有往後推——通常代表沒真的走完授權對話框，")
        print("   而是沿用了舊授權。fb_exchange_token 換發不會重置這個日期。")
        if input("   仍要繼續寫入嗎？[y/N] ").strip().lower() != "y":
            die("已中止，沒有動到任何設定。")

    print("\n→ 實際打一次 API…")
    media = graph(
        f"{cfg['ig_account_id']}/media",
        {"fields": "id", "limit": "1", "access_token": long_tok},
    )
    print(f"   ✅ 讀得到貼文（{len(media.get('data', []))} 篇）")

    if not missing_opt and media.get("data"):
        # 這只是加分項，讀不到也不能中止——token 還沒寫回，die 掉等於整次授權白做
        print("\n→ 驗 insights 真的讀得到…")
        try:
            url = (
                f"{GRAPH}/{media['data'][0]['id']}/insights?"
                + urllib.parse.urlencode({"metric": "reach", "access_token": long_tok})
            )
            with urllib.request.urlopen(url, timeout=30) as r:
                vals = json.loads(r.read()).get("data", [])
            print(f"   ✅ 觸及數讀得到（{vals[0]['values'][0]['value']:,} 次觸及）")
        except Exception as e:
            print(f"   ⚠️ 讀不到觸及數（{e}）——權限有拿到，但 API 這關沒過")

    print("\n→ 重簽 FB Page token…")
    page = graph(
        cfg["page_id"], {"fields": "id,name,access_token", "access_token": long_tok}
    )
    page_tok = page.get("access_token")
    print(f"   ✅ {page.get('name')}" if page_tok else "   ⚠️ 沒拿到 Page token，跳過")

    print("\n→ 寫回 config…")
    backup = CONFIG.with_name(
        CONFIG.name + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M")
    )
    shutil.copy2(CONFIG, backup)
    cfg["long_lived_user_token"] = long_tok
    cfg["token_refreshed_date"] = datetime.now().strftime("%Y-%m-%d")
    cfg["data_access_expires"] = new_dae
    cfg["token_expires"] = new_exp
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    print(f"   ✅ 已寫回，備份：{backup.name}")

    print("\n→ 更新 GitHub Secrets…")
    cred_out = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    ).stdout
    m = re.search(r"^password=(.+)$", cred_out, re.M)
    if not m:
        print("   ⚠️ git credential 取不到 GitHub PAT，Secrets 請自行更新")
    else:
        github_secret("IG_TOKEN", long_tok, m.group(1))
        if page_tok:
            github_secret("FB_PAGE_TOKEN", page_tok, m.group(1))

    print("\n" + "=" * 60)
    print("完成。下一步：跑一次 Token 到期提醒確認全綠——")
    print("  gh workflow run token_expiry_check.yml   （或到 Actions 手動觸發）")
    print("=" * 60)


if __name__ == "__main__":
    main()
