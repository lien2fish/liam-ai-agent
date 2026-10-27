"""頻道大頭貼意象圖（800×800）：黑底金環＋金色圖示，比照窮奢極欲「金拳握幣」那種符號式頭像。

A 金幣地球：金幣正面刻經緯線——錢大到跟一個國家一樣
C 天平：一邊金幣、一邊地球，兩邊打平——「富可敵國」字面的畫面
用法：python3 finance_shorts/avatar_icons.py → 試做成品/頻道_大頭貼_A.png、_C.png
"""

import cairosvg

from build import ROOT

DEFS = """
<defs>
  <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#fff1b8"/><stop offset="0.35" stop-color="#e2b85c"/>
    <stop offset="0.7" stop-color="#a87a22"/><stop offset="1" stop-color="#f3d27a"/>
  </linearGradient>
  <radialGradient id="gold" cx="0.35" cy="0.3" r="0.8">
    <stop offset="0" stop-color="#fff6cf"/><stop offset="0.45" stop-color="#f0c95e"/>
    <stop offset="1" stop-color="#9c6d17"/>
  </radialGradient>
  <linearGradient id="goldL" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fbe39a"/><stop offset="1" stop-color="#b8862a"/>
  </linearGradient>
</defs>
"""

FRAME = """
<circle cx="400" cy="400" r="400" fill="#05070c"/>
<circle cx="400" cy="400" r="372" fill="none" stroke="url(#ring)" stroke-width="22"/>
"""


def globe_lines(cx, cy, r, stroke, w):
    """經緯線：三條經線（橢圓）＋三條緯線。"""
    s = []
    for k in (0.33, 0.7):
        s.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r * k:.1f}" ry="{r}" fill="none" stroke="{stroke}" stroke-width="{w}"/>'
        )
    s.append(
        f'<line x1="{cx}" y1="{cy - r}" x2="{cx}" y2="{cy + r}" stroke="{stroke}" stroke-width="{w}"/>'
    )
    for t in (-0.5, 0, 0.5):
        y = cy + r * t
        half = r * (1 - t * t) ** 0.5
        s.append(
            f'<line x1="{cx - half:.1f}" y1="{y:.1f}" x2="{cx + half:.1f}" y2="{y:.1f}" stroke="{stroke}" stroke-width="{w}"/>'
        )
    return "".join(s)


def coin_globe():
    cx, cy = 400, 400
    return f"""
<circle cx="{cx}" cy="{cy}" r="250" fill="url(#gold)"/>
<circle cx="{cx}" cy="{cy}" r="250" fill="none" stroke="#7a5310" stroke-width="6"/>
<circle cx="{cx}" cy="{cy}" r="214" fill="none" stroke="#8a611a" stroke-width="5" stroke-dasharray="4 10"/>
<circle cx="{cx}" cy="{cy}" r="182" fill="none" stroke="#7a5310" stroke-width="9"/>
<clipPath id="g"><circle cx="{cx}" cy="{cy}" r="182"/></clipPath>
<g clip-path="url(#g)">{globe_lines(cx, cy, 182, "#7a5310", 8)}</g>
<path d="M 255 300 A 182 182 0 0 1 400 218" fill="none" stroke="#fffbe6" stroke-width="10" stroke-linecap="round" opacity="0.75"/>
"""


def balance():
    beam_y = 300
    left, right = 230, 570
    pan_y = 470
    coins = "".join(
        f'<ellipse cx="{left}" cy="{pan_y - 18 - i * 30}" rx="62" ry="17" fill="url(#goldL)" stroke="#7a5310" stroke-width="4"/>'
        for i in range(4)
    )
    return f"""
<rect x="388" y="250" width="24" height="330" rx="10" fill="url(#goldL)"/>
<path d="M 300 610 L 500 610 L 460 575 L 340 575 Z" fill="url(#goldL)"/>
<circle cx="400" cy="240" r="26" fill="url(#gold)"/>
<rect x="{left - 20}" y="{beam_y - 11}" width="{right - left + 40}" height="22" rx="11" fill="url(#goldL)"/>
<line x1="{left}" y1="{beam_y}" x2="{left - 85}" y2="{pan_y}" stroke="#d9ad4f" stroke-width="5"/>
<line x1="{left}" y1="{beam_y}" x2="{left + 85}" y2="{pan_y}" stroke="#d9ad4f" stroke-width="5"/>
<line x1="{right}" y1="{beam_y}" x2="{right - 85}" y2="{pan_y}" stroke="#d9ad4f" stroke-width="5"/>
<line x1="{right}" y1="{beam_y}" x2="{right + 85}" y2="{pan_y}" stroke="#d9ad4f" stroke-width="5"/>
<path d="M {left - 100} {pan_y} Q {left} {pan_y + 60} {left + 100} {pan_y} Z" fill="url(#goldL)"/>
<path d="M {right - 100} {pan_y} Q {right} {pan_y + 60} {right + 100} {pan_y} Z" fill="url(#goldL)"/>
{coins}
<circle cx="{right}" cy="{pan_y - 72}" r="70" fill="url(#gold)" stroke="#7a5310" stroke-width="5"/>
<clipPath id="g2"><circle cx="{right}" cy="{pan_y - 72}" r="70"/></clipPath>
<g clip-path="url(#g2)">{globe_lines(right, pan_y - 72, 70, "#7a5310", 5)}</g>
"""


