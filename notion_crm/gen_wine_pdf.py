#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鑫酒藏出貨單 PDF 產生器
修改 ORDER 後執行：python3 notion_crm/gen_wine_pdf.py
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

pdfmetrics.registerFont(TTFont("F", "/Library/Fonts/Arial Unicode.ttf"))

# ── 顏色（從原版 PDF 直接抽取）────────────────────────────────────
AMBER = colors.HexColor("#B7874A")  # 品牌金：標題、標籤文字
DARK = colors.HexColor("#2D1B0E")  # 深咖啡：副標、邊框
MID = colors.HexColor("#EFE6D3")  # 羊皮紙：標籤背景
LIGHT = colors.HexColor("#F9F8F2")  # 近白：資料欄背景
BLACK = colors.HexColor("#000000")  # 數值文字
RED = colors.HexColor("#A02010")  # 折扣

# ── 匯款資訊（固定）──────────────────────────────────────────────
BANK = [
    ("銀行", "彰化銀行(009) 南港科學園區分行"),
    ("戶名", "鉅鑫管理顧問有限公司"),
    ("帳號", "5383-01-056001-00"),
]

# ── 修改這裡 ──────────────────────────────────────────────────────
ORDER = {
    "出貨單號": "2026052001",
    "出貨日期": "2026 / 05 / 20",
    "客戶姓名": "詹傑涵 Hank",
    "付款方式": "VIP 優惠價",
    "items": [
        {
            "編碼": "AJS-401J201A",
            "品名": "Annonce de Belair-Monange '20",
            "數量": 6,
            "單位": "瓶",
            "星坊定價": 4930,
            "實售合計": 18000,
        }
    ],
    "備註": (
        "1. 本次訂購 Annonce de Belair-Monange '20 共 1 箱（6 瓶），VIP 特惠價 NT$18,000。\n"
        "2. 星坊酒業目錄參考定價 NT$4,930 / 瓶（合計 NT$29,580），本次折扣 39.1%。\n"
        "3. 如有疑問請聯繫鑫酒藏客服，謝謝惠顧。"
    ),
}


# ── 工具 ──────────────────────────────────────────────────────────
def st(size=10, bold=False, color=BLACK, align=TA_LEFT):
    return ParagraphStyle(
        "s",
        fontName="F",
        fontSize=size,
        leading=size * 1.5,
        textColor=color,
        alignment=align,
        bold=bold,
    )


def tx(text, size=10, bold=False, color=BLACK, align=TA_LEFT):
    return Paragraph(text.replace("\n", "<br/>"), st(size, bold, color, align))


def row_style(bg_label, bg_value):
    return [
        ("BACKGROUND", (0, 0), (0, -1), bg_label),
        ("BACKGROUND", (1, 0), (1, -1), bg_value),
        ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, AMBER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ]


