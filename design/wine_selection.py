"""聚食釜 六支精選酒款 — 客戶介紹 PDF（一酒一頁）＋餐桌酒單（單張 A4），不放價格。

    python3 design/wine_selection.py            # 兩份都產
    python3 design/wine_selection.py intro      # 只產客戶介紹
    python3 design/wine_selection.py menu       # 只產餐桌酒單

輸出：~/Desktop/聚食釜_精選酒款/（同名檔案先搬進 _備份/ 再覆蓋）
"""

import html
import os
import shutil
import sys
from datetime import datetime

import fitz
from playwright.sync_api import sync_playwright

OUT_DIR = os.path.expanduser("~/Desktop/聚食釜_精選酒款")
CHROMIUM = os.path.expanduser(
    "~/Library/Caches/ms-playwright/chromium_headless_shell-1243/"
    "chrome-headless-shell-mac-arm64/chrome-headless-shell"
)

BRAND = "聚食釜"
TAGLINE = "台式頂級蝦湯鍋物"
LEGAL = "禁止酒駕　飲酒過量，有害健康　未滿十八歲禁止飲酒"

GOLD = "#B7874A"
INK = "#2D1B0E"
PAPER = "#FBF8F1"
RULE = "#E4D8C2"
MUTED = "#7A6A58"

SERIF_ZH = '"Songti TC", "Songti SC", serif'
SERIF_EN = '"Baskerville", "Didot", serif'
SANS_ZH = '"PingFang TC", "Source Han Sans TC", sans-serif'

