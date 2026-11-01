"""大閘蟹分級與蟹王（紙感版）：依旁白長度排時間軸，產生 index.html。

風格沿用「兩位 AI 同事」影片（collab_video/yt2/shared.css）的紙感物件動畫，每場上半放一張真實照片（拍立得框）。
旁白與字幕共用 lines.json：[key, 餵 TTS 的字, 字幕]。音檔在 audio/<key>.wav（不進公開 repo）。

事實出處：
- 分級：江蘇省漁業協會團體標準《陽澄湖大閘蟹等級標準》編制說明（2025-07 徵求意見稿）表 2～表 4
- 蟹王 580.5 g：2024-11-12 王寶和杯全國大蟹比賽（China Daily、上海市政府英文網）
- 圓臍／尖臍、九雌十雄：人民網〈大闸蟹攻略〉、維基百科「中華絨螯蟹」
- 5.8–6.4 台兩＝217.5–240 g（Lien 10-31 確認是台兩），公母都 ≥ A 規格下限
照片與影片全部來自 Wikimedia Commons，作者與授權在 credits.json，畫面上的標示不可拿掉。
⛔ 都不是自家貨：蟹王那張只是示意，腹面實拍不標公母（沒經 Lien 指認）。
"""

import json
import os
import re
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
GAP = 0.35
LEAD = 0.15
TAIL = 1.8

SCENES = [
    ("king", ["v01", "v02"]),
    ("ask", ["v03"]),
    ("weight", ["v04", "v05"]),
    ("fat", ["v06"]),
    ("grade", ["v07"]),
    ("belly", ["v08", "v09"]),
    ("saying", ["v10"]),
    ("end", ["v11", "v12"]),
]

CREDITS = json.load(open(os.path.join(HERE, "credits.json")))
CREDITS["roe"] = {"artist": "Jpatokal", "license": "CC BY-SA 4.0"}

