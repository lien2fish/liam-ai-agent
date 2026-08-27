#!/usr/bin/env python3
"""
更新 GitHub Actions Secret（SealedBox 加密），值不經過命令列也不回顯。

    python3 scripts/set_secret.py IG_TOKEN              # 隱藏輸入（要有終端機）
    python3 scripts/set_secret.py IG_TOKEN --file p.txt # 從檔案讀
    python3 scripts/set_secret.py --list                # 列出現有 secret 名稱與更新時間

PAT 從 git credential helper（keychain）取，不印出來。值永遠不會出現在輸出或 shell history 裡。

⚠️ 在 Claude Code 對話框裡跑隱藏輸入會失敗（沒有互動終端機），
   請改用 --file，或到 Terminal.app 跑。這跟 wrangler secret put 是同一種坑，
   差別是這支會明講失敗，不會假裝成功。
"""

import argparse
import base64
import getpass
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "lien2fish/liam-ai-agent"


def die(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def pat():
    """從 git credential helper（keychain）取 PAT。值不落地、不回顯。"""
    out = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    ).stdout
    m = re.search(r"^password=(.+)$", out, re.M)
    if not m:
        die("git credential 取不到 github.com 憑證——keychain 是否已解鎖？")
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
    ap.add_argument(
        "--local",
        help="同時寫入本機檔案（例如 config/.anthropic_key）。"
        "GitHub Secret 唯寫讀不回來，本機與雲端一旦不同步就救不回，所以一次寫兩邊。",
    )
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
    print(f"✅ {args.name} 已更新到 GitHub（長度 {len(value)}）")
    if st == 200:
        print(f"   updated_at = {info.get('updated_at')}")

    if args.local:
        lp = pathlib.Path(args.local)
        if lp.exists():
            bak = lp.with_name(lp.name + ".bak")
            bak.write_text(lp.read_text())
            print(f"   舊的本機檔已備份到 {bak}")
        lp.write_text(value)
        lp.chmod(0o600)
        print(f"✅ 同一個值也寫進本機 {lp}")


if __name__ == "__main__":
    main()
