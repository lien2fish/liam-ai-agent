"""旭和官網商品頁＋IG 草稿產生器。

資料：design/xuhe_products/<slug>.json，原圖：design/xuhe_products/src/<slug>.<jpg|png|heic>
輸出：design/xuhe_site/products.html、p/<slug>.html、img/<slug>.jpg（只含 status=published）
IG 草稿：design/xuhe_products/ig/<slug>/post.jpg＋caption.txt（不進版控）

  python3 tools/xuhe_product.py check <slug>     # 護欄檢查
  python3 tools/xuhe_product.py preview [slug]   # 含草稿，建到暫存目錄並用 Safari 開
  python3 tools/xuhe_product.py ig <slug>        # 產生 IG 草稿
  python3 tools/xuhe_product.py publish <slug>   # 改成 published 並重建官網
  python3 tools/xuhe_product.py build            # 只重建官網
"""

import html
import platform
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "design" / "xuhe_products"
SITE = ROOT / "design" / "xuhe_site"


def find_font():
    # 雲端（claude.ai/code、GitHub Actions）是 Linux，沒有 macOS 的字型路徑。
    if platform.system() == "Darwin":
        return "/System/Library/Fonts/STHeiti Medium.ttc", 0
    try:
        out = subprocess.run(
            ["fc-list", ":lang=zh", "--format=%{file}\n"], capture_output=True, text=True
        ).stdout
    except FileNotFoundError:
        out = ""
    noto = [l.strip() for l in out.splitlines() if "Noto" in l and "CJK" in l]
    if not noto:
        sys.exit(
            "❌ 找不到中文字型。Linux 請先安裝：sudo apt-get install -y fonts-noto-cjk"
        )
    return noto[0], (3 if noto[0].endswith(".ttc") else 0)

CATEGORIES = {"seafood": "海鮮", "wine": "葡萄酒", "tea": "台灣茶", "gift": "禮盒"}
WINE_WARNING = "禁止酒駕　未滿十八歲禁止飲酒"
PLACEHOLDER = "＿＿"

FORBIDDEN_ALL = [
    (r"NT\$|\$\s?\d|\d[\d,]*\s*元|售價|特價|優惠|折扣|限時", "不放價格與促銷用語"),
    (r"生食級|可生食", "「生食級」未確認法規依據前不准出現"),
    (r"自家漁船|自有漁船", "漁船是鉅鑫的資產，旭和不能寫「自家漁船」"),
    (r"\d+\s*艘", "不寫死合作漁船數量"),
    (r"老闆.{0,6}出海", "老闆本人不出海"),
]
FORBIDDEN_WINE = [
    (r"線上購買|下單|購物車|宅配|網購", "酒依法不得線上販售（菸酒管理法 §30）"),
]