WINES = [
    {
        "style": "白酒",
        "name_en": "Riesling Red Label '20",
        "name_zh": "紅標 麗絲玲白酒 2020",
        "winery": "Selbach-Oster 賽爾巴哈奧斯特酒廠",
        "region": "Mosel, Germany",
        "grapes": "100% Riesling",
        "abv": "10%",
        "volume": "750ml",
        "tasting": "這款Riesling展現出純正且鮮明的品種特徵：成熟卻奔放的核果香氣、清脆的青蘋果風味，以及高度融合的礦物感。口感飽滿而不失平衡，並帶有唯有摩澤爾產區才能孕育出的標誌性「汽油」礦物氣息。風味微甜，果味比例拿捏得恰到好處。",
        "pairing": "是款可搭配各式各樣前菜及鹹點的開胃酒。適合夏日清爽的沙拉以及烤蔬菜。和亞洲料理也非常地恰當，除此之外也可以單獨飲用，單純的享受此款Riesling的美好。",
        "tips": "來自摩澤爾（Mosel）多個地塊的葡萄，全程於不鏽鋼槽中發酵與熟成。陳年實力達5-6年。",
        "menu_note": "核果與青蘋果香，礦物感鮮明，微甜清爽",
        "menu_pair": "前菜・沙拉・亞洲料理",
    },
    {
        "style": "白酒",
        "name_en": "Marlborough Sauvignon Blanc '24",
        "name_zh": "馬博羅蘇維濃白酒 2024",
        "winery": "Kim Crawford 金卡佛酒廠",
        "region": "Marlborough, New Zealand",
        "grapes": "Sauvignon Blanc",
        "abv": "13.5%",
        "volume": "750ml",
        "tasting": "這款酒呈現帶柔和綠色的淡金黃稻草色澤，輕輕搖晃杯子就能夠感受到撲鼻而來熱帶水果與明亮柑橘的香氣，在口中縈繞不去。中段風味鮮活奔放，熱帶水果甜感與持久的礦物氣息交織，營造出層次分明且優雅悠長的風味表現。",
        "pairing": "適合搭配風味清新的生菜沙拉、簡單調味的煎或烤白肉魚、酸辣而鮮味明顯的泰式料理，像是綠咖哩或西式青醬等為醬汁的美食。",
        "tips": "葡萄來自Marlborough各個葡萄園地塊，該地屬海洋性氣候，白天溫暖、夜晚涼爽，陽光充足且偶有不同方向的風帶來變化。在釀造過程中，每個區域的葡萄都個別處理，以保留每個塊地所賦予的不同特色。葡萄採收並去梗後即被輕柔破皮與壓榨，經三小時浸皮後進行分槽發酵，以釋放鮮明的酸度與百香果、粉紅葡萄柚風味。各批次完成後再進行調配，以呈現Kim Crawford招牌風格——芳香馥郁、風味濃郁集中。",
        "menu_note": "熱帶水果與明亮柑橘香，礦物氣息悠長",
        "menu_pair": "生菜沙拉・煎烤白肉魚・泰式料理",
    },
    {
        "style": "白酒",
        "name_en": "Rosso & Bianco Chardonnay '24",
        "name_zh": "R&B 夏多內白酒 2024",
        "winery": "Francis Ford Coppola Winery 教父酒莊",
        "region": "California, USA",
        "grapes": "Chardonnay, Pinot Grigio, Other",
        "abv": "13.5%",
        "volume": "750ml",
        "tasting": "這款酒呈現明亮的稻草黃色澤，是一款展現了現摘鮮果般輕盈、爽脆特質的白酒。散發出迷人的香氣，融合杏桃、鳳梨與磨刀石的礦石感；入口後，橘子、西洋梨、蜜桃、檸檬的果香風味交織，帶來豐富口感。",
        "pairing": "適合搭配各式海鮮、白肉料理或是搭配台式熱炒也非常好。",
        "tips": "葡萄根據風味成熟度與酸度表現來決定採收時機，全程在100%不鏽鋼槽中發酵，而非橡木桶進行發酵，以完整保留品種的芳香，呈現出最自然純淨與明亮的風格。",
        "menu_note": "杏桃、鳳梨與礦石感，輕盈爽脆",
        "menu_pair": "海鮮・白肉・台式熱炒",
    },
    {
        "style": "紅酒",
        "name_en": "Diamond Pinot Noir '22",
        "name_zh": "鑽石 黑皮諾紅酒 2022",
        "winery": "Francis Ford Coppola Winery 教父酒莊",
        "region": "California, USA",
        "grapes": "92% Pinot Noir, 5.1% Syrah, 2.6% Grenache, 0.5% Other Red",
        "abv": "14.5%",
        "volume": "750ml",
        "tasting": "散發著覆盆子、黑莓、醋栗等的果香，並點綴著香草、烘烤橡木的氣息。口感新鮮活潑多汁甜美，柔滑順口，是一款適合任何場合的美味酒款。",
        "pairing": "適合與紅酒燉肉、甚至是烤雞一同享用，都能夠品嘗餐酒搭配的美妙風味。",
        "tips": "葡萄進行冷浸後在不鏽鋼槽中發酵，經 100% 蘋果乳酸發酵，最後放入法國和美國橡木桶中陳釀。",
        "menu_note": "覆盆子與黑莓果香，點綴香草與烘烤橡木，柔滑順口",
        "menu_pair": "紅酒燉肉・烤雞",
    },
    {
        "style": "紅酒",
        "name_en": "Beaune 1er Cru Clos du Roi '22",
        "name_zh": "伯恩一級園 國王園紅酒 2022",
        "winery": "Domaine Chanson",
        "region": "Côte de Beaune, Burgundy, France",
        "grapes": "100% Pinot Noir",
        "abv": "14%",
        "volume": "750ml",
        "tasting": "這款酒酒體呈美麗的寶石紅色。擁有濃郁的花香，搭配成熟小果實（如紅醋栗）及香料的氣息。酒體結構優美，平衡且複雜。質地豐富且精緻，伴隨著絲滑的單寧。香氣持久，帶有香料的餘韻。",
        "pairing": "適合搭配櫻桃鴨胸、雉雞、野鵪鶉。",
        "tips": "「Clos du Roi」位於「Les Marconnets」地塊下方。原本屬於布根地公爵的產地，在查理曼大帝去世後被路易十一國王兼併。Chanson 擁有 2.4 公頃的葡萄園，占整個地塊的 35%，其中 2/3 的地塊種植了黑皮諾（Pinot Noir）葡萄。2022 年的葡萄收成量非常豐富，並且品質上乘，葡萄酒表現出很好的平衡感，精確而清新。",
        "menu_note": "濃郁花香與紅醋栗、香料氣息，單寧絲滑、結構優雅",
        "menu_pair": "櫻桃鴨胸・雉雞・野鵪鶉",
    },
    {
        "style": "紅酒",
        "name_en": "Rosso & Bianco Cabernet Sauvignon '23",
        "name_zh": "R&B 卡本內蘇維濃紅酒 2023",
        "winery": "Francis Ford Coppola Winery 教父酒莊",
        "region": "California, USA",
        "grapes": "Cabernet Sauvignon, Petite Verdot, Malbec, Other",
        "abv": "13.5%",
        "volume": "750ml",
        "tasting": "這款酒散發出迷人的香氣，黑胡椒粒與黑莓的溫暖芬芳，伴隨著燻烤氣息，與黑醋栗、丁香和大地風味交織在一起；入口後帶來了果香與辛香料的濃郁結合，活潑且平衡的酸度與柔順的單寧將這些元素和諧地揉合，成就了一款卓越且令人難忘的卡本內蘇維濃。",
        "pairing": "適合搭配各式烤肉、濃郁燉菜以及奶油義大利麵等料理，是一款口感親切、適合日常飲用的佳釀。",
        "tips": "Rosso & Bianco系列不僅向柯波拉家族的義大利傳承致敬，更是酒莊最早創立的系列之一。秉持著【為日常生活而生的葡萄酒】精神，酒莊在釀造過程中的用心，成就了其無與倫比的品質與極高性價比，為此酒款展現了最純粹的品種特性。部分酒液於法國與美國橡木桶中熟成至少4個月。",
        "menu_note": "黑莓、黑胡椒與燻烤氣息，酸度活潑、單寧柔順",
        "menu_pair": "烤肉・濃郁燉菜・奶油義大利麵",
    },
]