def render(name, body):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">{DEFS}{FRAME}{body}</svg>'
    out = ROOT / "試做成品" / f"頻道_大頭貼_{name}.png"
    cairosvg.svg2png(
        bytestring=svg.encode(), write_to=str(out), output_width=800, output_height=800
    )
    print(f"  🖼  {out}")


def crown_coin():
    """D 皇冠金幣：金幣上戴皇冠——財富稱王。"""
    return f"""
<circle cx="400" cy="450" r="205" fill="url(#gold)" stroke="#7a5310" stroke-width="6"/>
<circle cx="400" cy="450" r="150" fill="none" stroke="#7a5310" stroke-width="8"/>
<clipPath id="g3"><circle cx="400" cy="450" r="150"/></clipPath>
<g clip-path="url(#g3)">{globe_lines(400, 450, 150, "#7a5310", 7)}</g>
<path d="M 250 255 L 290 145 L 345 215 L 400 115 L 455 215 L 510 145 L 550 255 Z" fill="url(#goldL)" stroke="#7a5310" stroke-width="5" stroke-linejoin="round"/>
<rect x="245" y="245" width="310" height="34" rx="8" fill="url(#goldL)" stroke="#7a5310" stroke-width="5"/>
<circle cx="290" cy="140" r="14" fill="#fff1b8"/><circle cx="400" cy="108" r="16" fill="#fff1b8"/><circle cx="510" cy="140" r="14" fill="#fff1b8"/>
"""


def ingot_globe():
    """E 元寶地球：元寶上頂著地球——東方的財富符號撐起世界。"""
    return f"""
<circle cx="400" cy="330" r="130" fill="url(#gold)" stroke="#7a5310" stroke-width="5"/>
<clipPath id="g4"><circle cx="400" cy="330" r="130"/></clipPath>
<g clip-path="url(#g4)">{globe_lines(400, 330, 130, "#7a5310", 6)}</g>
<path d="M 150 420 Q 180 400 250 430 Q 400 470 550 430 Q 620 400 650 420 Q 640 520 560 575 Q 400 625 240 575 Q 160 520 150 420 Z" fill="url(#goldL)" stroke="#7a5310" stroke-width="6"/>
<path d="M 210 450 Q 400 520 590 450" fill="none" stroke="#fff1b8" stroke-width="7" opacity="0.7"/>
"""


def coin_skyline():
    """F 金幣城市：一疊疊金幣堆成城市天際線——錢堆出一個國家。"""
    heights = [3, 6, 9, 12, 8, 5, 10, 4]
    w, gap, base = 62, 8, 600
    x0 = 400 - (len(heights) * (w + gap) - gap) / 2
    s = []
    for i, n in enumerate(heights):
        x = x0 + i * (w + gap)
        for k in range(n):
            y = base - k * 30
            s.append(f'<rect x="{x:.1f}" y="{y - 26}" width="{w}" height="26" rx="6" fill="url(#goldL)" stroke="#7a5310" stroke-width="3"/>')
    s.append('<circle cx="560" cy="200" r="48" fill="url(#gold)"/>')
    return "".join(s)


def ring_globe():
    """H 金環地球：地球外圍一道金色光環（像土星環）——錢繞著全世界流動。"""
    back = '<path d="M 140 430 A 270 80 0 0 1 660 370" fill="none" stroke="url(#goldL)" stroke-width="26" stroke-linecap="round" transform="rotate(-14 400 400)"/>'
    front = '<path d="M 660 370 A 270 80 0 0 1 140 430" fill="none" stroke="url(#goldL)" stroke-width="26" stroke-linecap="round" transform="rotate(-14 400 400)"/>'
    return f"""
{back}
<circle cx="400" cy="400" r="175" fill="url(#gold)" stroke="#7a5310" stroke-width="6"/>
<clipPath id="g5"><circle cx="400" cy="400" r="175"/></clipPath>
<g clip-path="url(#g5)">{globe_lines(400, 400, 175, "#7a5310", 7)}</g>
{front}
<circle cx="640" cy="300" r="20" fill="url(#gold)"/>
"""


def monster_eye():
    """M1 怪物之眼：豎瞳金眼，虹膜刻經緯線——「一睜眼，就是錢的世界」。"""
    eye = "M 85 400 Q 400 100 715 400 Q 400 700 85 400 Z"
    return f"""
<clipPath id="e1"><path d="{eye}"/></clipPath>
<path d="{eye}" fill="#2a0d08"/>
<g clip-path="url(#e1)">
<circle cx="400" cy="400" r="200" fill="url(#gold)"/>
{globe_lines(400, 400, 200, "#7a5310", 7)}
<ellipse cx="400" cy="400" rx="34" ry="185" fill="#05070c"/>
<ellipse cx="465" cy="320" rx="26" ry="16" fill="#fffbe6" opacity="0.85"/>
</g>
<path d="{eye}" fill="none" stroke="url(#ring)" stroke-width="16" stroke-linejoin="round"/>
"""