CSS = """
@font-face { font-family: "PingFang TC"; src: local("PingFang TC"); }
@font-face { font-family: "Menlo"; src: local("Menlo"); }
:root {
  --paper:#ece6da; --card:#f8f5ee; --ink:#2b2621; --dim:#6f665a; --line:#cfc6b6;
  --kraft:#d4b07a; --kraft-ink:#4a3820; --seal:#b5322a; --teal:#3c8c86; --roe:#d9773f;
  --sticky:#f3dc8f; --shadow:0 22px 44px rgba(70,52,30,.20), 0 3px 8px rgba(70,52,30,.14);
}
* { margin:0; padding:0; box-sizing:border-box; }
html, body { width:1080px; height:1920px; overflow:hidden; background:var(--paper); }
body { font-family:"PingFang TC",sans-serif; font-weight:600; color:var(--ink); }
#root { position:relative; width:1080px; height:1920px; overflow:hidden; }
.clip { position:absolute; inset:0; }
#bg { background:radial-gradient(80% 60% at 50% 38%, #f3eee4 0%, var(--paper) 60%, #ddd5c6 100%); }
.abs { position:absolute; }
.card { position:absolute; background:var(--card); border-radius:16px; box-shadow:var(--shadow); }
.kraft { position:absolute; left:80px; top:200px; background:var(--kraft); color:var(--kraft-ink);
  font-size:40px; padding:12px 30px; border-radius:6px; box-shadow:0 8px 18px rgba(70,52,30,.22); white-space:nowrap; letter-spacing:.06em; z-index:3; }
.seal { position:absolute; color:var(--seal); border:8px solid var(--seal); border-radius:16px; padding:4px 24px;
  font-size:92px; font-weight:900; letter-spacing:.12em; outline:3px solid var(--seal); outline-offset:7px; white-space:nowrap;
  background:rgba(248,245,238,.7); z-index:4; }
.polar { position:absolute; background:#fff; padding:18px 18px 58px; box-shadow:var(--shadow); }
.polar img, .polar video { display:block; object-fit:cover; }
.polar .pc { position:absolute; left:0; right:0; bottom:14px; text-align:center; font-size:21px; color:var(--dim); font-weight:400; }
.polar .note { position:absolute; right:30px; top:30px; background:rgba(43,38,33,.7); color:#fff; font-size:24px; padding:4px 14px; border-radius:6px; }
.chip { position:absolute; left:90px; width:900px; background:var(--card); border:2px solid var(--line); border-radius:14px;
  font-size:44px; padding:22px 30px 22px 100px; box-shadow:0 8px 18px rgba(70,52,30,.12); white-space:nowrap; }
.chip .ck { position:absolute; left:28px; top:20px; width:52px; height:52px; border-radius:50%; background:var(--teal);
  color:#fff; font-size:34px; display:flex; align-items:center; justify-content:center; }
.chip .dm { color:var(--dim); font-size:38px; margin-left:16px; }
.sticky { position:absolute; background:var(--sticky); box-shadow:0 10px 20px rgba(70,52,30,.18); font-size:48px; padding:26px 40px; white-space:nowrap; }
.sticky::before { content:""; position:absolute; left:50%; top:-14px; width:26px; height:26px; margin-left:-13px;
  border-radius:50%; background:var(--seal); box-shadow:0 3px 5px rgba(0,0,0,.25); }
#head { position:absolute; left:0; right:0; top:110px; text-align:center; font-size:30px; color:var(--dim); letter-spacing:.3em; }
.sub { position:absolute; left:60px; right:60px; top:1440px; bottom:auto; display:flex; justify-content:center; align-items:flex-start; }
.sub span { background:rgba(248,245,238,.95); border-radius:12px; padding:16px 28px; font-size:46px; line-height:1.4;
  text-align:center; box-shadow:0 6px 14px rgba(70,52,30,.12); }

/* 蟹王 */
#kp { left:150px; top:290px; transform:rotate(-2deg); } #kp img { width:780px; height:500px; }
#scale { left:200px; top:930px; width:680px; height:380px; padding:36px 46px; }
#scale .lcd { background:#2f3b37; border-radius:14px; height:190px; display:flex; align-items:flex-end; justify-content:flex-end;
  padding:0 40px 22px; color:#9fe0c8; font-family:Menlo,monospace; font-weight:700; }
#scale .lcd b { font-size:140px; line-height:1; } #scale .lcd i { font-style:normal; font-size:60px; margin-left:14px; }
#scale .plate { margin:30px auto 0; width:460px; height:22px; border-radius:11px; background:var(--line); }
#scale .lbl { margin-top:22px; text-align:center; font-size:32px; color:var(--dim); letter-spacing:.1em; }
#kingseal { left:690px; top:840px; transform:rotate(-9deg); }
#kingnote { left:0; right:0; top:1340px; text-align:center; font-size:36px; color:var(--dim); }
#kingnote b { color:var(--ink); }

/* 第幾級 */
#vp { left:120px; top:290px; } #vp .vbox { width:800px; height:600px; background:#2b2621; }
#crabvid { position:absolute; z-index:5; left:138px; top:308px; width:800px; height:600px; object-fit:cover; }
#askcard { left:110px; top:1000px; width:860px; height:330px; padding:46px 50px; text-align:center; }
#askcard .a { font-size:56px; } #askcard .b { font-size:120px; font-weight:900; color:var(--seal); margin-top:16px; }

/* 重量表 */
#wp { left:600px; top:250px; transform:rotate(3deg); z-index:2; } #wp img { width:380px; height:260px; }
#wtable { left:70px; top:600px; width:940px; height:740px; padding:30px 44px; }
.tr { display:flex; align-items:center; height:190px; border-bottom:2px solid var(--line); border-radius:10px; }
.tr.h { height:90px; font-size:36px; color:var(--dim); }
.tr .k { width:170px; text-align:center; font-size:84px; font-weight:900; font-family:Menlo,monospace; color:var(--kraft-ink); }
.tr.h .k { font-size:36px; font-family:inherit; font-weight:600; color:var(--dim); }
.tr .c { flex:1; text-align:center; }
.tr .c b { display:block; font-size:68px; font-weight:900; } .tr .c span { display:block; font-size:30px; color:var(--dim); margin-top:4px; }

/* 肥滿度 */
#fp { left:150px; top:290px; transform:rotate(-1.5deg); } #fp img { width:780px; height:520px; }
#fat1 { top:950px; } #fat2 { top:1080px; } #fat3 { top:1210px; }

/* 合起來 */
#gp { left:620px; top:250px; transform:rotate(3deg); z-index:2; } #gp img { width:360px; height:250px; }
#matrix { left:60px; top:600px; width:960px; height:720px; padding:30px 36px; }
.mr { display:flex; height:180px; align-items:center; border-bottom:2px solid var(--line); }
.mr.h { height:90px; }
.mr div { flex:1; text-align:center; font-size:58px; font-weight:800; }
.mr.h div { font-size:34px; font-weight:600; color:var(--dim); }
.mr div:first-child { flex:.6; font-family:Menlo,monospace; font-weight:900; color:var(--kraft-ink); font-size:72px; }
.mr .no { color:var(--line); }
#jpseal { left:220px; top:700px; transform:rotate(-7deg); font-size:84px; }

/* 公母 */
#bp { left:240px; top:280px; transform:rotate(-2deg); } #bp img { width:600px; height:400px; }
.bcard { top:820px; width:440px; height:510px; padding:20px 20px; text-align:center; }
#bf { left:80px; } #bm { left:560px; }
.bcard .svgbox { width:400px; height:270px; color:var(--ink); }
.bcard .abd { fill:rgba(217,119,63,0); stroke:var(--ink); }
.bcard .t1 { font-size:48px; font-weight:900; margin-top:16px; }
.bcard .t2 { font-size:58px; font-weight:900; color:var(--roe); margin-top:16px; }

/* 九雌十雄 */
#sp { left:150px; top:290px; transform:rotate(1.5deg); } #sp img { width:780px; height:440px; }
#saybig { left:0; right:0; top:840px; text-align:center; font-size:128px; font-weight:900; letter-spacing:.08em; color:var(--seal); }
.cal { position:absolute; top:1030px; width:300px; }
.cal .top { height:56px; background:var(--seal); border-radius:12px 12px 0 0; }
.cal .bd { height:250px; background:#fffdf7; border-radius:0 0 12px 12px; box-shadow:var(--shadow);
  display:flex; flex-direction:column; align-items:center; justify-content:center; }
.cal .bd b { font-size:76px; font-weight:900; line-height:1; } .cal .bd span { font-size:28px; color:var(--dim); margin-top:8px; }
.cal .bd em { font-style:normal; font-size:52px; font-weight:900; color:var(--roe); margin-top:18px; }
#cal9 { left:170px; transform:rotate(-3deg); } #cal10 { left:610px; transform:rotate(2deg); }

/* 結尾 */
#ep { left:150px; top:290px; transform:rotate(-2deg); } #ep img { width:780px; height:560px; }
#endk { left:50%; top:960px; transform:translateX(-50%); font-size:56px; }
#endchip { left:50%; top:1080px; transform:translateX(-50%); width:auto; }
#dm { left:50%; top:1230px; transform:translateX(-50%) rotate(1.5deg); }
#src { left:40px; right:40px; top:1830px; text-align:center; font-size:20px; color:var(--dim); font-weight:400; line-height:1.5; }
"""