BASE_CSS = f"""
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: {PAPER}; color: {INK}; font-family: {SANS_ZH};
       -webkit-print-color-adjust: exact; }}
.page {{ width: 210mm; height: 297mm; position: relative; overflow: hidden;
        padding: 22mm 22mm 20mm; page-break-after: always; background: {PAPER}; }}
.page:last-child {{ page-break-after: auto; }}
.frame {{ position: absolute; inset: 9mm; border: 0.5pt solid {RULE}; pointer-events: none; }}
.brand {{ font-family: {SERIF_ZH}; font-size: 11pt; letter-spacing: 0.5em; color: {GOLD}; }}
.foot {{ position: absolute; left: 22mm; right: 22mm; bottom: 15mm; display: flex;
        justify-content: space-between; font-size: 7.5pt; color: {MUTED}; letter-spacing: 0.08em; }}
.gold-rule {{ width: 18mm; height: 0.8pt; background: {GOLD}; }}
"""


def esc(s):
    return html.escape(s)


def footer():
    return (
        f'<div class="foot"><span>{BRAND}・{TAGLINE}</span><span>{LEGAL}</span></div>'
    )


def intro_html():
    css = (
        BASE_CSS
        + f"""
.cover {{ display: flex; flex-direction: column; }}
.cover .title-zh {{ font-family: {SERIF_ZH}; font-size: 30pt; letter-spacing: 0.35em; margin: 34mm 0 4mm; }}
.cover .title-en {{ font-family: {SERIF_EN}; font-style: italic; font-size: 15pt; color: {MUTED}; letter-spacing: 0.06em; }}
.cover .gold-rule {{ margin: 12mm 0 14mm; }}
.list {{ width: 100%; border-collapse: collapse; }}
.list td {{ padding: 4.2mm 0; border-bottom: 0.5pt solid {RULE}; vertical-align: top; }}
.list tr:first-child td {{ border-top: 0.5pt solid {RULE}; }}
.list .no {{ width: 12mm; font-family: {SERIF_EN}; color: {GOLD}; font-size: 11pt; }}
.list .en {{ font-family: {SERIF_EN}; font-size: 11.5pt; }}
.list .zh {{ font-family: {SERIF_ZH}; font-size: 10pt; color: {MUTED}; margin-top: 1mm; }}
.list .meta {{ text-align: right; font-size: 8.5pt; color: {MUTED}; line-height: 1.7; white-space: nowrap; }}
.wine .top {{ display: flex; justify-content: space-between; align-items: baseline; }}
.wine .idx {{ font-family: {SERIF_EN}; font-size: 10pt; color: {GOLD}; letter-spacing: 0.15em; }}
.wine .name-en {{ font-family: {SERIF_EN}; font-size: 22pt; line-height: 1.2; margin: 16mm 0 3mm; }}
.wine .name-zh {{ font-family: {SERIF_ZH}; font-size: 15pt; letter-spacing: 0.12em; }}
.wine .winery {{ font-size: 9.5pt; color: {MUTED}; margin-top: 3mm; letter-spacing: 0.05em; }}
.wine .gold-rule {{ margin: 9mm 0 8mm; }}
.facts {{ display: grid; grid-template-columns: 1.35fr 1.65fr 0.6fr 0.6fr; gap: 0 6mm;
         padding: 5mm 0; border-top: 0.5pt solid {RULE}; border-bottom: 0.5pt solid {RULE}; margin-bottom: 9mm; }}
.facts dt {{ font-size: 7.5pt; color: {GOLD}; letter-spacing: 0.2em; margin-bottom: 1.5mm; }}
.facts dd {{ font-family: {SERIF_EN}; font-size: 9.5pt; line-height: 1.45; }}
.sec {{ margin-bottom: 7.5mm; }}
.sec h3 {{ font-family: {SERIF_ZH}; font-size: 11pt; font-weight: 600; letter-spacing: 0.3em; color: {GOLD}; margin-bottom: 2.5mm; }}
.sec p {{ font-size: 10pt; line-height: 1.95; text-align: justify; letter-spacing: 0.02em; }}
"""
    )
    rows = "".join(
        f'<tr><td class="no">{i:02d}</td>'
        f'<td><div class="en">{esc(w["name_en"])}</div><div class="zh">{esc(w["name_zh"])}</div></td>'
        f'<td class="meta">{w["style"]}<br>{esc(w["region"])}</td></tr>'
        for i, w in enumerate(WINES, 1)
    )
    cover = (
        f'<section class="page cover"><div class="frame"></div>'
        f'<div class="brand">{BRAND}</div>'
        f'<div class="title-zh">精選酒款</div>'
        f'<div class="title-en">Selected Wines</div>'
        f'<div class="gold-rule"></div>'
        f'<table class="list">{rows}</table>{footer()}</section>'
    )
    pages = [cover]
    for i, w in enumerate(WINES, 1):
        pages.append(
            f'<section class="page wine"><div class="frame"></div>'
            f'<div class="top"><div class="brand">{BRAND}</div>'
            f'<div class="idx">{i:02d} / {len(WINES):02d}　{w["style"]}</div></div>'
            f'<div class="name-en">{esc(w["name_en"])}</div>'
            f'<div class="name-zh">{esc(w["name_zh"])}</div>'
            f'<div class="winery">{esc(w["winery"])}</div>'
            f'<div class="gold-rule"></div>'
            f'<dl class="facts">'
            f'<div><dt>產區</dt><dd>{esc(w["region"])}</dd></div>'
            f'<div><dt>葡萄品種</dt><dd>{esc(w["grapes"])}</dd></div>'
            f'<div><dt>酒精濃度</dt><dd>{w["abv"]}</dd></div>'
            f'<div><dt>容量</dt><dd>{w["volume"]}</dd></div></dl>'
            f'<div class="sec"><h3>酒質</h3><p>{esc(w["tasting"])}</p></div>'
            f'<div class="sec"><h3>餐酒搭配</h3><p>{esc(w["pairing"])}</p></div>'
            f'<div class="sec"><h3>釀造與風土</h3><p>{esc(w["tips"])}</p></div>'
            f"{footer()}</section>"
        )
    return (
        f"<html><head><style>{css}</style></head><body>{''.join(pages)}</body></html>"
    )


