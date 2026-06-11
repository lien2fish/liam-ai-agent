#!/usr/bin/env python3
"""表揚海報 — 捐款人名單條列版（一張圖）"""
from PIL import Image, ImageDraw, ImageFont
import math, os, subprocess

W, H = 7016, 9933
DPI = 300
OUT = "/Users/lien/Downloads/海報/"

FONT_BOLD = "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
FONT_MED = "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc"

os.makedirs(OUT, exist_ok=True)


def heart_polygon(cx, cy, scale=1):
    pts = []
    for t in range(0, 360, 3):
        r = math.radians(t)
        x = 16 * math.sin(r) ** 3
        y = (
            13 * math.cos(r)
            - 5 * math.cos(2 * r)
            - 2 * math.cos(3 * r)
            - math.cos(4 * r)
        )
        pts.append((cx + x * scale, cy - y * scale))
    return pts


def draw_heart_tile(img, tile=200, scale=7, alpha=22):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for r in range(H // tile + 2):
        for c in range(W // tile + 2):
            cx = c * tile + (tile // 2 if r % 2 else 0)
            cy = r * tile
            d.polygon(heart_polygon(cx, cy, scale), fill=(255, 255, 255, alpha))
    img.alpha_composite(layer)


def shadow_text(d, x, y, text, font, fill=(255, 255, 255, 255), offset=12):
    d.text((x + offset, y + offset), text, font=font, fill=(0, 0, 0, 140))
    d.text((x, y), text, font=font, fill=fill)


def cx_of(d, text, font):
    bb = d.textbbox((0, 0), text, font=font)
    return (W - (bb[2] - bb[0])) // 2


def make_list_poster(
    bg_path, title, subtitle, donors, filename, overlay_color, accent_rgb
):
    print(f"生成：{filename}（{len(donors)} 位捐款人）")

    # 底圖
    bg = Image.open(bg_path).convert("RGBA")
    bw, bh = bg.size
    sc = max(W / bw, H / bh)
    bg = bg.resize((int(bw * sc), int(bh * sc)), Image.LANCZOS)
    nw, nh = bg.size
    bg = bg.crop(((nw - W) // 2, (nh - H) // 2, (nw - W) // 2 + W, (nh - H) // 2 + H))

    overlay = Image.new("RGBA", (W, H), (*overlay_color, 170))
    canvas = Image.alpha_composite(bg, overlay)
    draw_heart_tile(canvas)
    d = ImageDraw.Draw(canvas)

    # 三重邊框
    for margin, color, w in [
        (80, accent_rgb, 12),
        (100, (255, 255, 255, 200), 5),
        (118, accent_rgb, 4),
    ]:
        d.rectangle([margin, margin, W - margin, H - margin], outline=color, width=w)

    # 角落愛心
    for hx, hy in [(700, 700), (W - 700, 700), (700, H - 700), (W - 700, H - 700)]:
        d.polygon(heart_polygon(hx, hy, 18), fill=(*accent_rgb, 200))

    # ── 主標題（頂部）──
    fnt_title = ImageFont.truetype(FONT_BOLD, 460)
    tx = cx_of(d, title, fnt_title)
    ty = 500
    bb = d.textbbox((0, 0), title, font=fnt_title)
    tw = bb[2] - bb[0]
    d.rectangle([tx - 80, ty - 60, tx + tw + 80, ty - 52], fill=(*accent_rgb, 230))
    shadow_text(d, tx, ty, title, fnt_title, offset=12)
    title_bottom = ty + 460
    d.rectangle(
        [tx - 80, title_bottom + 30, tx + tw + 80, title_bottom + 38],
        fill=(*accent_rgb, 230),
    )

    # ── 子標題 ──
    fnt_sub_title = ImageFont.truetype(FONT_BOLD, 260)
    stx = cx_of(d, subtitle, fnt_sub_title)
    sty = title_bottom + 80
    shadow_text(d, stx, sty, subtitle, fnt_sub_title, fill=(*accent_rgb, 255), offset=8)
    subtitle_bottom = sty + 260
    # 子標題下方細線
    d.rectangle(
        [tx, subtitle_bottom + 30, tx + tw, subtitle_bottom + 34],
        fill=(255, 255, 255, 120),
    )

    # ── 底部雙行標語（裝飾線上一句、下一句）──
    fnt_bottom = ImageFont.truetype(FONT_BOLD, 260)  # 兩句統一字體
    line_above = "等一個便當，等一個疼惜"
    line_below = "疼惜食物。疼惜台灣"

    sep_y = H - 800  # 裝飾線 Y 位置
    gap = 55  # 文字與線的間距
    # 線的左右邊界：角落愛心圓心 x=700 往內留出心形半徑（約 290px）不穿過愛心
    line_x1 = 700 + 300
    line_x2 = W - 700 - 300

    # 裝飾線（accent 粗線 + 白色細線）
    d.rectangle([line_x1, sep_y, line_x2, sep_y + 6], fill=(*accent_rgb, 220))
    d.rectangle([line_x1, sep_y + 18, line_x2, sep_y + 22], fill=(255, 255, 255, 120))

    # 上方文字
    sy_above = sep_y - gap - 260
    shadow_text(
        d,
        cx_of(d, line_above, fnt_bottom),
        sy_above,
        line_above,
        fnt_bottom,
        fill=(255, 255, 255, 210),
        offset=8,
    )

    # 下方文字
    sy_below = sep_y + 22 + gap
    shadow_text(
        d,
        cx_of(d, line_below, fnt_bottom),
        sy_below,
        line_below,
        fnt_bottom,
        fill=(255, 255, 255, 230),
        offset=8,
    )

    # ── 捐款人名單（條列）──
    # 左右邊界對齊四個角落愛心的圓心 x=700
    list_l = 700
    list_r = W - 700
    list_w = list_r - list_l  # = 5616px

    name_size = 300
    amt_size = 300
    line_gap = 20  # 名字換行時兩行間距
    row_gap = 260  # 每筆之間行距
    col_gap = 700  # 名字與金額之間固定間距（加大）
    fnt_name = ImageFont.truetype(FONT_BOLD, name_size)
    fnt_amt = ImageFont.truetype(FONT_BOLD, amt_size)

    def amt_str(amount):
        return f"NT$ {amount}" if amount.replace(",", "").isdigit() else amount

    # 固定金額欄：所有金額對齊右側，名字欄寬 = list_w - max_amt_w - col_gap
    all_at = [amt_str(amount) for _, amount in donors]
    max_amt_w = max(d.textbbox((0, 0), t, font=fnt_amt)[2] for t in all_at)
    name_col_w = list_w - max_amt_w - col_gap  # ≈ 6416 - 2217 - 700 = 3499px

    def wrap_name(name):
        """名字超過名字欄寬時，找讓「兩行都 ≤ name_col_w」的最平衡斷點"""
        nw = d.textbbox((0, 0), name, font=fnt_name)[2]
        if nw <= name_col_w:
            return [name]
        best, best_diff = None, float("inf")
        for sp in range(2, len(name) - 1):
            l1, l2 = name[:sp], name[sp:]
            w1 = d.textbbox((0, 0), l1, font=fnt_name)[2]
            w2 = d.textbbox((0, 0), l2, font=fnt_name)[2]
            if w1 <= name_col_w and w2 <= name_col_w:
                diff = abs(w1 - w2)
                if diff < best_diff:
                    best_diff, best = diff, [l1, l2]
        return best if best else [name]

    # 預計算每筆行高
    rows = []
    for name, amount in donors:
        at = amt_str(amount)
        lines = wrap_name(name)
        h = name_size * len(lines) + line_gap * (len(lines) - 1)
        rows.append((lines, at, h))

    total_h = sum(r[2] for r in rows) + row_gap * (len(rows) - 1)

    zone_top = subtitle_bottom + 120
    zone_bottom = int(H * 0.68)
    start_y = zone_top + max(0, (zone_bottom - zone_top - total_h) // 2)

    y = start_y
    for lines, at, row_h in rows:
        block_h = row_h  # 名字區塊實際高度
        amt_vert = y + (block_h - amt_size) // 2  # 金額垂直置中對齊名字區塊

        # 名字（左對齊，可能雙行）
        for li, line in enumerate(lines):
            shadow_text(
                d, list_l, y + li * (name_size + line_gap), line, fnt_name, offset=8
            )

        # 金額（右對齊，垂直置中）
        aw = d.textbbox((0, 0), at, font=fnt_amt)[2]
        shadow_text(
            d, list_r - aw, amt_vert, at, fnt_amt, fill=(*accent_rgb, 255), offset=8
        )

        y += block_h + row_gap

    out_path = OUT + filename.replace(".png", ".tif")
    rgb = canvas.convert("RGB")
    cmyk = rgb.convert("CMYK")
    cmyk.save(out_path, "TIFF", dpi=(DPI, DPI), compression="lzw")
    print(f"  ✅ {out_path}  ({os.path.getsize(out_path) // 1024}KB)")
    return out_path


# ── 100 萬以上捐款 ──
donors_100 = [
    ("僑威科技", "2,500,000"),
    ("簡承盈", "1,700,000"),
    ("楊奕蘭", "1,500,000"),
    ("謝德璋", "1,200,000"),
    ("簡清潭", "1,100,000"),
    ("鉅陞建設", "1,000,000"),
]

p1 = make_list_poster(
    bg_path="/Users/lien/Desktop/未命名設計-1.jpg",
    title="惜食台灣行動協會",
    subtitle="累積100萬以上捐款",
    donors=donors_100,
    filename="累積100萬以上捐款_名單.tif",
    overlay_color=(100, 10, 10),
    accent_rgb=(255, 215, 0),
)


# ── 50 萬以上捐款 ──
donors_50 = [
    ("王光明", "600,000"),
    ("林子軒", "600,000"),
    ("邱正宏美學教育基金會", "600,000"),
    ("謝明達", "500,000"),
    ("國寶社會福利慈善事業基金會", "500,000"),
    ("海悅國際", "500,000"),
    ("白俊宇", "全區磁磚捐贈"),
]

p2 = make_list_poster(
    bg_path="/Users/lien/Desktop/191214-growth-1170x780.jpg",
    title="惜食台灣行動協會",
    subtitle="累積50萬以上捐款",
    donors=donors_50,
    filename="累積50萬以上捐款_名單.tif",
    overlay_color=(10, 60, 20),
    accent_rgb=(144, 238, 144),
)

subprocess.Popen(["open", p1])
subprocess.Popen(["open", p2])
print("\n🎉 兩張海報完成！")
