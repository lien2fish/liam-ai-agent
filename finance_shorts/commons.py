"""背景照片：從 Wikimedia Commons 找圖（免 key），只收不必同樣授權的版權條款。

Pexels、Pixabay 都申請不到 key（2026-10-20），改用 Commons。
只收公有領域／CC0／CC BY；BY-SA 會要求整支影片也用同樣授權，一律不收。
下載的圖放 shared/bg/，出處與授權記在 shared/bg/credits.json，上片時抄進說明欄。

用法：
  python3 finance_shorts/commons.py search 名稱 "搜尋字"     # 出候選縮圖拼貼，挑編號
  python3 finance_shorts/commons.py take 名稱 編號           # 下載那張到 shared/bg/名稱.jpg
"""

import html
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request

from build import ROOT

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "liam-finance-shorts/1 (lien2fish@gmail.com)"}
BG = ROOT / "shared" / "bg"
CAND = BG / "_candidates"
OK = re.compile(
    r"^(public domain|pd|cc0|cc by \d|cc-by-\d|cc by$|attribution$|copyrighted free use)",
    re.I,
)


def get(params):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    with urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=30
    ) as r:
        return json.load(r)


def plain(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def search(name, q, n=12):
    d = get(
        {
            "action": "query",
            "generator": "search",
            "gsrnamespace": 6,
            "gsrlimit": 50,
            "gsrsearch": f"{q} filetype:bitmap",
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata",
            "iiurlwidth": 480,
        }
    )
    keep = []
    for p in sorted(
        d.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0)
    ):
        ii = p["imageinfo"][0]
        m = ii.get("extmetadata", {})
        lic = plain(m.get("LicenseShortName", {}).get("value"))
        if not OK.match(lic) or "sa" in lic.lower().split():
            continue
        if ii["width"] < 1920 or ii["width"] < ii["height"] * 1.2:
            continue
        keep.append(
            {
                "title": p["title"],
                "page": ii["descriptionurl"],
                "license": lic,
                "license_url": plain(m.get("LicenseUrl", {}).get("value")),
                "artist": plain(m.get("Artist", {}).get("value"))
                or plain(m.get("Credit", {}).get("value")),
                "thumb": ii["thumburl"],
                "w": ii["width"],
                "h": ii["height"],
            }
        )
        if len(keep) == n:
            break
    CAND.mkdir(parents=True, exist_ok=True)
    for f in CAND.glob(f"{name}_*"):
        f.unlink()
    for i, c in enumerate(keep):
        raw = CAND / f"{name}_raw.jpg"
        fetch(c["thumb"], raw)
        # 統一成 480×270 再拼，尺寸不一 ffmpeg 會中途停；兩位數編號才不會 10 排在 2 前面
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-vf",
             f"scale=480:270:force_original_aspect_ratio=increase,crop=480:270,"
             f"drawtext=text='{i}':x=12:y=10:fontsize=44:fontcolor=yellow:box=1:boxcolor=black",
             str(CAND / f"{name}_{i:02d}.jpg")],
            check=True,
        )
        raw.unlink()
    (CAND / f"{name}.json").write_text(json.dumps(keep, ensure_ascii=False, indent=1))
    if keep:
        # ffmpeg tile 拼出來會漏掉前幾張（10-20 實測），改用 Pillow 拼
        from PIL import Image

        sheet = Image.new("RGB", (480 * 4, 270 * 3))
        for i in range(len(keep)):
            sheet.paste(Image.open(CAND / f"{name}_{i:02d}.jpg"), (480 * (i % 4), 270 * (i // 4)))
        sheet.save(CAND / f"{name}_sheet.png")
    for i, c in enumerate(keep):
        print(f"  {i}. {c['license']:<14} {c['w']}×{c['h']}  {c['title'][5:70]}")
    print(f"  → {CAND / f'{name}_sheet.png'}")


def fetch(url, out):
    with urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=60
    ) as r:
        out.write_bytes(r.read())


def take(name, idx):
    c = json.loads((CAND / f"{name}.json").read_text())[int(idx)]
    d = get(
        {
            "action": "query",
            "titles": c["title"],
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 2560,
        }
    )
    ii = next(iter(d["query"]["pages"].values()))["imageinfo"][0]
    fetch(ii.get("thumburl") or ii["url"], BG / f"{name}.jpg")
    credits_path = BG / "credits.json"
    credits = json.loads(credits_path.read_text()) if credits_path.exists() else {}
    credits[name] = {
        k: c[k] for k in ("title", "page", "license", "license_url", "artist")
    }
    credits_path.write_text(json.dumps(credits, ensure_ascii=False, indent=1))
    print(f"  ✅ {name}.jpg  {c['license']}  {c['artist'][:60]}")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    {"search": search, "take": take}[cmd](*args)