def menu_html():
    css = (
        BASE_CSS
        + f"""
.head {{ text-align: center; margin: 4mm 0 9mm; }}
.head .title {{ font-family: {SERIF_EN}; font-size: 26pt; letter-spacing: 0.22em; margin-top: 7mm; }}
.head .sub {{ font-family: {SERIF_ZH}; font-size: 11pt; letter-spacing: 0.6em; color: {MUTED}; margin-top: 2mm; }}
.head .gold-rule {{ margin: 7mm auto 0; }}
.group {{ margin-top: 7mm; }}
.group h2 {{ display: flex; align-items: center; gap: 4mm; font-family: {SERIF_ZH}; font-weight: 600;
            font-size: 12pt; letter-spacing: 0.5em; color: {GOLD}; margin-bottom: 2mm; }}
.group h2 small {{ font-family: {SERIF_EN}; font-style: italic; font-weight: 400; font-size: 10pt; letter-spacing: 0.1em; }}
.group h2::after {{ content: ""; flex: 1; height: 0.5pt; background: {RULE}; }}
.item {{ padding: 4.3mm 0; border-bottom: 0.5pt dotted {RULE}; }}
.item:last-child {{ border-bottom: none; }}
.item .l1 {{ display: flex; justify-content: space-between; align-items: baseline; gap: 6mm; }}
.item .en {{ font-family: {SERIF_EN}; font-size: 12.5pt; }}
.item .zh {{ font-family: {SERIF_ZH}; font-size: 10.5pt; white-space: nowrap; }}
.item .l2 {{ font-size: 8.3pt; color: {MUTED}; margin-top: 1.2mm; letter-spacing: 0.03em; }}
.item .l3 {{ font-size: 9pt; margin-top: 1.6mm; line-height: 1.6; }}
.item .l3 span {{ color: {GOLD}; margin: 0 1.5mm 0 4mm; }}
"""
    )

    def group(style, en):
        items = "".join(
            f'<div class="item"><div class="l1"><div class="en">{esc(w["name_en"])}</div>'
            f'<div class="zh">{esc(w["name_zh"])}</div></div>'
            f'<div class="l2">{esc(w["winery"])}・{esc(w["region"])}</div>'
            f'<div class="l3">{esc(w["menu_note"])}<span>搭配</span>{esc(w["menu_pair"])}</div></div>'
            for w in WINES
            if w["style"] == style
        )
        return f'<div class="group"><h2>{style}<small>{en}</small></h2>{items}</div>'

    body = (
        f'<section class="page"><div class="frame"></div>'
        f'<div class="head"><div class="brand">{BRAND}</div>'
        f'<div class="title">WINE LIST</div><div class="sub">酒　單</div>'
        f'<div class="gold-rule"></div></div>'
        f'{group("白酒", "White")}{group("紅酒", "Red")}{footer()}</section>'
    )
    return f"<html><head><style>{css}</style></head><body>{body}</body></html>"


