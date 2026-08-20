#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""鉅鑫管理顧問對外簡報「一人五品牌」的 16:9 投影片版。

內容與網頁版（Artifact）同一份，這支負責可投影／可列印／可寄出的離線版本。
版面刻意做成「一張精密的營運報表」：細線、表格、等寬數字，不用漸層與圖示。

字型：中文襯線走系統 Songti.ttc（index 2 粗／3 細，index 0 是 SC 缺繁體字不要用），
內文走 repo 內的 NotoSansTC.ttf。⚠️ 這支只在 macOS 跑，不進 GitHub Actions。

用法：python3 design/pitch_deck.py [輸出.pdf]
"""
import os
import sys

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

W, H = 960, 540
M = 62

GROUND = HexColor("#E9EAE5")
SURF = HexColor("#F4F5F1")
SURF2 = HexColor("#DEE0D9")
INK = HexColor("#14181C")
INK2 = HexColor("#4A5560")
INK3 = HexColor("#7C8791")
RULE = HexColor("#C9CDC4")
RULE_S = HexColor("#DADDD4")
NAVY = HexColor("#1F4E79")
SEAL = HexColor("#A33B2A")
FILL = HexColor("#D3DCE4")

SONGTI = "/System/Library/Fonts/Supplemental/Songti.ttc"
NOTO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "scripts",
    "fonts",
    "NotoSansTC.ttf",
)

pdfmetrics.registerFont(TTFont("SerifB", SONGTI, subfontIndex=2))
pdfmetrics.registerFont(TTFont("SerifR", SONGTI, subfontIndex=3))
pdfmetrics.registerFont(TTFont("Sans", NOTO))
MONO = "Courier"
MONO_B = "Courier-Bold"


def wrap(text, font, size, maxw):
    """逐字量寬換行——reportlab 不會自己斷中文。"""
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


class Deck:
    def __init__(self, path):
        self.c = canvas.Canvas(path, pagesize=(W, H))
        self.c.setTitle("一人五品牌｜鉅鑫管理顧問")
        self.c.setAuthor("鉅鑫管理顧問有限公司")
        self.n = 0

    def page(self, bg=GROUND):
        self.c.setFillColor(bg)
        self.c.rect(0, 0, W, H, stroke=0, fill=1)
        self.n += 1

    def footer(self, label):
        if self.n <= 1:
            return
        self.c.setFillColor(INK3)
        self.c.setFont("Sans", 7.5)
        self.c.drawString(M, 26, "鉅鑫管理顧問　一人五品牌")
        self.c.setFont(MONO, 7.5)
        self.c.drawRightString(W - M, 26, "%02d" % (self.n - 1))
        self.c.setFillColor(RULE)
        self.c.setLineWidth(0.5)
        self.c.line(M, 40, W - M, 40)
        if label:
            self.c.setFillColor(INK3)
            self.c.setFont("Sans", 7.5)
            self.c.drawCentredString(W / 2, 26, label)

    def eyebrow(self, text, y=H - M - 8):
        self.c.setFillColor(INK3)
        self.c.setFont("Sans", 8.5)
        self.c.drawString(M, y, " ".join(text))
        tw = pdfmetrics.stringWidth(" ".join(text), "Sans", 8.5)
        self.c.setStrokeColor(RULE)
        self.c.setLineWidth(0.5)
        self.c.line(M + tw + 14, y + 3, W - M, y + 3)

    def title(self, text, y, size=34, color=INK, font="SerifB"):
        self.c.setFillColor(color)
        self.c.setFont(font, size)
        for i, ln in enumerate(wrap(text, font, size, W - 2 * M)):
            self.c.drawString(M, y - i * (size * 1.34), ln)
        return y - len(wrap(text, font, size, W - 2 * M)) * (size * 1.34)

    def para(self, text, y, size=12, color=INK2, maxw=None, font="Sans", lead=1.85):
        maxw = maxw or (W - 2 * M)
        self.c.setFillColor(color)
        self.c.setFont(font, size)
        lines = wrap(text, font, size, maxw)
        for i, ln in enumerate(lines):
            self.c.drawString(M, y - i * size * lead, ln)
        return y - len(lines) * size * lead


# ---------------------------------------------------------------- slides


def cover(d):
    d.page()
    c = d.c
    c.setFillColor(INK3)
    c.setFont("Sans", 9)
    c.drawString(M, H - 92, " ".join("鉅鑫管理顧問有限公司"))

    c.setFillColor(INK)
    c.setFont("SerifB", 108)
    c.drawString(M, H - 250, "一人五品牌")

    c.setFillColor(INK2)
    c.setFont("Sans", 24)
    c.drawString(M + 4, H - 296, "十五週，把重複的事交給系統")

    d.para(
        "葡萄酒、茶葉、私廚、海產、管理顧問，加上保險業務、公益與社團。一個人。"
        "這份簡報是這套營運系統的實證紀錄——做了什麼、省下多少、方法怎麼複製。",
        H - 352,
        size=12.5,
        maxw=560,
    )

    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.line(M, 118, W - M, 118)
    x = M
    for k, v in [
        ("期間", "2026.05.09 – 08.20"),
        ("運行中系統", "18"),
        ("版本紀錄", "1,041 筆"),
        ("", "全部可查核"),
    ]:
        if k:
            c.setFillColor(INK3)
            c.setFont("Sans", 9)
            c.drawString(x, 94, k)
            x += pdfmetrics.stringWidth(k, "Sans", 9) + 8
            c.setFillColor(NAVY)
            c.setFont(MONO_B, 9.5)
            c.drawString(x, 94, v)
            x += pdfmetrics.stringWidth(v, MONO_B, 9.5) + 40
        else:
            c.setFillColor(INK3)
            c.setFont("Sans", 9)
            c.drawString(x, 94, v)


def statement(d, eyebrow, head, lede, body, label):
    d.page()
    d.eyebrow(eyebrow)
    y = d.title(head, H - 150, 36)
    y = d.para(lede, y - 34, size=15, color=INK2, maxw=680)
    for b in body:
        y = d.para(b, y - 26, size=12, color=INK2, maxw=680)
    d.footer(label)


def tiles(d):
    d.page()
    d.eyebrow("成果")
    d.title("十五週的累計產出", H - 150, 36)
    d.para(
        "每一個數字都對得上版本紀錄與平台後台，不是估算。", H - 196, size=13, maxw=680
    )

    data = [
        ("18", "條雲端排程運行中", "全年無休"),
        ("94", "天社群自動發文", "IG ＋ FB 同步"),
        ("96", "份市場分析日報", "含 PDF"),
        ("84", "份漁獲行情追蹤", "官方成交價"),
        ("60", "支自動生成影片", "腳本到上傳全自動"),
        ("12", "面大圖送印完成", "CMYK 直送印刷廠"),
    ]

    c = d.c
    gw = (W - 2 * M) / 3.0
    gh = 108
    for i, (num, lab, sub) in enumerate(data):
        col, row = i % 3, i // 3
        x = M + col * gw
        y = H - 260 - row * (gh + 12)
        c.setFillColor(SURF)
        c.rect(x, y, gw - 12, gh, stroke=0, fill=1)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.rect(x, y, gw - 12, gh, stroke=1, fill=0)
        c.setFillColor(NAVY)
        c.setFont(MONO_B, 40)
        c.drawString(x + 20, y + gh - 50, num)
        c.setFillColor(INK2)
        c.setFont("Sans", 11)
        c.drawString(x + 20, y + 34, lab)
        c.setFillColor(INK3)
        c.setFont("Sans", 8.5)
        c.drawString(x + 20, y + 17, sub)
    d.footer("成果")


STEP = [
    ("05/09", 0),
    ("05/16", 2),
    ("05/23", 5),
    ("05/30", 7),
    ("06/06", 7),
    ("06/13", 7),
    ("06/20", 9),
    ("06/27", 14),
    ("07/04", 15),
    ("07/11", 15),
    ("07/18", 16),
    ("07/25", 16),
    ("08/01", 16),
    ("08/08", 16),
    ("08/15", 18),
]


def chart_step(d):
    d.page()
    d.eyebrow("節奏")
    d.title("系統是疊起來的，不是一次做完的", H - 150, 32)
    d.para(
        "每次只上一條，跑穩了再上下一條。中間的平台期是刻意的——那是在確認前一條真的能自己跑。",
        H - 190,
        size=12,
        maxw=700,
    )

    c = d.c
    x0, y0, cw, ch = M + 34, 108, W - 2 * M - 44, 200
    maxy = 20

    def px(i):
        return x0 + cw * i / (len(STEP) - 1)

    def py(v):
        return y0 + ch * v / maxy

    c.setStrokeColor(RULE_S)
    c.setLineWidth(0.5)
    for v in (0, 5, 10, 15, 20):
        c.line(x0, py(v), x0 + cw, py(v))
        c.setFillColor(INK3)
        c.setFont(MONO, 8)
        c.drawRightString(x0 - 10, py(v) - 3, str(v))
        c.setStrokeColor(RULE_S)

    p = c.beginPath()
    p.moveTo(x0, py(0))
    for i, (_, v) in enumerate(STEP):
        if i:
            p.lineTo(px(i), py(STEP[i - 1][1]))
        p.lineTo(px(i), py(v))
    p.lineTo(px(len(STEP) - 1), py(0))
    p.close()
    c.setFillColor(FILL)
    c.drawPath(p, stroke=0, fill=1)

    c.setStrokeColor(NAVY)
    c.setLineWidth(1.6)
    ln = c.beginPath()
    ln.moveTo(x0, py(0))
    for i, (_, v) in enumerate(STEP):
        if i:
            ln.lineTo(px(i), py(STEP[i - 1][1]))
        ln.lineTo(px(i), py(v))
    c.drawPath(ln, stroke=1, fill=0)

    c.setFillColor(NAVY)
    c.circle(px(len(STEP) - 1), py(18), 3.4, stroke=0, fill=1)
    c.setFont(MONO_B, 10)
    c.drawRightString(px(len(STEP) - 1) - 8, py(18) + 8, "18 條")

    c.setFillColor(INK3)
    c.setFont(MONO, 8)
    for i in (0, 3, 6, 9, 12, 14):
        c.drawCentredString(px(i), y0 - 16, STEP[i][0])

    c.setFillColor(INK3)
    c.setFont("Sans", 9)
    c.drawString(x0 - 34, y0 + ch + 16, "運行中的自動化系統數（累計）")
    d.footer("節奏")


def lines(d):
    d.page()
    d.eyebrow("三條產線")
    d.title("同樣的事，換一種做法", H - 150, 34)

    rows = [
        (
            "內容",
            "社群與影音",
            "每天想題目、寫文案、找圖、發布。影片拍完堆在硬碟裡，剪一支要半天。",
            "文案與配圖每天早上八點自動產出並同步發布；影片剪輯有固定產線，三套工具對應三種內容。",
        ),
        (
            "設計送印",
            "大圖與文宣",
            "改一次尺寸就要重排一次版，來回等設計。顏色送到印刷廠才知道對不對。",
            "版面由參數驅動，改尺寸只改一個數字，整面重算。CMYK 輸出規格固定，直接交印刷廠。",
        ),
        (
            "客戶維繫",
            "回購與保單",
            "靠記性和翻名單。想到才打，通常是想不到。",
            "系統每天掃一次，該接觸的人主動出現在信箱裡，附上切入的理由與話術。",
        ),
    ]

    c = d.c
    top, rh = H - 212, 92
    for i, (name, sub, before, after) in enumerate(rows):
        y = top - i * (rh + 10)
        c.setFillColor(SURF)
        c.rect(M, y - rh, W - 2 * M, rh, stroke=0, fill=1)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.rect(M, y - rh, W - 2 * M, rh, stroke=1, fill=0)

        c.setFillColor(INK)
        c.setFont("SerifB", 16)
        c.drawString(M + 20, y - 32, name)
        c.setFillColor(INK3)
        c.setFont("Sans", 8.5)
        c.drawString(M + 20, y - 50, sub)

        colw = (W - 2 * M - 190) / 2 - 20
        for j, (lab, txt, col) in enumerate(
            [("原本", before, INK3), ("現在", after, INK)]
        ):
            cx = M + 176 + j * (colw + 34)
            c.setFillColor(INK3)
            c.setFont("Sans", 7.5)
            c.drawString(cx, y - 24, " ".join(lab))
            c.setFillColor(col)
            c.setFont("Sans", 9.5)
            for k, l in enumerate(wrap(txt, "Sans", 9.5, colw)):
                c.drawString(cx, y - 42 - k * 15, l)
    d.footer("三條產線")


BARS = [
    ("影音製作與上傳", 120, "60 支", 120),
    ("市場分析日報", 64, "96 份", 40),
    ("社群每日發文", 47, "94 天", 30),
    ("漁獲行情追蹤", 28, "84 份", 20),
    ("客戶提醒名單", 28, "約 110 天", 15),
]


def chart_bar(d):
    d.page()
    d.eyebrow("效益")
    d.title("省下的時間，換算得出來", H - 150, 34)
    d.para(
        "下面是估算，不是實測。每一列的假設都寫出來，你可以自己換成你的數字。",
        H - 190,
        size=12,
        maxw=700,
    )

    c = d.c
    lx, bx = M + 4, M + 132
    bw = 300
    top = H - 232
    bh, gap = 20, 12
    maxv = 130

    c.setStrokeColor(RULE_S)
    c.setLineWidth(0.5)
    for v in (0, 40, 80, 120):
        gx = bx + bw * v / maxv
        c.line(gx, top - 5 * (bh + gap) + gap, gx, top + bh)
        c.setFillColor(INK3)
        c.setFont(MONO, 7.5)
        c.drawCentredString(gx, top - 5 * (bh + gap) + gap - 14, str(v))
        c.setStrokeColor(RULE_S)
    c.setFillColor(INK3)
    c.setFont("Sans", 7.5)
    c.drawString(bx + bw + 8, top - 5 * (bh + gap) + gap - 14, "小時")

    for i, (name, hours, _, _) in enumerate(BARS):
        y = top - i * (bh + gap)
        c.setFillColor(INK2)
        c.setFont("Sans", 9.5)
        c.drawRightString(bx - 14, y + 6, name)
        c.setFillColor(NAVY)
        c.roundRect(bx, y, bw * hours / maxv, bh, 3, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont(MONO_B, 9)
        c.drawString(bx + bw * hours / maxv + 8, y + 6, str(hours))

    tx = M + 500
    c.setFillColor(INK3)
    c.setFont("Sans", 7.5)
    for lab, off in [("項目", 0), ("產出", 132), ("單次分", 196), ("時數", 258)]:
        (c.drawString if off < 100 else c.drawRightString)(
            tx + off + (62 if off else 0), top + 20, lab
        )
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.line(tx, top + 14, W - M, top + 14)

    for i, (name, hours, out, per) in enumerate(BARS):
        y = top - i * (bh + gap) + 6
        c.setFillColor(INK2)
        c.setFont("Sans", 9)
        c.drawString(tx, y, name)
        c.setFillColor(INK3)
        c.drawString(tx + 132, y, out)
        c.setFillColor(INK)
        c.setFont(MONO, 9)
        c.drawRightString(tx + 258, y, str(per))
        c.drawRightString(W - M, y, str(hours))
        c.setStrokeColor(RULE_S)
        c.setLineWidth(0.4)
        c.line(tx, y - 8, W - M, y - 8)

    ty = top - 5 * (bh + gap) + 4
    c.setStrokeColor(RULE)
    c.setLineWidth(0.8)
    c.line(tx, ty + 14, W - M, ty + 14)
    c.setFillColor(INK)
    c.setFont("Sans", 10)
    c.drawString(tx, ty, "合計")
    c.setFillColor(NAVY)
    c.setFont(MONO_B, 12)
    c.drawRightString(W - M, ty, "287")
    c.setFillColor(INK3)
    c.setFont("Sans", 8.5)
    c.drawRightString(W - M, ty - 16, "小時")

    d.para(
        "287 小時約等於 36 個工作天，接近一個全職人力做滿一個半月。"
        "這還沒算上「想到要做卻一直沒做」的那些事——系統跑起來之後，它們是被做完的，不是被記著的。",
        92,
        size=10,
        color=INK3,
        maxw=W - 2 * M,
    )
    d.footer("效益")


def cost(d):
    d.page()
    d.eyebrow("成本")
    d.title("兩邊不是同一個量級", H - 150, 34)

    c = d.c
    cw = (W - 2 * M - 12) / 2
    top, ch = H - 210, 158
    cells = [
        (
            SURF,
            "若外包給人",
            "NT$229,600",
            INK2,
            "287 小時 × 行銷／設計外包時薪 NT$800。這是把上一頁那張表換算成錢，同樣是估算。",
        ),
        (
            SURF2,
            "實際工具支出",
            "月費量級",
            NAVY,
            "雲端排程用公開專案的免費額度；生圖每張 US$0.005；週報每次不到 NT$2。按用量計費，沒有綁約。",
        ),
    ]
    for i, (bg, k, v, vc, note) in enumerate(cells):
        x = M + i * (cw + 12)
        c.setFillColor(bg)
        c.rect(x, top - ch, cw, ch, stroke=0, fill=1)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.rect(x, top - ch, cw, ch, stroke=1, fill=0)
        c.setFillColor(INK3)
        c.setFont("Sans", 8.5)
        c.drawString(x + 22, top - 30, " ".join(k))
        c.setFillColor(vc)
        c.setFont(MONO_B, 32)
        c.drawString(x + 22, top - 76, v)
        c.setFillColor(INK3)
        c.setFont("Sans", 9.5)
        for j, l in enumerate(wrap(note, "Sans", 9.5, cw - 44)):
            c.drawString(x + 22, top - 104 - j * 15, l)

    d.para(
        "重點不是「便宜」，是成本結構換了一種：從「請一個人」的固定支出，變成「用多少算多少」的變動支出。"
        "事業規模變大時，前者要再請一個人，後者只是多跑幾次。",
        top - ch - 34,
        size=11.5,
        color=INK2,
        maxw=W - 2 * M,
    )
    d.footer("成本")


def method(d):
    d.page()
    d.eyebrow("方法")
    d.title("可以複製的五件事", H - 148, 34)
    d.para(
        "工具會換，這五條不會。它們是十五週裡踩出來的，每一條背後都有一次修正。",
        H - 186,
        size=12,
        maxw=700,
    )

    items = [
        (
            "先記錄，再自動化",
            "沒有紀錄就不知道時間花在哪裡。兩週後回頭看，重複最多的那幾件事會自己浮出來——通常和你以為的不一樣。",
        ),
        (
            "只自動化不需要判斷的部分",
            "留言可以自動回，但問價格、問到貨的一律轉人工。判斷錯一次的代價，遠高於省下的那幾分鐘。",
        ),
        (
            "驗收看產出，不看回應碼",
            "「系統回報成功」不算成功。要把實際發出去的東西抓回來比對，確認它真的長成你要的樣子。",
        ),
        (
            "踩到的坑要寫下來",
            "同一個問題不該解第二次。怎麼發現的、根因是什麼、以後怎麼避開——這份紀錄比任何一支程式都值錢。",
        ),
        (
            "跑在雲端，不要跑在你的電腦上",
            "系統的價值在於你不在的時候它照跑。綁在自己電腦上的自動化，只是把工作換個時間做而已。",
        ),
    ]

    c = d.c
    y = H - 232
    for i, (head, body) in enumerate(items):
        c.setStrokeColor(NAVY)
        c.setLineWidth(1.6)
        c.line(M, y + 13, M + 22, y + 13)
        c.setFillColor(NAVY)
        c.setFont(MONO_B, 9)
        c.drawString(M, y, "%02d" % (i + 1))
        c.setFillColor(INK)
        c.setFont("SerifB", 14)
        c.drawString(M + 44, y, head)
        c.setFillColor(INK2)
        c.setFont("Sans", 9.5)
        for j, l in enumerate(wrap(body, "Sans", 9.5, W - 2 * M - 44)):
            c.drawString(M + 44, y - 18 - j * 14, l)
        y -= 64
    d.footer("方法")


def limits(d):
    d.page()
    d.eyebrow("界線")
    d.title("什麼情況不該自動化", H - 150, 34)
    d.para(
        "誠實講，這套做法有明確的邊界。談的時候會先確認你的事業落在哪一邊。",
        H - 190,
        size=12,
        maxw=700,
    )

    items = [
        (
            "錯了收不回來的事",
            "對外發布、款項、客戶個資的流向，一律先確認再動。有些平台的內容發出去之後，連系統自己都刪不掉。",
        ),
        (
            "一個月不到三次的事",
            "建置與維護也要成本。頻率不夠高的工作，寫下標準流程比寫成程式划算。",
        ),
        (
            "知識只在你腦裡的事",
            "哪個月份的魚最肥、怎麼分野生與養殖——這種東西 AI 產不出來，也不該讓它編。"
            "它只能幫你把它整理好、用出去。",
        ),
    ]

    c = d.c
    cw = (W - 2 * M - 24) / 3
    top, ch = H - 236, 150
    for i, (head, body) in enumerate(items):
        x = M + i * (cw + 12)
        c.setFillColor(SURF)
        c.rect(x, top - ch, cw, ch, stroke=0, fill=1)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.rect(x, top - ch, cw, ch, stroke=1, fill=0)
        c.setFillColor(SEAL)
        c.rect(x, top - 2, cw, 2, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("SerifB", 14)
        c.drawString(x + 20, top - 34, head)
        c.setFillColor(INK2)
        c.setFont("Sans", 9.5)
        for j, l in enumerate(wrap(body, "Sans", 9.5, cw - 40)):
            c.drawString(x + 20, top - 58 - j * 15, l)
    d.footer("界線")


def closing(d):
    d.page(SURF)
    d.eyebrow("下一步")
    y = d.title("同樣的方法，可以套在你的事業上", H - 152, 34)
    y = d.para(
        "這套系統是為了自己的五個品牌做的，所以每一條都經過實際營運檢驗，不是提案裡的構想。",
        y - 30,
        size=14,
        color=INK2,
        maxw=680,
    )
    y = d.para(
        "如果你的公司也有那種「每天都要做、每次都差不多、但沒人想做」的事，"
        "多半可以用同樣的方式處理掉。從盤點開始——先看清楚時間花在哪裡，再決定要不要動手。",
        y - 26,
        size=12,
        color=INK2,
        maxw=680,
    )

    c = d.c
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.line(M, y - 34, W - M, y - 34)

    info = [
        ("公司", "鉅鑫管理顧問有限公司"),
        ("統一編號", "50877146"),
        ("地址", "台北市內湖區南京東路六段 461 號 1 樓"),
        ("電話", "02-2658-5560"),
    ]
    for i, (k, v) in enumerate(info):
        x = M + (i % 2) * 380
        yy = y - 62 - (i // 2) * 46
        c.setFillColor(INK3)
        c.setFont("Sans", 8)
        c.drawString(x, yy, " ".join(k))
        c.setFillColor(INK)
        c.setFont("Sans", 12)
        c.drawString(x, yy - 20, v)

    c.setFillColor(INK3)
    c.setFont("Sans", 7.5)
    c.drawString(
        M,
        26,
        "資料期間 2026.05.09 – 2026.08.20　／　"
        "產出數字取自版本紀錄與平台後台，時數與金額為估算並已標示假設　／　"
        "本簡報不含任何客戶名稱、報價或個人資料",
    )


def main():
    out = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.expanduser("~/liam-workspace/reviews/一人五品牌_簡報.pdf")
    )
    d = Deck(out)

    cover(d)
    d.c.showPage()

    statement(
        d,
        "現況",
        "時間是唯一不能外包的東西",
        "五個品牌、一份保經業務、一個公益協會、一個社團。行程橫跨漁港、內湖接待會所、三芝咖啡廳與客戶端。",
        [
            "真正吃掉時間的不是決策，是那些每天都要做、但不需要判斷的事：社群要發文、市場行情要追、"
            "客戶回購要盯、保單到期要提醒、影片要剪要上傳。這些事單看都只要二三十分鐘，加起來卻是一份全職工作。",
            "停下來一天，斷的不只是一天。社群的節奏、客戶的溫度、內容的累積，全部一起停。",
        ],
        "現況",
    )
    d.c.showPage()

    statement(
        d,
        "原則",
        "系統做重複，人做判斷",
        "不是把工作丟給 AI，是把工作拆開：哪一段是照規則跑的，哪一段需要你當場判斷。",
        [
            "前者交給系統，跑在雲端，不依賴你的電腦開機、不依賴你人在哪裡。"
            "後者留給人，而且刻意保留——因為判斷錯的代價，遠高於省下的那二十分鐘。",
            "這條線畫在哪裡，就是整套系統成敗的地方。",
        ],
        "原則",
    )
    d.c.showPage()

    for fn in (tiles, chart_step, lines, chart_bar, cost, method, limits, closing):
        fn(d)
        d.c.showPage()

    d.c.save()
    print("OK: %s（%d 頁）" % (out, d.n))


if __name__ == "__main__":
    main()