def credit(key):
    c = CREDITS[key]
    return f'Photo: {c["artist"]} / {c["license"]}'


def polar(pid, key, src, note=""):
    media = (
        '<div class="vbox"></div>'
        if src.endswith(".mp4")
        else f'<img src="assets/{src}" alt="" />'
    )
    note = f'<div class="note">{note}</div>' if note else ""
    return f'<div class="polar pop" id="{pid}" data-in="{{first}}:0">{media}{note}<div class="pc">{credit(key)}</div></div>'


def belly_svg(abd):
    legs = "".join(
        f'<line x1="-140" y1="{y}" x2="-190" y2="{y + 26}"/><line x1="140" y1="{y}" x2="190" y2="{y + 26}"/>'
        for y in (-40, 0, 40, 78)
    )
    shell = '<path d="M -150 -70 Q -135 -122 0 -125 Q 135 -122 150 -70 L 128 60 Q 95 128 0 132 Q -95 128 -128 60 Z"/>'
    claws = (
        '<path d="M -132 -100 Q -176 -150 -140 -182 Q -112 -170 -120 -140"/>'
        '<path d="M 132 -100 Q 176 -150 140 -182 Q 112 -170 120 -140"/>'
    )
    return (
        '<svg viewBox="-200 -200 400 365" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">'
        '<g stroke="currentColor" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round">'
        f'{shell}{legs}{claws}</g><path class="abd" stroke-width="7" stroke-linejoin="round" d="{abd}"/></svg>'
    )