def backup(path):
    if not os.path.exists(path):
        return None
    bdir = os.path.join(OUT_DIR, "_備份")
    os.makedirs(bdir, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(path))
    dest = os.path.join(bdir, f"{stem}_{datetime.now():%Y%m%d_%H%M%S}{ext}")
    shutil.move(path, dest)
    return dest


def render(browser, doc, name):
    pdf = os.path.join(OUT_DIR, f"{name}.pdf")
    moved = backup(pdf)
    page = browser.new_page()
    page.set_content(doc, wait_until="load")
    page.pdf(path=pdf, format="A4", print_background=True, prefer_css_page_size=True)
    page.close()
    with fitz.open(pdf) as d:
        for i, p in enumerate(d, 1):
            p.get_pixmap(dpi=110).save(
                os.path.join(OUT_DIR, "_預覽", f"{name}_p{i}.png")
            )
        print(
            f"✅ {pdf}（{d.page_count} 頁）" + (f"　舊檔備份→{moved}" if moved else "")
        )


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(os.path.join(OUT_DIR, "_預覽"), exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM)
        if which in ("all", "intro"):
            render(browser, intro_html(), "聚食釜_精選酒款介紹")
        if which in ("all", "menu"):
            render(browser, menu_html(), "聚食釜_餐桌酒單")
        browser.close()


if __name__ == "__main__":
    main()