def coin_monster():
    """M2 金幣怪：金幣長出犄角、斜眼與獠牙——錢本身就是怪物。"""
    return f"""
<path d="M 250 300 Q 190 210 215 120 Q 265 210 320 255 Z" fill="url(#goldL)" stroke="#7a5310" stroke-width="5" stroke-linejoin="round"/>
<path d="M 550 300 Q 610 210 585 120 Q 535 210 480 255 Z" fill="url(#goldL)" stroke="#7a5310" stroke-width="5" stroke-linejoin="round"/>
<circle cx="400" cy="440" r="215" fill="url(#gold)" stroke="#7a5310" stroke-width="6"/>
<circle cx="400" cy="440" r="185" fill="none" stroke="#8a611a" stroke-width="5" stroke-dasharray="4 10"/>
<path d="M 270 370 L 375 405 L 365 440 Q 300 445 270 370 Z" fill="#05070c"/>
<path d="M 530 370 L 425 405 L 435 440 Q 500 445 530 370 Z" fill="#05070c"/>
<circle cx="335" cy="418" r="9" fill="#fff1b8"/><circle cx="465" cy="418" r="9" fill="#fff1b8"/>
<path d="M 285 505 Q 400 575 515 505 Q 400 615 285 505 Z" fill="#05070c"/>
<path d="M 320 520 L 345 575 L 365 530 Z" fill="#fffbe6"/>
<path d="M 480 520 L 455 575 L 435 530 Z" fill="#fffbe6"/>
"""


def gulp_monster():
    """M3 吞金獸：圓滾滾的怪物張大嘴，一枚金幣正掉進去——錢永遠吃不飽。"""
    teeth = "".join(
        f'<path d="M {x} 470 L {x + 22} 505 L {x + 44} 470 Z" fill="#fffbe6"/>'
        for x in range(268, 520, 44)
    )
    return f"""
<path d="M 285 250 L 255 160 L 330 225 Z" fill="url(#goldL)" stroke="#7a5310" stroke-width="5" stroke-linejoin="round"/>
<path d="M 515 250 L 545 160 L 470 225 Z" fill="url(#goldL)" stroke="#7a5310" stroke-width="5" stroke-linejoin="round"/>
<path d="M 170 470 Q 170 220 400 215 Q 630 220 630 470 Q 630 650 400 650 Q 170 650 170 470 Z" fill="url(#gold)" stroke="#7a5310" stroke-width="6"/>
<circle cx="320" cy="345" r="42" fill="#fffbe6"/><circle cx="480" cy="345" r="42" fill="#fffbe6"/>
<circle cx="330" cy="355" r="22" fill="#05070c"/><circle cx="470" cy="355" r="22" fill="#05070c"/>
<path d="M 255 455 Q 400 430 545 455 Q 540 600 400 610 Q 260 600 255 455 Z" fill="#2a0d08"/>
{teeth}
<ellipse cx="400" cy="560" rx="50" ry="16" fill="#3d1410"/>
<g transform="rotate(-18 520 140)">
<ellipse cx="520" cy="140" rx="46" ry="46" fill="url(#gold)" stroke="#7a5310" stroke-width="5"/>
<circle cx="520" cy="140" r="30" fill="none" stroke="#7a5310" stroke-width="4"/>
</g>
"""


def money_bag_monster():
    """M4 錢袋怪：束口錢袋長出眼睛和獠牙——貪吃的錢袋。"""
    return f"""
<path d="M 330 250 Q 300 180 340 150 Q 400 190 460 150 Q 500 180 470 250 Z" fill="url(#goldL)" stroke="#7a5310" stroke-width="5" stroke-linejoin="round"/>
<rect x="320" y="240" width="160" height="30" rx="12" fill="#7a5310"/>
<path d="M 330 265 Q 160 360 175 500 Q 190 640 400 645 Q 610 640 625 500 Q 640 360 470 265 Z" fill="url(#gold)" stroke="#7a5310" stroke-width="6"/>
<path d="M 285 395 L 370 425 Q 340 470 295 440 Z" fill="#05070c"/>
<path d="M 515 395 L 430 425 Q 460 470 505 440 Z" fill="#05070c"/>
<path d="M 290 510 Q 400 560 510 510 Q 470 590 400 592 Q 330 590 290 510 Z" fill="#05070c"/>
<path d="M 325 525 L 348 572 L 368 535 Z" fill="#fffbe6"/>
<path d="M 475 525 L 452 572 L 432 535 Z" fill="#fffbe6"/>
"""


if __name__ == "__main__":
    render("A", coin_globe())
    render("C", balance())
    render("D", crown_coin())
    render("E", ingot_globe())
    render("F", coin_skyline())
    render("H", ring_globe())
    render("M1", monster_eye())
    render("M2", coin_monster())
    render("M3", gulp_monster())
    render("M4", money_bag_monster())