FEMALE = "M -92 116 C -112 30 -72 -46 0 -48 C 72 -46 112 30 92 116 Q 0 134 -92 116 Z"
MALE = "M -40 122 L -30 70 L -20 20 L 0 -46 L 20 20 L 30 70 L 40 122 Q 0 130 -40 122 Z"


def gram(x):
    return f"<b>≥ {x} g<span>約 {x / 37.5:.1f} 台兩</span></b>"


# 每場的物件。data-in="key:秒"＝該句開始後幾秒出現；pop＝淡入上浮、stamp＝蓋章
BODY = {
    "king": polar("kp", "hk_steamed", "hk_steamed.jpg", "示意照片")
    + """
<div class="kraft pop" data-in="v01:0">全國大蟹比賽・蟹王</div>
<div class="card pop" id="scale" data-in="v01:0"><div class="lcd"><b>580.5</b><i>g</i></div><div class="plate"></div><div class="lbl">一隻・公蟹</div></div>
<div class="seal stamp" id="kingseal" data-in="v01:0.9">蟹王</div>
<div class="abs pop" id="kingnote" data-in="v02:0.3"><b>2024</b> 王寶和杯全國大蟹比賽・上海</div>""",
    "ask": polar("vp", "live_video", "live_video.mp4")
    + """
<div class="card pop" id="askcard" data-in="v03:0.3"><div class="a">你買的那一隻</div><div class="b">是第幾級？</div></div>""",
    "weight": polar("wp", "tied_cc0", "tied_cc0.jpg")
    + f"""
<div class="kraft pop" data-in="v04:0">① 先秤重</div>
<div class="card pop" id="wtable" data-in="v04:0.2">
 <div class="tr h"><div class="k">規格</div><div class="c">公蟹</div><div class="c">母蟹</div></div>
 <div class="tr" id="rowA"><div class="k">A</div><div class="c">{gram(200)}</div><div class="c">{gram(175)}</div></div>
 <div class="tr"><div class="k">B</div><div class="c">{gram(175)}</div><div class="c">{gram(150)}</div></div>
 <div class="tr"><div class="k">C</div><div class="c">{gram(150)}</div><div class="c">{gram(125)}</div></div>
</div>""",
    "fat": polar("fp", "cut_half", "cut_half.jpg")
    + """
<div class="kraft pop" data-in="v06:0">② 再看肥不肥</div>
<div class="chip pop" id="fat1" data-in="v06:0.6"><span class="ck">✓</span>第三對腳<span class="dm">越硬越好</span></div>
<div class="chip pop" id="fat2" data-in="v06:1.3"><span class="ck">✓</span>背跟肚子之間<span class="dm">越鼓越好</span></div>
<div class="chip pop" id="fat3" data-in="v06:2.0"><span class="ck">✓</span>掀開蟹臍<span class="dm">透色越深越好</span></div>""",
    "grade": polar("gp", "tied_red", "tied_red.jpg")
    + """
<div class="kraft pop" data-in="v07:0">③ 合起來定等級</div>
<div class="card pop" id="matrix" data-in="v07:0">
 <div class="mr h"><div></div><div>第一檔</div><div>第二檔</div><div>第三檔</div></div>
 <div class="mr"><div>A</div><div>精品</div><div>優選</div><div>標準</div></div>
 <div class="mr"><div>B</div><div>優選</div><div>標準</div><div class="no">—</div></div>
 <div class="mr"><div>C</div><div>標準</div><div class="no">—</div><div class="no">—</div></div>
</div>
<div class="seal stamp" id="jpseal" data-in="v07:1.0">精品</div>""",
    "belly": polar("bp", "belly_real", "belly_real.jpg", "實拍腹面")
    + f"""
<div class="kraft pop" data-in="v08:0">翻過來看肚子</div>
<div class="card bcard pop" id="bf" data-in="v08:0.6"><div class="svgbox">{belly_svg(FEMALE)}</div><div class="t1">母蟹・圓臍</div><div class="t2 pop" data-in="v09:0.6">吃蟹黃</div></div>
<div class="card bcard pop" id="bm" data-in="v08:0.9"><div class="svgbox">{belly_svg(MALE)}</div><div class="t1">公蟹・尖臍</div><div class="t2 pop" data-in="v09:2.4">吃蟹膏</div></div>""",
    "saying": polar("sp", "cooked_plate", "cooked_plate.jpg")
    + """
<div class="kraft pop" data-in="v10:0">老話說</div>
<div class="abs stamp" id="saybig" data-in="v10:0.3">九雌十雄</div>
<div class="cal pop" id="cal9" data-in="v10:1.6"><div class="top"></div><div class="bd"><b>九月</b><span>農曆</span><em>吃母蟹</em></div></div>
<div class="cal pop" id="cal10" data-in="v10:3.2"><div class="top"></div><div class="bd"><b>十月</b><span>農曆</span><em>吃公蟹</em></div></div>""",
    "end": polar("ep", "roe", "roe.jpg")
    + """
<div class="kraft pop" id="endk" data-in="v11:0.3">每隻 5.8–6.4 台兩</div>
<div class="chip pop" id="endchip" data-in="v11:1.8"><span class="ck">✓</span>重量都在 A 規格以上</div>
<div class="sticky pop" id="dm" data-in="v12:0.6">想吃的要加快腳步</div>
<div class="abs pop" id="src" data-in="v11:0">資料：江蘇省漁業協會等級標準（2025 徵求意見稿）・China Daily・人民網・維基百科「中華絨螯蟹」<br>照片與影片：Wikimedia Commons，非實際販售商品</div>""",
}


