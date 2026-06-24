#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鑫海產出貨單 PDF 產生器
修改 ORDER 後執行：python3 notion_crm/gen_seafood_pdf.py
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

# ── 顏色（海洋深藍系）────────────────────────────────────────────
TEAL = colors.HexColor("#1B5E7B")  # 品牌藍：標題、標籤文字
DARK = colors.HexColor("#0D2B38")  # 深藍：副標、邊框
MID = colors.HexColor("#D6EAF4")  # 淺藍：標籤背景
LIGHT = colors.HexColor("#F4FAFD")  # 近白：資料欄背景
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
    "出貨單號": "2026060201",
    "出貨日期": "2026 / 06 / 02",
    "客戶姓名": "詹傑涵 Hank",
    "地址": "台北市內湖路一段387巷8號7樓",
    "付款方式": "現金",
    "items": [
        {
            "品名": "黑鮪魚金三角",
            "規格": "8兩",
            "數量": 1,
            "單位": "份",
            "單價": 2000,
            "實售合計": 2000,
        }
    ],
    "備註": (
        "野生黑鮪魚，龜吼漁港現流直送，品質保證。\n"
        "【保鮮須知】收到後請立即冷藏（0～4°C）或冷凍（-18°C以下）。"
        "生食建議當日食用；解凍請置冷藏室緩慢退冰，切勿常溫或熱水解凍。"
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
    return Paragraph(str(text).replace("\n", "<br/>"), st(size, bold, color, align))


def build(show_bank=True, show_items=False, field_size=14):
    customer = ORDER["客戶姓名"].split()[0]
    product = ORDER["items"][0]["品名"]
    date_str = ORDER["出貨日期"].replace(" ", "").replace("/", "")
    archive = f"/Users/lien/Desktop/鉅鑫管理顧問/鑫海產/{date_str[:4]}年出貨單"
    os.makedirs(archive, exist_ok=True)
    filename = f"出貨單_{customer}_{product}_{date_str}.pdf"
    output = f"/Users/lien/Desktop/{filename}"

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

    # ── 標題：鑫海產（置中，品牌藍）────────────────────────────
    s.append(tx("鑫  海  產", 24, True, TEAL, TA_CENTER))
    s.append(Spacer(1, 4))
    s.append(tx("龜吼現流活海產", 11, False, DARK, TA_CENTER))
    s.append(Spacer(1, 6))
    s.append(HRFlowable(width=W, thickness=1, color=TEAL, spaceAfter=6))
    s.append(tx("出  貨  單", 17, False, DARK, TA_CENTER))
    s.append(Spacer(1, 10))

    # ── 訂單資訊 ──────────────────────────────────────────────────
    cw = [W * 0.15, W * 0.35, W * 0.15, W * 0.35]
    s.append(
        Table(
            [
                [
                    tx("出貨單號", field_size, False, TEAL),
                    tx(ORDER["出貨單號"], field_size),
                    tx("出貨日期", field_size, False, TEAL),
                    tx(ORDER["出貨日期"], field_size),
                ],
                [
                    tx("客戶姓名", field_size, False, TEAL),
                    tx(ORDER["客戶姓名"], 16, True),
                    tx("付款方式", field_size, False, TEAL),
                    tx(ORDER["付款方式"], field_size),
                ],
                [
                    tx("地　　址", field_size, False, TEAL),
                    tx(ORDER.get("地址", ""), field_size),
                    "",
                    "",
                ],
            ],
            colWidths=cw,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), MID),
                    ("BACKGROUND", (2, 0), (2, 1), MID),
                    ("BACKGROUND", (1, 0), (1, -1), LIGHT),
                    ("BACKGROUND", (3, 0), (3, 1), LIGHT),
                    ("BACKGROUND", (1, 2), (3, 2), LIGHT),
                    ("SPAN", (1, 2), (3, 2)),
                    ("BOX", (0, 0), (-1, -1), 0.8, TEAL),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, TEAL),
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
    if show_items:
        s.append(
            Table(
                [[tx("▍ 商品明細", 10, False, TEAL)]],
                colWidths=[W],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), MID),
                        ("BOX", (0, 0), (-1, -1), 0.8, TEAL),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            )
        )

        # ── 商品表格 ──────────────────────────────────────────────────
        col_w = [W * 0.50, W * 0.25, W * 0.25]
        headers = ["商品名稱", "規格", "數量"]
        rows = [[tx(h, 9, True, DARK, TA_CENTER) for h in headers]]
        for it in ORDER["items"]:
            rows.append(
                [
                    tx(it["品名"], 10),
                    tx(it["規格"], 9, align=TA_CENTER),
                    tx(f"{it['數量']} {it['單位']}", 9, align=TA_CENTER),
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
                        ("BOX", (0, 0), (-1, -1), 0.8, TEAL),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, TEAL),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING", (1, 0), (1, -1), 7),
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
                    [
                        tx("備  註", field_size, False, TEAL, TA_CENTER),
                        tx(ORDER["備註"], field_size - 1),
                    ],
                ],
                colWidths=[W * 0.12, W * 0.88],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, 0), MID),
                        ("BACKGROUND", (1, 0), (1, 0), LIGHT),
                        ("BOX", (0, 0), (-1, -1), 0.8, TEAL),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, TEAL),
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
    if show_bank:
        s.append(
            Table(
                [[tx("▍ 匯款資訊", 10, False, TEAL)]],
                colWidths=[W],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), MID),
                        ("BOX", (0, 0), (-1, -1), 0.8, TEAL),
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
                            tx(label, 9, True, TEAL, TA_CENTER),
                            tx(value, 10 if label == "帳號" else 9),
                        ],
                    ],
                    colWidths=[W * 0.15, W * 0.85],
                    style=TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (0, 0), MID),
                            ("BACKGROUND", (1, 0), (1, 0), LIGHT),
                            ("BOX", (0, 0), (-1, -1), 0.5, TEAL),
                            ("INNERGRID", (0, 0), (-1, -1), 0.5, TEAL),
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
    s.append(HRFlowable(width=W, thickness=1, color=TEAL, spaceAfter=4))
    s.append(tx("鑫海產 · 鉅鑫只提供最高品質", 9, color=DARK, align=TA_CENTER))

    doc.build(s)
    import shutil

    shutil.copy(output, f"{archive}/{filename}")
    print(f"✅ 桌面：{output}")
    print(f"   備份：{archive}/{filename}")
    return output


if __name__ == "__main__":
    import subprocess

    subprocess.run(["open", build()])
