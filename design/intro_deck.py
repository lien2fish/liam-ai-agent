#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""個人與公司介紹「凝鉅情感，真鑫相待」的 16:9 投影片版。

內容與 design/intro/index.html（gs-intro.pages.dev）同一份，這支負責
可投影／可列印／可寄的離線版本。素材共用 design/intro/assets/。

⚠️ 事實界線見 memory feedback-seafood-facts：公司有自家漁船，但 Lien 本人不上船出海。
⚠️ 中文標籤不能用 Courier（沒有中文字符），MONO 只給數字用。
⚠️ Songti.ttc index 0 是 SC 缺繁體字，用 index 2（粗）／3（細）。
⚠️ 只在 macOS 跑，不進 GitHub Actions。

用法：python3 design/intro_deck.py [輸出.pdf]
"""
import os
import sys

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

W, H = 960, 540
M = 62

PAPER = HexColor("#F6F4EF")
CARD = HexColor("#FFFDF9")
CARD2 = HexColor("#EDE9E1")
INK = HexColor("#1A1D24")
INK2 = HexColor("#4E5560")
INK3 = HexColor("#87909C")
RULE = HexColor("#DDD7CC")
NAVY = HexColor("#16233D")
RED = HexColor("#C8302F")
GOLD = HexColor("#B07E1E")

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "intro", "assets")
SONGTI = "/System/Library/Fonts/Supplemental/Songti.ttc"
NOTO = os.path.join(BASE, "..", "scripts", "fonts", "NotoSansTC.ttf")

pdfmetrics.registerFont(TTFont("SerifB", SONGTI, subfontIndex=2))
pdfmetrics.registerFont(TTFont("Sans", NOTO))
MONO = "Courier"
MONO_B = "Courier-Bold"


def wrap(text, font, size, maxw):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if pdfmetrics.stringWidth(cur + ch, font, size) > maxw and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def img(path):
    return os.path.join(ASSETS, path)


class Deck:
    def __init__(self, path):
        self.c = canvas.Canvas(path, pagesize=(W, H))
        self.c.setTitle("凝鉅情感，真鑫相待｜鉅鑫管理顧問")
        self.c.setAuthor("鉅鑫管理顧問有限公司")
        self.n = 0

    def page(self, bg=PAPER):
        self.c.setFillColor(bg)
        self.c.rect(0, 0, W, H, stroke=0, fill=1)
        self.n += 1

    def foot(self, label=""):
        if self.n <= 1:
            return
        c = self.c
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        c.line(M, 40, W - M, 40)
        c.setFillColor(INK3)
        c.setFont("Sans", 7.5)
        c.drawString(M, 26, "鉅鑫管理顧問　凝鉅情感、真鑫相待")
        if label:
            c.drawCentredString(W / 2, 26, label)
        c.setFont(MONO, 7.5)
        c.drawRightString(W - M, 26, "%02d" % (self.n - 1))

    def mark(self, text, y=H - M - 10):
        c = self.c
        c.setFillColor(RED)
        c.rect(M, y + 4, 26, 3, stroke=0, fill=1)
        c.setFillColor(INK3)
        c.setFont("Sans", 8.5)
        c.drawString(M + 38, y, " ".join(text))

    def title(self, text, y, size=32, color=INK, font="Sans"):
        self.c.setFillColor(color)
        self.c.setFont(font, size)
        lines = wrap(text, font, size, W - 2 * M)
        for i, ln in enumerate(lines):
            self.c.drawString(M, y - i * size * 1.32, ln)
        return y - len(lines) * size * 1.32

    def para(self, text, y, size=11.5, color=INK2, maxw=None, x=M, lead=1.85):
        maxw = maxw or (W - 2 * M)
        self.c.setFillColor(color)
        self.c.setFont("Sans", size)
        lines = wrap(text, "Sans", size, maxw)
        for i, ln in enumerate(lines):
            self.c.drawString(x, y - i * size * lead, ln)
        return y - len(lines) * size * lead


# ---------------------------------------------------------------- slides


def cover(d):
    d.page(NAVY)
    c = d.c
    c.drawImage(img("cover_flat.jpg"), M, H - 236, width=300, height=157, mask="auto")

    c.setFillColor(HexColor("#FBF8F2"))
    c.setFont("SerifB", 54)
    c.drawString(M, H - 320, "凝鉅情感")
    c.setFillColor(HexColor("#E6A93C"))
    c.drawString(M, H - 386, "真鑫相待")

    c.setFillColor(HexColor("#FBF8F2"))
    c.setFont("Sans", 15)
    c.drawString(M + 430, H - 320, "連傳正")
    c.setFillColor(HexColor("#B9C2D2"))
    c.setFont("Sans", 11.5)
    c.drawString(M + 430, H - 340, "鉅鑫管理顧問有限公司")
    for i, ln in enumerate(
        wrap(
            "從金融保險起家，走到漁港、餐桌與茶席。做的事看起來很散，"
            "但底下是同一件——把好東西，誠實地交到需要的人手上。",
            "Sans",
            11.5,
            380,
        )
    ):
        c.drawString(M + 430, H - 368 - i * 20, ln)

    c.setStrokeColor(HexColor("#3A465E"))
    c.setLineWidth(0.6)
    c.line(M, 108, W - M, 108)
    x = M
    for k, v in [
        ("創立", "2009"),
        ("擴大營運", "2018"),
        ("領域", "6"),
        ("自有品牌", "5"),
    ]:
        c.setFillColor(HexColor("#8994A8"))
        c.setFont("Sans", 9)
        c.drawString(x, 86, k)
        x += pdfmetrics.stringWidth(k, "Sans", 9) + 8
        c.setFillColor(HexColor("#E6A93C"))
        c.setFont(MONO_B, 10)
        c.drawString(x, 86, v)
        x += pdfmetrics.stringWidth(v, MONO_B, 10) + 44


def me(d):
    d.page()
    d.mark("ABOUT ME")
    y = d.title("先講我這個人", H - 140, 32)
    y = d.para(
        "我是連傳正。做保險出身，現在同時管五個品牌、跑漁港、接待客人，"
        "也在協會與社團裡做事。",
        y - 26,
        size=14,
        maxw=700,
    )
    y = d.para(
        "會走到今天這樣，是因為我不太能忍受「說得好聽但東西不到位」。"
        "賣酒就得自己喝過、賣魚就得自己去漁港看，客戶問我這條魚幾月最肥，我答得出來"
        "——這是我唯一的門檻，也是我全部的本事。",
        y - 24,
        maxw=700,
    )
    d.para(
        "所以鉅鑫的東西不做低價競爭。品項少、挑得兇，但每一樣我都敢自己端上桌。",
        y - 22,
        maxw=700,
    )
    d.foot("關於我")


def era(d):
    d.page()
    d.mark("THE COMPANY")
    d.title("鉅鑫是怎麼長成現在這樣的", H - 140, 32)
    d.para(
        "不是先畫好藍圖再照著做，是一路上把客戶真正需要的東西一件一件補進來。",
        H - 178,
        size=13,
        maxw=740,
    )

    c = d.c
    items = [
        (
            "2009",
            "從金融保險起家",
            "以誠信為起點。人生每個階段的規劃，是最早也最久的本業。",
        ),
        (
            "2018",
            "擴大規模，成立公司",
            "為了更緊密地連結客戶與朋友，把各項服務做大做精，鉅鑫管理顧問有限公司正式登記。",
        ),
        (
            "今天",
            "六大領域、五個自有品牌",
            "從金融保險延伸到貿易、餐飲、不動產、進口代理與教育，並自營五個消費品牌。",
        ),
    ]
    cw = (W - 2 * M - 20) / 3
    top, ch = H - 218, 168
    for i, (yr, head, body) in enumerate(items):
        x = M + i * (cw + 10)
        c.setFillColor(CARD)
        c.rect(x, top - ch, cw, ch, stroke=0, fill=1)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.rect(x, top - ch, cw, ch, stroke=1, fill=0)
        c.setFillColor(RED)
        c.setFont(MONO_B, 22) if yr.isdigit() else c.setFont("Sans", 20)
        c.drawString(x + 20, top - 40, yr)
        c.setFillColor(INK)
        c.setFont("Sans", 14)
        c.drawString(x + 20, top - 70, head)
        c.setFillColor(INK2)
        c.setFont("Sans", 10)
        for j, ln in enumerate(wrap(body, "Sans", 10, cw - 40)):
            c.drawString(x + 20, top - 94 - j * 16, ln)
    d.foot("沿革")


def fields(d):
    d.page()
    d.mark("SIX FIELDS")
    d.title("六大領域平台", H - 140, 32)
    d.para(
        "彼此不是各做各的——客戶在其中一個領域認識我們，通常會用到第二個。",
        H - 178,
        size=13,
        maxw=740,
    )

    data = [
        ("01", "金融保險", "國際專業顧問認證，人生各階段的完整規劃。"),
        ("02", "外銷貿易", "農產與漁產外銷，打造國際市場銷售通道。"),
        (
            "03",
            "餐飲創投",
            "結合龜吼觀光、兩岸四地餐飲運營經驗，與調茶師、侍酒師的專業觀點。",
        ),
        ("04", "不動產銷售", "以誠信為本，物件資源豐富，精準匹配買賣雙方。"),
        ("05", "進口代理", "羽球用品、葡萄酒等商品代理，為國內市場引進高品質商品。"),
        ("06", "教育系統", "國際 NLP 師資，因材施教；並舉辦營隊與企業實習。"),
    ]
    c = d.c
    cw = (W - 2 * M - 20) / 3
    gh = 100
    for i, (n, head, body) in enumerate(data):
        x = M + (i % 3) * (cw + 10)
        y = H - 226 - (i // 3) * (gh + 10)
        c.setFillColor(CARD)
        c.rect(x, y - gh, cw, gh, stroke=0, fill=1)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.rect(x, y - gh, cw, gh, stroke=1, fill=0)
        c.setFillColor(GOLD)
        c.setFont(MONO, 9)
        c.drawString(x + 18, y - 24, n)
        c.setFillColor(INK)
        c.setFont("Sans", 13)
        c.drawString(x + 18, y - 46, head)
        c.setFillColor(INK2)
        c.setFont("Sans", 9.5)
        for j, ln in enumerate(wrap(body, "Sans", 9.5, cw - 36)):
            c.drawString(x + 18, y - 66 - j * 14, ln)
    d.foot("六大領域")


def brands(d):
    d.page()
    d.mark("OWN BRANDS")
    d.title("五個自己做的品牌", H - 140, 32)
    d.para("共同的規則只有一條：自己不會端上桌的，不賣。", H - 178, size=13, maxw=740)

    rows = [
        (
            "鑫海產",
            "SEAFOOD",
            "龜吼漁港當日現撈，自家漁船撈捕、上岸真空急凍。做 VIP 現流直送、通路批發，也與龜吼在地餐廳聯名。",
        ),
        (
            "鑫酒藏",
            "WINE",
            "把品酒變成日常、藏酒當成興趣。依酒款個性配奧地利杯型，讓每一口珍釀發揮原有的性格。",
        ),
        (
            "鑫茶坊",
            "TEA",
            "以南投鹿谷青心烏龍為主的台灣精品茶。目標是把台灣茶的滋味送上米其林的桌。",
        ),
        (
            "匠鑫聚",
            "原「匠鑫私廚」",
            "內湖預約制私廚與接待會所。現流海鮮、精品茶與世界酒款，配專業侍酒師與可客製的菜單，可包場。",
        ),
        ("龜吼現流活海產", "2026 建置中", "把產地直接搬到餐桌前的下一步。目前籌備中。"),
    ]
    c = d.c
    top, rh = H - 202, 46
    for i, (name, en, body) in enumerate(rows):
        y = top - i * (rh + 5)
        c.setFillColor(CARD)
        c.rect(M, y - rh, W - 2 * M, rh, stroke=0, fill=1)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        c.rect(M, y - rh, W - 2 * M, rh, stroke=1, fill=0)
        c.setFillColor(INK)
        c.setFont("Sans", 13)
        c.drawString(M + 18, y - 22, name)
        c.setFillColor(INK3)
        c.setFont("Sans", 8)
        c.drawString(M + 18, y - 38, en)
        c.setFillColor(INK2)
        c.setFont("Sans", 10)
        for j, ln in enumerate(wrap(body, "Sans", 10, W - 2 * M - 210)):
            c.drawString(M + 190, y - 22 - j * 15, ln)
    d.para(
        "另有磊山保經的壽險與產險業務，是最早的本業，也持續在做。",
        top - 5 * (rh + 5) - 20,
        size=9.5,
        color=INK3,
    )
    d.foot("自有品牌")


def origin(d):
    d.page()
    c = d.c
    iw = (W - 4) / 3.0
    ih = 200
    for i, (f, cap) in enumerate(
        [
            ("port.jpg", "新北市龜吼漁港"),
            ("catch.jpg", "當日清晨上岸的漁獲"),
            ("market.jpg", "魚市現場"),
        ]
    ):
        x = i * (iw + 2)
        c.drawImage(
            img(f),
            x,
            H - ih,
            width=iw,
            height=ih,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
        c.setFillColor(HexColor("#0A0E16"))
        c.rect(x, H - ih, iw, 24, stroke=0, fill=1)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Sans", 9)
        c.drawString(x + 12, H - ih + 8, cap)

    d.mark("WHERE IT STARTS", H - ih - 40)
    y = d.title("一切從龜吼開始", H - ih - 80, 28)
    y = d.para(
        "在龜吼有自家漁船，另與當地共捕漁船長期合作。"
        "這是鑫海產能講「現流」兩個字的底氣。",
        y - 20,
        size=12.5,
        maxw=800,
    )
    d.para(
        "凌晨的船靠岸、天亮前分魚，好的那一批不會流到市場上——那是熟客的。"
        "真空急凍在上岸那一刻就做完，鮮甜被封在裡面。"
        "船是自己的，加上跟共捕船的長期關係，才有這個順位。",
        y - 20,
        size=11,
        maxw=800,
    )
    d.foot("產地")


def house(d):
    d.page()
    d.mark("THE HOUSE")
    d.title("內湖接待會所：匠鑫聚", H - 140, 30)
    d.para(
        "和公司同一個地址。談生意、宴客、辦品酒會，都在這裡——把人請到自己的場子，話才好講。",
        H - 176,
        size=12,
        maxw=820,
    )

    c = d.c
    iw, ih = 200, 268           # 對齊 venue_space.jpg 的 896x1200 直式比例
    iy = 92
    c.drawImage(
        img("venue_space.jpg"),
        M,
        iy,
        width=iw,
        height=ih,
        preserveAspectRatio=True,
        anchor="c",
        mask="auto",
    )
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.rect(M, iy, iw, ih, stroke=1, fill=0)

    sx = M + iw + 26
    sw = W - M - sx
    specs = [
        ("座位上限", "中式圓桌 30 人（10／14／16 人桌）"),
        ("包場時段", "午 11:30–14:30　晚 18:30–21:30"),
        ("非包場", "私房菜 4–8 人，家庭餐宴或同事聚餐"),
        ("設備加購", "100 吋投影布幕／投影機／麥克風／音響"),
    ]
    yy = iy + ih - 6
    for k, v in specs:
        c.setFillColor(INK3)
        c.setFont("Sans", 8.5)
        c.drawString(sx, yy, " ".join(k))
        c.setFillColor(INK)
        c.setFont("Sans", 12)
        c.drawString(sx, yy - 20, v)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.4)
        c.line(sx, yy - 34, W - M, yy - 34)
        yy -= 58

    c.setFillColor(INK2)
    c.setFont("Sans", 10)
    c.drawString(
        sx, iy + 6, "預約制。每月 20 日開放次月包場預訂。訂位 (02) 2658-5290。"
    )
    d.foot("接待會所")


def guests(d):
    d.page()
    d.mark("WHO CAME")
    d.title("來過這裡的人", H - 140, 30)

    c = d.c
    iw = 186
    ih = int(iw * 2245 / 1587.0)
    iy = H - 190 - ih
    c.drawImage(img("venue_moueix.jpg"), M, iy, width=iw, height=ih, mask="auto")
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.rect(M, iy, iw, ih, stroke=1, fill=0)
    c.setFillColor(INK3)
    c.setFont("Sans", 8.5)
    c.drawString(M, iy - 14, "工商時報｜Christian Moueix 賢伉儷親臨")

    tx = M + iw + 34
    tw = W - M - tx
    items = [
        ("2026 RIEDEL 認證餐廳", "葡萄酒服務的識別標章，全台認證名單之一。"),
        ("Christian Moueix 賢伉儷親臨", "Pétrus 與 Dominus 背後的傳奇人物。"),
        (
            "Tim Mondavi 來訪",
            "Robert Mondavi 之子、Continuum 創辦人。我們以台灣小吃、台式手路菜與當日直送海味款待，珍珠奶茶壓軸。",
        ),
        ("台灣第一位香檳大師萊特", "合作品酒會、品杯會與微醺餐宴多場。"),
        ("工商時報報導", "「內湖隱世私廚」。"),
        ("星坊酒業總經理須弘道推薦", "龜吼直送的現流海鮮私廚料理。"),
    ]
    y = H - 190
    for head, body in items:
        c.setFillColor(GOLD)
        c.circle(tx + 3, y + 4, 3, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("Sans", 11.5)
        c.drawString(tx + 14, y, head)
        c.setFillColor(INK2)
        c.setFont("Sans", 9.5)
        lines = wrap(body, "Sans", 9.5, tw - 14)
        for j, ln in enumerate(lines):
            c.drawString(tx + 14, y - 16 - j * 14, ln)
        y -= 24 + len(lines) * 14

    c.setStrokeColor(RED)
    c.setLineWidth(2.5)
    c.line(tx, y + 6, tx, y - 26)
    c.setFillColor(INK2)
    c.setFont("Sans", 10.5)
    c.drawString(tx + 14, y - 6, "「超好吃😋 食材新鮮美味，服務超級棒！」")
    c.setFillColor(INK3)
    c.setFont("Sans", 8.5)
    c.drawString(tx + 14, y - 24, "— Yun Chen，Google 評論")
    d.foot("接待會所")


def giving(d):
    d.page()
    d.mark("GIVING BACK")
    d.title("公益不是附加，是本來就在做的事", H - 140, 30)
    d.para(
        "「無私」是鉅鑫四大核心理念之一。這些是實際參與過的：",
        H - 176,
        size=12.5,
        maxw=740,
    )

    causes = [
        "2026 國際扶輪世界年會",
        "惜食廚房",
        "2025 德國 IDBF 龍舟世界錦標賽",
        "根除小兒麻痺慈善音樂會",
        "撿回珍珠計畫",
        "自行車環島公益扶助計畫",
        "反毒路跑",
        "基隆 1919 陪讀計畫",
        "陳爸的書屋創辦人紀念音樂會",
        "匠鑫私廚公益書法募款餐會",
        "2017 台北世大運志工",
        "中壢國中羽球隊贊助",
    ]
    c = d.c
    cw = (W - 2 * M) / 3.0
    for i, name in enumerate(causes):
        x = M + (i % 3) * cw
        y = H - 230 - (i // 3) * 40
        c.setFillColor(RED)
        c.rect(x, y + 3, 5, 5, stroke=0, fill=1)
        c.setFillColor(INK2)
        c.setFont("Sans", 11.5)
        c.drawString(x + 16, y, name)
    d.foot("公益")


def partners(d):
    d.page()
    d.mark("PARTNERS")
    d.title("一起做事的夥伴", H - 140, 30)
    d.para("鉅鑫以資源整合為核心。這些是長期合作的對象：", H - 176, size=12.5, maxw=740)

    c = d.c
    key = [
        ("星坊酒業", "葡萄酒代理。總經理須弘道推薦匠鑫龜吼直送的現流海鮮。"),
        ("磊山保經", "壽險與產險。鉅鑫最早的本業，至今仍在做。"),
        (
            "我們在海邊",
            "三芝北海岸海景咖啡廳，後厝漁港旁，預約制。曾為投資標的，現為合作夥伴。",
        ),
    ]
    cw = (W - 2 * M - 20) / 3
    top, ch = H - 218, 118
    for i, (name, body) in enumerate(key):
        x = M + i * (cw + 10)
        c.setFillColor(CARD)
        c.rect(x, top - ch, cw, ch, stroke=0, fill=1)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.rect(x, top - ch, cw, ch, stroke=1, fill=0)
        c.setFillColor(INK)
        c.setFont("Sans", 13)
        c.drawString(x + 18, top - 32, name)
        c.setFillColor(INK2)
        c.setFont("Sans", 9.5)
        for j, ln in enumerate(wrap(body, "Sans", 9.5, cw - 36)):
            c.drawString(x + 18, top - 54 - j * 15, ln)

    rest = [
        "品特商業",
        "東潮時裝",
        "金漫",
        "羽雁體育",
        "Chester",
        "banana blue",
        "汆食",
        "鵵咖啡",
    ]
    x, y = M, top - ch - 34
    c.setFont("Sans", 10.5)
    for name in rest:
        wdt = pdfmetrics.stringWidth(name, "Sans", 10.5) + 24
        c.setFillColor(CARD2)
        c.rect(x, y - 8, wdt, 26, stroke=0, fill=1)
        c.setFillColor(INK2)
        c.drawString(x + 12, y, name)
        x += wdt + 8
    d.foot("合作夥伴")


def contact(d):
    d.page(CARD2)
    d.mark("GET IN TOUCH")
    y = d.title("要找我，直接打電話最快", H - 142, 30)
    d.para(
        "不管是想吃到好魚、想配一支對的酒、想談合作，還是想聊保險規劃——先聯絡，再看怎麼配。",
        y - 24,
        size=13,
        maxw=780,
    )

    c = d.c
    info = [
        ("公司", "鉅鑫管理顧問有限公司"),
        ("統一編號", "50877146"),
        ("地址", "114 台北市內湖區南京東路六段 461 號 1 樓"),
        ("電話", "(02) 2658-5560"),
        ("E-mail", "giantsatellite2018@gmail.com"),
        ("官方網站", "gs-group.com.tw"),
        ("匠鑫聚訂位", "(02) 2658-5290"),
    ]
    top = H - 258
    for i, (k, v) in enumerate(info):
        x = M + (i % 2) * 420
        yy = top - (i // 2) * 52
        c.setFillColor(INK3)
        c.setFont("Sans", 8.5)
        c.drawString(x, yy, " ".join(k))
        c.setFillColor(INK)
        c.setFont("Sans", 13)
        c.drawString(x, yy - 20, v)

    c.setFillColor(INK3)
    c.setFont("Sans", 7.5)
    c.drawString(
        M,
        26,
        "鉅鑫管理顧問有限公司　凝鉅情感、真鑫相待　／　"
        "內容依據官方網站 gs-group.com.tw 與公司登記資料整理",
    )


def main():
    out = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.expanduser(
            "~/liam-workspace/reviews/凝鉅情感真鑫相待_介紹簡報.pdf"
        )
    )
    d = Deck(out)
    for fn in (
        cover,
        me,
        era,
        fields,
        brands,
        origin,
        house,
        guests,
        giving,
        partners,
        contact,
    ):
        fn(d)
        d.c.showPage()
    d.c.save()
    print("OK: %s（%d 頁）" % (out, d.n))


if __name__ == "__main__":
    main()