def dur(key):
    with wave.open(os.path.join(HERE, "audio", f"{key}.wav")) as w:
        return w.getnframes() / w.getframerate()


def main():
    lines = {k: sub for k, _, sub in json.load(open(os.path.join(HERE, "lines.json")))}
    t, starts, ends, audio, scene_t = 0.0, {}, {}, [], []
    for _, keys in SCENES:
        scene_t.append(t)
        for k in keys:
            d = dur(k)
            starts[k], ends[k] = t, t + LEAD + d
            audio.append(
                f'<audio id="a-{k}" data-start="{t + LEAD:.2f}" data-duration="{d:.2f}" src="audio/{k}.wav"></audio>'
            )
            t += LEAD + d + GAP
    total = round(t - GAP + TAIL, 2)
    scene_t.append(total)

    html, tl, n = [], [], 0
    for i, (sid, keys) in enumerate(SCENES):
        s0, s1 = scene_t[i], scene_t[i + 1]
        body = BODY[sid].replace("{first}", keys[0])

        def tag(m):
            nonlocal n
            n += 1
            k, off = m.group(2).split(":")
            at = starts[k] + float(off)
            sel = f'[data-anim=\\"{n}\\"]'
            if at < 0.2:  # 開場第一格就要完整可讀，不做淡入
                pass
            elif "stamp" in m.group(1):
                tl.append(
                    f'tl.fromTo("{sel}", {{autoAlpha:0, scale:1.7}}, {{autoAlpha:1, scale:1, duration:0.35, ease:"power3.in"}}, {at:.2f});'
                )
            else:
                tl.append(
                    f'tl.fromTo("{sel}", {{autoAlpha:0, y:30}}, {{autoAlpha:1, y:0, duration:0.5, ease:"power2.out"}}, {at:.2f});'
                )
            return f'{m.group(1)}data-anim="{n}"'

        body = re.sub(r'(<\w+[^>]*?)data-in="([^"]+)"', tag, body)
        html.append(
            f'<section id="sc-{sid}" class="clip" data-start="{s0:.2f}" data-duration="{s1 - s0:.2f}" data-track-index="{i + 2}">'
            f'<div class="clip" id="in-{sid}">{body}</div></section>'
        )
        if sid == "ask":
            html.append(
                f'<video id="crabvid" src="assets/live_video.mp4" muted playsinline data-start="{s0:.2f}" '
                f'data-duration="{s1 - s0:.2f}" data-track-index="30"></video>'
            )
            tl.append(f'tl.fromTo("#crabvid", {{autoAlpha:0}}, {{autoAlpha:1, duration:0.3}}, {s0 + 0.4:.2f});')
            tl.append(f'tl.to("#crabvid", {{autoAlpha:0, duration:0.25}}, {s1 - 0.25:.2f});')
            tl.append(f'tl.set("#crabvid", {{autoAlpha:0}}, {s1:.2f});')
        if i < len(SCENES) - 1:
            tl.append(
                f'tl.to("#in-{sid}", {{opacity:0, duration:0.25, ease:"power1.in"}}, {s1 - 0.25:.2f});'
            )
            tl.append(f'tl.set("#in-{sid}", {{opacity:0}}, {s1:.2f});')
        tl.append(
            f'tl.fromTo("#in-{sid} .polar img", {{scale:1}}, {{scale:1.05, duration:{s1 - s0:.2f}, ease:"none"}}, {s0:.2f});'
        )

    tl.append(
        f'tl.to("#rowA", {{backgroundColor:"rgba(243,220,143,.85)", duration:0.4}}, {starts["v05"] + 0.3:.2f});'
    )
    tl.append(
        f'tl.to("#bf .abd", {{fill:"rgba(217,119,63,.35)", stroke:"#d9773f", duration:0.5}}, {starts["v09"] + 0.3:.2f});'
    )
    tl.append(
        f'tl.to("#bm .abd", {{fill:"rgba(217,119,63,.35)", stroke:"#d9773f", duration:0.5}}, {starts["v09"] + 2.1:.2f});'
    )

    subs = [
        f'<div class="sub clip" data-start="{starts[k]:.2f}" data-duration="{ends[k] - starts[k] + GAP:.2f}" '
        f'data-track-index="20"><span>{sub}</span></div>'
        for k, sub in lines.items()
    ]
    nl = "\n"
    page = f"""<!doctype html>
<html lang="zh-Hant" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<title>大閘蟹分級與蟹王</title>
<script src="vendor/gsap.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div id="root" data-composition-id="species02b" data-start="0" data-duration="{total}" data-fps="24" data-width="1080" data-height="1920">
<div id="bg" class="clip" data-start="0" data-duration="{total}" data-track-index="0"></div>
<div class="clip" data-start="0" data-duration="{total}" data-track-index="1"><div id="head">連老闆・產地到餐桌</div></div>
{nl.join(html)}
{nl.join(subs)}
{nl.join(audio)}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{nl.join(tl)}
window.__timelines["species02b"] = tl;
</script>
</body>
</html>
"""
    open(os.path.join(HERE, "index.html"), "w").write(page)
    print(f"index.html  {total}s  {len(lines)} 句")


if __name__ == "__main__":
    main()