def build():
    customer = ORDER["客戶姓名"].split()[0]
    product = ORDER["items"][0]["品名"].split()[0]
    date_str = ORDER["出貨日期"].replace(" ", "").replace("/", "")
    out_dir = f"/Users/lien/Desktop/鉅鑫管理顧問/鑫酒藏/{date_str[:4]}年出貨單"
    os.makedirs(out_dir, exist_ok=True)
    output = f"{out_dir}/出貨單_{customer}_{product}_{date_str}.pdf"

    W = A4[0] - 36 * mm
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
    )
    s = []

    # ── 標題：鑫酒藏（置中，品牌金）────────────────────────────
    s.append(tx("鑫  酒  藏", 24, True, AMBER, TA_CENTER))
    s.append(Spacer(1, 6))
    s.append(HRFlowable(width=W, thickness=1, color=AMBER, spaceAfter=6))
    s.append(tx("出  貨  單", 17, False, DARK, TA_CENTER))
    s.append(Spacer(1, 10))

    # ── 訂單資訊 ──────────────────────────────────────────────────
    cw = [W * 0.15, W * 0.35, W * 0.15, W * 0.35]
    s.append(
        Table(
            [
                [
                    tx("出貨單號", 10, False, AMBER),
                    tx(ORDER["出貨單號"], 10),
                    tx("出貨日期", 10, False, AMBER),
                    tx(ORDER["出貨日期"], 10),
                ],
                [
                    tx("客戶姓名", 10, False, AMBER),
                    tx(ORDER["客戶姓名"], 11, True),
                    tx("付款方式", 10, False, AMBER),
                    tx(ORDER["付款方式"], 10),
                ],
            ],
            colWidths=cw,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), MID),
                    ("BACKGROUND", (2, 0), (2, -1), MID),
                    ("BACKGROUND", (1, 0), (1, -1), LIGHT),
                    ("BACKGROUND", (3, 0), (3, -1), LIGHT),
                    ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, AMBER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        )
    )
    s.append(Spacer(1, 8))

    # ── 商品明細 section header ────────────────────────────────
    s.append(
        Table(
            [[tx("▍ 商品明細", 10, False, AMBER)]],
            colWidths=[W],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), MID),
                    ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ]
            ),
        )
    )

    # ── 商品表格 ──────────────────────────────────────────────────
    col_w = [W * 0.14, W * 0.30, W * 0.08, W * 0.19, W * 0.12, W * 0.17]
    headers = ["品項編碼", "商品名稱", "數量", "星坊定價", "折扣", "實售小計"]
    rows = [[tx(h, 9, True, DARK, TA_CENTER) for h in headers]]
    for it in ORDER["items"]:
        ref = it["星坊定價"] * it["數量"]
        disc = round((1 - it["實售合計"] / ref) * 100, 1) if ref else 0
        rows.append(
            [
                tx(it["編碼"], 8, align=TA_CENTER),
                tx(it["品名"], 9),
                tx(f"{it['數量']} {it['單位']}", 9, align=TA_CENTER),
                tx(f"NT${it['星坊定價']:,}/瓶<br/>合計 NT${ref:,}", 8, align=TA_CENTER),
                tx(f"- {disc}%", 9, color=RED, align=TA_CENTER),
                tx(f"NT$ {it['實售合計']:,}", 10, True, align=TA_CENTER),
            ]
        )
    s.append(
        Table(
            rows,
            colWidths=col_w,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), MID),
                    ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
                    ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, AMBER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (1, 1), (1, -1), 7),
                ]
            ),
        )
    )

    # ── 合計 ──────────────────────────────────────────────────────
    total = sum(it["實售合計"] for it in ORDER["items"])
    s.append(
        Table(
            [
                [
                    tx("合  計", 12, True, DARK, TA_CENTER),
                    tx(f"NT$  {total:,}", 13, True, DARK, TA_CENTER),
                ],
            ],
            colWidths=[W * 0.84, W * 0.16],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), MID),
                    ("BACKGROUND", (1, 0), (1, 0), LIGHT),
                    ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, AMBER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        )
    )
    s.append(Spacer(1, 8))

    # ── 備註 ──────────────────────────────────────────────────────
    if ORDER.get("備註"):
        s.append(
            Table(
                [
                    [tx("備  註", 10, False, AMBER, TA_CENTER), tx(ORDER["備註"], 9)],
                ],
                colWidths=[W * 0.12, W * 0.88],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, 0), MID),
                        ("BACKGROUND", (1, 0), (1, 0), LIGHT),
                        ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, AMBER),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (1, 0), (1, 0), 8),
                    ]
                ),
            )
        )
        s.append(Spacer(1, 8))

    # ── 匯款資訊 ──────────────────────────────────────────────────
    s.append(
        Table(
            [[tx("▍ 匯款資訊", 10, False, AMBER)]],
            colWidths=[W],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), MID),
                    ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ]
            ),
        )
    )
    for label, value in BANK:
        s.append(
            Table(
                [
                    [
                        tx(label, 9, True, AMBER, TA_CENTER),
                        tx(value, 10 if label == "帳號" else 9),
                    ],
                ],
                colWidths=[W * 0.15, W * 0.85],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, 0), MID),
                        ("BACKGROUND", (1, 0), (1, 0), LIGHT),
                        ("BOX", (0, 0), (-1, -1), 0.5, AMBER),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, AMBER),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING", (1, 0), (1, 0), 8),
                    ]
                ),
            )
        )

    # ── Footer ────────────────────────────────────────────────────
    s.append(Spacer(1, 8))
    s.append(HRFlowable(width=W, thickness=1, color=AMBER, spaceAfter=4))
    s.append(tx("鑫酒藏 · 鉅鑫只提供最高品質", 9, color=DARK, align=TA_CENTER))

    doc.build(s)
    print(f"✅ {output}")
    return output


if __name__ == "__main__":
    import subprocess

    subprocess.run(["open", build()])
