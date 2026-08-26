#!/usr/bin/env python3
"""
更新 GitHub Actions Secret（SealedBox 加密），值不經過命令列也不回顯。

    python3 scripts/set_secret.py IG_TOKEN              # 隱藏輸入（要有終端機）
    python3 scripts/set_secret.py IG_TOKEN --file p.txt # 從檔案讀
    python3 scripts/set_secret.py --list                # 列出現有 secret 名稱與更新時間

PAT 從 ~/.git-credentials 取，不印出來。值永遠不會出現在輸出或 shell history 裡。

⚠️ 在 Claude Code 對話框裡跑隱藏輸入會失敗（沒有互動終端機），
   請改用 --file，或到 Terminal.app 跑。這跟 wrangler secret put 是同一種坑，
   差別是這支會明講失敗，不會假裝成功。
"""

import argparse
import base64
import getpass
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

REPO = "lien2fish/liam-ai-agent"


def die(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def pat():
    cred = pathlib.Path.home() / ".git-credentials"
    if not cred.exists():
        die("找不到 ~/.git-credentials")
    m = re.search(r"https://[^:]+:([^@]+)@github\.com", cred.read_text())
    if not m:
        die("~/.git-credentials 裡沒有 github.com 的憑證")
    return m.group(1)


def api(path, token, method="GET", body=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}",
        data=json.dumps(body).encode() if body else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?", help="Secret 名稱")
    ap.add_argument("--file", help="從檔案讀值（去掉前後空白與換行）")
    ap.add_argument("--list", action="store_true", help="列出現有 secret")
    args = ap.parse_args()

    token = pat()

    if args.list:
        st, d = api("actions/secrets?per_page=100", token)
        if st != 200:
            die(f"列出失敗（HTTP {st}）")
        print(f"共 {d['total_count']} 個：")
        for s in sorted(d["secrets"], key=lambda x: x["name"]):
            print(f"  {s['name']:24s} 更新於 {s['updated_at'][:10]}")
        return

    if not args.name:
        die("要給 Secret 名稱，或用 --list")

    if args.file:
        value = pathlib.Path(args.file).read_text().strip()
    else:
        if not sys.stdin.isatty():
            die("沒有互動終端機。改用 --file，或到 Terminal.app 跑。")
        value = getpass.getpass(f"{args.name} 的值（不會顯示）：").strip()

    if not value:
        die("值是空的——這正是 wrangler 那個坑，這裡直接擋下。")

    from nacl import encoding, public

    st, key = api("actions/secrets/public-key", token)
    if st != 200:
        die(f"取公鑰失敗（HTTP {st}）")

    box = public.SealedBox(
        public.PublicKey(key["key"].encode(), encoding.Base64Encoder)
    )
    enc = base64.b64encode(box.encrypt(value.encode())).decode()

    st, resp = api(
        f"actions/secrets/{args.name}",
        token,
        "PUT",
        {"encrypted_value": enc, "key_id": key["key_id"]},
    )
    if st not in (201, 204):
        die(f"更新失敗（HTTP {st}）：{resp}")

    st, info = api(f"actions/secrets/{args.name}", token)
    print(f"✅ {args.name} 已{'新建' if st == 201 else '更新'}（長度 {len(value)}）")
    if st == 200:
        print(f"   updated_at = {info.get('updated_at')}")


if __name__ == "__main__":
    main()