def load(slug):
    path = DATA / f"{slug}.json"
    if not path.exists():
        sys.exit(f"❌ 找不到 {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def all_products():
    return sorted(
        (json.loads(p.read_text(encoding="utf-8")) for p in DATA.glob("*.json")),
        key=lambda d: (list(CATEGORIES).index(d["category"]), d["name"]),
    )


def source_image(slug):
    for ext in ("jpg", "jpeg", "png", "heic", "webp"):
        p = DATA / "src" / f"{slug}.{ext}"
        if p.exists():
            return p
    return None


def texts(d):
    parts = [
        d.get("name", ""),
        d.get("subtitle", ""),
        d.get("intro", ""),
        d.get("pairing", ""),
    ]
    parts += [f.get("title", "") + f.get("text", "") for f in d.get("features", [])]
    parts += [v for _, v in d.get("specs", [])]
    parts += [d.get("ig_caption", "")]
    return "\n".join(parts)


def check(d, for_publish=False):
    errors = []
    for key in ("slug", "category", "name", "intro", "features", "sources"):
        if not d.get(key):
            errors.append(f"缺少欄位 {key}")
    if d.get("category") not in CATEGORIES:
        errors.append(f"category 必須是 {list(CATEGORIES)}")
    for s in d.get("sources", []):
        if not str(s.get("url", "")).startswith("http"):
            errors.append(f"出處沒有網址：{s}")
    if not source_image(d.get("slug", "")):
        errors.append("找不到原圖 design/xuhe_products/src/<slug>.jpg")
    body = texts(d)
    rules = FORBIDDEN_ALL + (FORBIDDEN_WINE if d.get("category") == "wine" else [])
    for pattern, why in rules:
        m = re.search(pattern, body)
        if m:
            errors.append(f"「{m.group(0)}」→ {why}")
    if len(re.findall(r"#\S+", " ".join(d.get("hashtags", [])))) > 30:
        errors.append("IG hashtag 超過 30 個")
    if for_publish and PLACEHOLDER in body:
        errors.append(f"還有 {PLACEHOLDER} 沒填，不能上線")
    return errors


def save_web_image(slug, out_dir):
    src = source_image(slug)
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    img.thumbnail((1400, 1400))
    out_dir.mkdir(parents=True, exist_ok=True)
    img.save(out_dir / f"{slug}.jpg", quality=86, optimize=True)


def e(s):
    return html.escape(str(s))


def page(title, body, depth=0, desc=""):
    up = "../" * depth
    return f"""<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="icon" href="{up}mark.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@500;700;900&family=Noto+Sans+TC:wght@400;500;700&family=IBM+Plex+Mono:wght@400;600&display=swap">
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<nav class="nav">
  <div class="wrap">
    <a class="brand" href="{up}index.html"><img class="mark" src="{up}mark.svg" alt=""><b>旭和</b><small>XUHE CONSULTING</small></a>
    <ul>
      <li class="opt"><a href="{up}index.html#about">關於</a></li>
      <li><a href="{up}index.html#services">服務</a></li>
      <li><a href="{up}products.html" aria-current="page">商品</a></li>
      <li><a href="{up}index.html#contact">聯絡</a></li>
    </ul>
  </div>
</nav>
<main>
{body}
</main>
<footer>
  <div class="wrap">
    <p>© 2026 旭和管理顧問（籌備中）</p>
    <p class="legal">{WINE_WARNING}</p>
  </div>
</footer>
</body>
</html>
"""


def detail_html(d):
    draft = (
        '<p class="draft">草稿預覽・尚未上線</p>'
        if d.get("status") != "published"
        else ""
    )
    features = "".join(
        f'<div><h3>{e(f["title"])}</h3><p>{e(f["text"])}</p></div>'
        for f in d["features"]
    )
    specs = "".join(
        f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in d.get("specs", [])
    )
    pairing = (
        f'<div class="pd-block"><h2>適合的場合</h2><p>{e(d["pairing"])}</p></div>'
        if d.get("pairing")
        else ""
    )
    warning = f'<p class="warn">{WINE_WARNING}</p>' if d["category"] == "wine" else ""
    note = (
        "依法酒類恕不提供線上購買，請透過專人洽詢。"
        if d["category"] == "wine"
        else "品項與供應量依當期狀況而定，歡迎洽詢。"
    )
    sources = "".join(
        f'<li><a href="{e(s["url"])}" rel="noopener" target="_blank">{e(s.get("title") or s["url"])}</a></li>'
        for s in d["sources"]
    )
    body = f"""<article class="pd">
  <div class="wrap">
    {draft}
    <p class="eyebrow"><a href="../products.html">商品</a> · {CATEGORIES[d["category"]]}</p>
    <div class="pd-top">
      <img class="pd-img" src="../img/{e(d["slug"])}.jpg" alt="{e(d["name"])}">
      <div>
        <h1>{e(d["name"])}</h1>
        {f'<p class="pd-en">{e(d["name_en"])}</p>' if d.get("name_en") else ""}
        {f'<p class="pd-sub">{e(d["subtitle"])}</p>' if d.get("subtitle") else ""}
        <p class="pd-intro">{e(d["intro"])}</p>
        {f'<dl class="pd-specs">{specs}</dl>' if specs else ""}
        <a class="btn solid" href="../index.html#contact">洽詢這項商品</a>
        <p class="pd-note">{note}</p>
        {warning}
      </div>
    </div>
    <div class="pd-block"><h2>特色</h2><div class="pd-feat">{features}</div></div>
    {pairing}
    <div class="pd-block pd-src"><h2>資料來源</h2><ul>{sources}</ul></div>
  </div>
</article>"""
    return page(
        f'{d["name"]}｜旭和管理顧問',
        body,
        depth=1,
        desc=d.get("subtitle") or d["intro"][:80],
    )


def catalog_html(items):
    groups = []
    for cat, label in CATEGORIES.items():
        cards = "".join(
            f"""<a class="pc" href="p/{e(d["slug"])}.html">
  <img src="img/{e(d["slug"])}.jpg" alt="{e(d["name"])}" loading="lazy">
  <span class="pc-body"><b>{e(d["name"])}</b><span>{e(d.get("subtitle", ""))}</span>
  {'<em>草稿</em>' if d.get("status") != "published" else ""}</span>
</a>"""
            for d in items
            if d["category"] == cat
        )
        if cards:
            groups.append(
                f'<h2 class="pc-cat">{label}</h2><div class="pc-grid">{cards}</div>'
            )
    content = "".join(groups) or '<p class="pc-empty">商品陸續上架中。</p>'
    body = f"""<section class="pd">
  <div class="wrap">
    <div class="sec-head"><p class="eyebrow">Products</p><h1 class="pc-title">商品介紹</h1>
    <p>每一項商品的來歷、特色與適合的場合。供應狀況請直接洽詢。</p></div>
    {content}
  </div>
</section>"""
    return page("商品介紹｜旭和管理顧問", body, desc="旭和經手的海鮮、葡萄酒與台灣茶。")


def build(out, include_drafts):
    items = [
        d for d in all_products() if include_drafts or d.get("status") == "published"
    ]
    bad = {d["slug"]: check(d, for_publish=not include_drafts) for d in items}
    bad = {k: v for k, v in bad.items() if v}
    if bad:
        for slug, errs in bad.items():
            print(f"❌ {slug}")
            for x in errs:
                print(f"   - {x}")
        sys.exit(1)
    (out / "p").mkdir(parents=True, exist_ok=True)
    published = {f"{d['slug']}.html" for d in items}
    for old in (out / "p").glob("*.html"):
        if old.name not in published:
            old.unlink()
    for d in items:
        save_web_image(d["slug"], out / "img")
        (out / "p" / f'{d["slug"]}.html').write_text(detail_html(d), encoding="utf-8")
    (out / "products.html").write_text(catalog_html(items), encoding="utf-8")
    print(f"✅ 建置 {len(items)} 項商品 → {out}")


def preview(slug=None):
    if slug:
        errs = check(load(slug))
        if errs:
            print("⚠️ 護欄提醒（預覽照常產生）：")
            for x in errs:
                print(f"   - {x}")
    out = Path(tempfile.gettempdir()) / "xuhe_preview"
    subprocess.run(
        [
            "rsync",
            "-a",
            "--delete",
            "--exclude",
            "p/",
            "--exclude",
            "img/",
            f"{SITE}/",
            f"{out}/",
        ],
        check=True,
    )
    build(out, include_drafts=True)
    target = out / "p" / f"{slug}.html" if slug else out / "products.html"
    subprocess.run(["open", "-a", "Safari", str(target)])
    print(f"👀 預覽：{target}")


def wrap_lines(draw, text, font, width):
    lines, line = [], ""
    for token in re.findall(r"[A-Za-z0-9.'%\-]+|\s|.", text):
        if line and draw.textlength(line + token, font=font) > width:
            lines.append(line.rstrip())
            line = token.lstrip()
        else:
            line += token
    return lines + [line] if line else lines


def ig(slug):
    d = load(slug)
    errs = check(d)
    if errs:
        print("❌ 護欄沒過，不產生 IG 草稿：")
        for x in errs:
            print(f"   - {x}")
        sys.exit(1)
    W, H = 1080, 1350
    img = ImageOps.fit(
        ImageOps.exif_transpose(Image.open(source_image(slug))).convert("RGB"), (W, H)
    )
    draw = ImageDraw.Draw(img)
    font, idx = find_font()
    f_name = ImageFont.truetype(font, 58, index=idx)
    f_small = ImageFont.truetype(font, 30, index=idx)
    name_lines = wrap_lines(draw, d["name"], f_name, W - 120)[:2]
    is_wine = d["category"] == "wine"
    bar_h = 48 + 74 * len(name_lines) + 50 + (64 if is_wine else 0) + 40
    overlay = Image.new("RGBA", (W, bar_h), (22, 32, 42, 225))
    img.paste(overlay, (0, H - bar_h), overlay)
    y = H - bar_h + 48
    for line in name_lines:
        draw.text((60, y), line, font=f_name, fill=(246, 243, 236))
        y += 74
    draw.text((60, y + 6), "旭和管理顧問", font=f_small, fill=(224, 138, 92))
    if is_wine:
        draw.text((60, y + 70), WINE_WARNING, font=f_small, fill=(246, 243, 236))
    out = DATA / "ig" / slug
    out.mkdir(parents=True, exist_ok=True)
    img.save(out / "post.jpg", quality=90)
    caption = d.get("ig_caption", "").strip()
    if d["category"] == "wine":
        caption += f"\n\n{WINE_WARNING}"
    if d.get("hashtags"):
        caption += "\n\n" + " ".join(d["hashtags"])
    (out / "caption.txt").write_text(caption + "\n", encoding="utf-8")
    print(f"✅ IG 草稿 → {out}")
    if platform.system() == "Darwin":
        subprocess.run(["open", str(out / "post.jpg")])


def publish(slug):
    path = DATA / f"{slug}.json"
    d = load(slug)
    errs = check(d, for_publish=True)
    if errs:
        print("❌ 不能上線：")
        for x in errs:
            print(f"   - {x}")
        sys.exit(1)
    d["status"] = "published"
    path.write_text(
        json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    build(SITE, include_drafts=False)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, arg = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    if cmd == "check":
        errs = check(load(arg))
        print("✅ 護欄通過" if not errs else "\n".join(f"❌ {x}" for x in errs))
        sys.exit(1 if errs else 0)
    if cmd == "preview":
        return preview(arg)
    if cmd == "ig":
        return ig(arg)
    if cmd == "publish":
        return publish(arg)
    if cmd == "build":
        return build(SITE, include_drafts=False)
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
