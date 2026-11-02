"""大閘蟹知識 2：大陸蟹與台灣蟹（紙感版）：依旁白長度排時間軸，產生 index.html。

旁白與字幕共用 lines.json：[key, 餵 TTS 的字, 字幕]。音檔在 audio/<key>.wav（不進公開 repo）。

事實出處：
- 一兩換算、2014 同重量比價：旺報 2014-09-30；遠見 2015-01、海大《大閘蟹養殖》2012 佐證陸蟹常較低價
- 物種：海大《大閘蟹養殖》2012；水產試驗所
- 大陸 2026 預估破百萬噸、2025 為 93.9 萬噸：世界日報 2026-10-28、澎湃 2026-10
- 苗栗 2026：29 戶、21.13 公頃、68 項檢測、蟹環：苗栗縣政府農業處 115-10-06；2025 同制度見中央社 2025-09-30
- 陽澄湖 2026：1.01 萬噸，湖區約 1600、池塘約 8500，價格持平：協會聲明 2026-10-19（澎湃全文）
- 無錫 2.5 兩母蟹 12～19.9 元：澎湃 2026-10-16（批發／零售／商超）、央視
- 陽澄湖名氣：海大 2012、Michelin HK 2017
- 進口管制：食藥署輸入管制頁（維護 2026-10-27）；逐批查驗見自由 2025-10-28、公視 2024-12-04
⛔ 不下「查驗或名氣造成高價」的因果，也不比口感優劣；都不是自家貨，不暗示自家貨產地。
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
    ("weigh", ["v01"]),
    ("conv", ["v02", "v03"]),
    ("same", ["v04"]),
    ("scale", ["v05"]),
    ("lake", ["v06", "v07"]),
    ("notsure", ["v08"]),
    ("price", ["v09", "v10"]),
    ("why", ["v11"]),
    ("guard", ["v12"]),
    ("end", ["v13"]),
]

CREDITS = json.load(open(os.path.join(HERE, "credits.json")))

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
.polar img { display:block; object-fit:cover; }
.polar .pc { position:absolute; left:0; right:0; bottom:14px; text-align:center; font-size:21px; color:var(--dim); font-weight:400; white-space:nowrap; overflow:hidden; }
.polar .note { position:absolute; right:30px; top:30px; background:rgba(43,38,33,.7); color:#fff; font-size:24px; padding:4px 14px; border-radius:6px; }
.chip { position:absolute; left:90px; width:900px; background:var(--card); border:2px solid var(--line); border-radius:14px;
  font-size:48px; padding:22px 30px 22px 100px; box-shadow:0 8px 18px rgba(70,52,30,.12); white-space:nowrap; }
.chip .ck { position:absolute; left:28px; top:22px; width:52px; height:52px; border-radius:50%; background:var(--teal);
  color:#fff; font-size:34px; display:flex; align-items:center; justify-content:center; }
.chip .dm { color:var(--dim); font-size:38px; margin-left:16px; }
#head { position:absolute; left:0; right:0; top:110px; text-align:center; font-size:30px; color:var(--dim); letter-spacing:.3em; }
.sub { position:absolute; left:50px; right:50px; top:1440px; bottom:auto; display:flex; justify-content:center; align-items:flex-start; }
.sub span { background:rgba(248,245,238,.95); border-radius:12px; padding:16px 28px; font-size:46px; line-height:1.4;
  text-align:center; box-shadow:0 6px 14px rgba(70,52,30,.12); }
.lbl { font-size:32px; color:var(--dim); letter-spacing:.06em; }

/* 五兩兩台秤 */
#wp { left:150px; top:190px; transform:rotate(-2deg); } #wp img { width:780px; height:440px; }
.sc { top:850px; width:450px; height:430px; padding:28px; text-align:center; }
#scL { left:70px; } #scR { left:560px; }
.sc .tt { font-size:50px; font-weight:900; margin-bottom:20px; }
.sc .lcd { background:#2f3b37; border-radius:14px; height:170px; display:flex; align-items:flex-end; justify-content:center;
  padding-bottom:24px; color:#9fe0c8; font-family:Menlo,monospace; font-weight:700; }
.sc .lcd b { font-size:104px; line-height:1; } .sc .lcd i { font-style:normal; font-size:46px; margin-left:10px; }
.sc .plate { margin:28px auto 0; width:300px; height:18px; border-radius:9px; background:var(--line); }
#diff { left:0; right:0; top:760px; text-align:center; z-index:4; }
#diff span { display:inline-block; background:var(--seal); color:#fff; font-size:44px; font-weight:900; padding:6px 26px; border-radius:8px; transform:rotate(-1.5deg); }

/* 換算表 */
#ctable { left:70px; top:330px; width:940px; height:980px; padding:40px 44px; }
.tr { display:flex; align-items:center; height:230px; border-bottom:2px solid var(--line); }
.tr.h { height:100px; font-size:40px; color:var(--dim); }
.tr .k { width:230px; text-align:center; font-size:60px; font-weight:900; color:var(--kraft-ink); }
.tr.h .k { font-size:40px; font-weight:600; color:var(--dim); }
.tr .c { flex:1; text-align:center; }
.tr .c b { display:block; font-size:80px; font-weight:900; font-family:Menlo,monospace; }
.tr .c span { font-size:40px; color:var(--dim); }
#eq { left:60px; right:60px; top:1020px; text-align:center; }
#eq b { display:inline-block; font-size:58px; font-weight:900; color:var(--seal); white-space:nowrap; }
#eq em { display:block; font-style:normal; margin-top:18px; font-size:38px; color:var(--dim); }

/* 同一物種 */
#sp { left:150px; top:280px; transform:rotate(1.5deg); } #sp img { width:780px; height:560px; }
#sameseal { left:230px; top:960px; transform:rotate(-5deg); }
#latin { left:0; right:0; top:1210px; text-align:center; font-size:46px; font-style:italic; color:var(--dim); font-weight:500; }

/* 規模 */
.bar { position:absolute; left:80px; width:920px; }
.bar .nm { font-size:52px; font-weight:900; margin-bottom:22px; }
.bar .big { font-size:100px; font-weight:900; color:var(--seal); line-height:1.1; }
.bar .small { font-size:100px; font-weight:900; color:var(--teal); line-height:1.1; }
.bar .note2 { font-size:40px; color:var(--dim); margin-top:10px; }
#barC { top:300px; height:400px; } #barT { top:740px; height:590px; }
.bar { background:var(--card); border-radius:16px; box-shadow:var(--shadow); padding:50px 56px; }

/* 陽澄湖 */
#lp { left:120px; top:280px; transform:rotate(-1.5deg); } #lp img { width:840px; height:430px; }
#lname { left:310px; top:960px; transform:rotate(-4deg); }
#ring { left:90px; top:820px; width:900px; height:490px; padding:36px 44px; display:flex; align-items:center; gap:50px; }
#ring svg { width:320px; height:320px; flex:none; }
#ring .tx b { display:block; font-size:92px; font-weight:900; color:var(--seal); line-height:1.1; }
#ring .tx span { display:block; font-size:42px; margin-top:12px; white-space:nowrap; }
#ring .tx em { display:block; font-style:normal; font-size:36px; color:var(--dim); margin-top:18px; white-space:nowrap; }

/* 不一定 */
#qp { left:150px; top:280px; transform:rotate(2deg); } #qp img { width:780px; height:560px; }
#qcard { left:110px; top:960px; width:860px; height:340px; padding:50px; text-align:center; }
#qcard .a { font-size:60px; }
#nope { left:310px; top:1100px; transform:rotate(-6deg); font-size:110px; }

/* 價錢 */
.pcard { left:80px; width:920px; padding:30px 44px; }
#p1 { top:270px; height:270px; } #p2 { top:565px; height:190px; } #p3 { top:790px; height:450px; }
.pcard .h1 { font-size:36px; color:var(--dim); }
.pcard .v1 { font-size:68px; font-weight:900; margin-top:10px; white-space:nowrap; }
.pcard .v1 i { font-style:normal; color:var(--seal); }
.pcard .v2 { font-size:50px; font-weight:800; margin-top:10px; white-space:nowrap; }
.cmp { display:flex; gap:30px; margin-top:26px; }
.cmp div { flex:1; background:#fffdf7; border:2px solid var(--line); border-radius:12px; text-align:center; padding:30px 10px; }
.cmp div b { display:block; font-size:44px; }
.cmp div strong { display:block; font-size:74px; font-weight:900; color:var(--roe); margin-top:18px; white-space:nowrap; font-family:Menlo,monospace; }
.cmp div small { display:block; font-size:30px; color:var(--dim); margin-top:10px; font-weight:400; }

/* 三個因素 */
#yp { left:150px; top:280px; transform:rotate(-1.5deg); } #yp img { width:780px; height:520px; }
#w1 { top:930px; } #w2 { top:1070px; } #w3 { top:1210px; }

/* 把關 */
.gcard { top:300px; width:450px; height:1010px; padding:36px 30px; }
#gL { left:70px; } #gR { left:560px; }
.gcard .tt { font-size:58px; font-weight:900; text-align:center; padding-bottom:24px; border-bottom:3px solid var(--line); }
.gcard .it { font-size:46px; font-weight:800; margin-top:50px; line-height:1.3; text-align:center; }
.gcard .it span { display:block; font-size:30px; color:var(--dim); font-weight:500; margin-top:8px; }
.gcard .big { font-size:112px; font-weight:900; color:var(--teal); text-align:center; margin-top:44px; font-family:Menlo,monospace; line-height:1; }

/* 結尾 */
#ep { left:190px; top:260px; transform:rotate(-2deg); } #ep img { width:700px; height:560px; }
.ask1 { position:absolute; width:440px; left:0; background:var(--sticky); box-shadow:0 10px 20px rgba(70,52,30,.18); font-size:58px; font-weight:900; padding:26px 0; text-align:center; }
#a1 { left:80px; top:920px; transform:rotate(-1deg); } #a2 { left:560px; top:920px; transform:rotate(1deg); }
#a3 { left:80px; top:1070px; transform:rotate(1deg); } #a4 { left:560px; top:1070px; transform:rotate(-1deg); }
#src { left:30px; right:30px; top:1745px; text-align:center; font-size:21px; color:var(--dim); font-weight:400; line-height:1.5; }
"""


def credit(key):
    c = CREDITS[key]
    return f'Photo: {c["artist"]} / {c["license"]}'


def polar(pid, key, note=""):
    note = f'<div class="note">{note}</div>' if note else ""
    return (
        f'<div class="polar pop" id="{pid}" data-in="{{first}}:0"><img src="assets/{key}.jpg" alt="" />'
        f'{note}<div class="pc">{credit(key)}</div></div>'
    )


# 每場的物件。data-in="key:秒"＝該句開始後幾秒出現；pop＝淡入上浮、stamp＝蓋章
BODY = {
    "weigh": polar("wp", "yc_large", "示意照片")
    + """
<div class="abs" id="diff"><span>同樣「五兩」</span></div>
<div class="card sc pop" id="scL" data-in="v01:0"><div class="tt">大陸五兩</div><div class="lcd"><b>250</b><i>g</i></div><div class="plate"></div></div>
<div class="card sc pop" id="scR" data-in="v01:0"><div class="tt">台灣五兩</div><div class="lcd"><b>187.5</b><i>g</i></div><div class="plate"></div></div>""",
    "conv": """
<div class="kraft pop" data-in="v02:0">先換成公克</div>
<div class="card pop" id="ctable" data-in="v02:0.2">
 <div class="tr h"><div class="k"></div><div class="c">大陸</div><div class="c">台灣</div></div>
 <div class="tr"><div class="k">一斤</div><div class="c"><b>500</b><span>克（10 兩）</span></div><div class="c"><b>600</b><span>克（16 兩）</span></div></div>
 <div class="tr"><div class="k">一兩</div><div class="c"><b>50</b><span>克</span></div><div class="c"><b>37.5</b><span>克</span></div></div>
</div>
<div class="abs pop" id="eq" data-in="v03:0.2"><b>大陸 4 兩 ＝ 200 克 ＝ 台灣 5 兩</b></div>""",
    "same": polar("sp", "mini", "示意照片")
    + """
<div class="seal stamp" id="sameseal" data-in="v04:0.8">同一個物種</div>
<div class="abs pop" id="latin" data-in="v04:1.4">中華絨螯蟹 Eriocheir sinensis</div>""",
    "scale": """
<div class="bar pop" id="barC" data-in="v05:1.2"><div class="nm">大陸・2026 預估</div><div class="big">破 100 萬噸</div></div>
<div class="bar pop" id="barT" data-in="v05:4.0"><div class="nm">苗栗縣輔導・2026</div><div class="small">29 戶</div><div class="small">約 21 公頃</div><div class="note2">放養約 41.5 萬隻</div></div>""",
    "lake": polar("lp", "yc_scenery", "陽澄湖")
    + """
<div class="kraft pop" data-in="v06:0">名氣最大的產區</div>
<div class="seal stamp" id="lname" style="z-index:0" data-in="v06:3.2">陽澄湖</div>
<div class="card pop" id="ring" data-in="v07:0.2">
 <svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="none" stroke="#cfc6b6" stroke-width="16"/>
 <circle cx="50" cy="50" r="40" fill="none" stroke="#b5322a" stroke-width="16" stroke-dasharray="2.5 251" transform="rotate(-90 50 50)"/></svg>
 <div class="tx"><b>約 1%</b><span>預估 1.01 萬噸</span><em>湖區約 1600 噸</em><em>沿湖池塘約 8500 噸</em></div>
</div>""",
    "notsure": polar("qp", "yc_raw", "示意照片")
    + """
<div class="card pop" id="qcard" data-in="v08:0"><div class="a">大陸蟹一定比較貴？</div></div>
<div class="seal stamp" id="nope" data-in="v08:1.8">不一定</div>""",
    "price": """
<div class="card pcard pop" id="p1" data-in="v09:0"><div class="h1">2026・江蘇無錫市場・二兩半母蟹（約 125 克）</div><div class="v1">一隻 <i>人民幣十幾元</i></div></div>
<div class="card pcard pop" id="p2" data-in="v09:3.6"><div class="h1">陽澄湖協會的說法</div><div class="v2">本產區價格與近三年持平</div></div>
<div class="card pcard pop" id="p3" data-in="v10:0"><div class="h1">2014 年報導・一樣 200 克・新台幣</div>
 <div class="cmp"><div><b>陸蟹</b><strong>250–350</strong><small>元／隻</small></div><div><b>台灣蟹</b><strong>500+</strong><small>元／隻</small></div></div></div>""",
    "why": polar("yp", "steamed", "示意照片")
    + """
<div class="chip pop" id="w1" data-in="v11:2.0"><span class="ck">✓</span>產區</div>
<div class="chip pop" id="w2" data-in="v11:2.6"><span class="ck">✓</span>規格</div>
<div class="chip pop" id="w3" data-in="v11:3.2"><span class="ck">✓</span>等級</div>""",
    "guard": """
<div class="kraft pop" data-in="v12:0">管理各有一套</div>
<div class="card gcard pop" id="gL" data-in="v12:1.0"><div class="tt">進口蟹</div>
 <div class="it">核准養殖場</div><div class="it">官方衛生證明</div><div class="it">戴奧辛報告</div><div class="it">逐批查驗<span>不合格退運或銷毀</span></div></div>
<div class="card gcard pop" id="gR" data-in="v12:3.8"><div class="tt">苗栗蟹</div>
 <div class="big">68</div><div class="it">項藥物殘留<span>及戴奧辛檢測</span></div><div class="it">符合才能掛蟹環</div><div class="it">掃碼查來源<span>與檢驗資訊</span></div></div>""",
    "end": polar("ep", "roe", "示意照片")
    + """
<div class="ask1 pop" id="a1" data-in="v13:2.2">產區</div>
<div class="ask1 pop" id="a2" data-in="v13:2.8">公母</div>
<div class="ask1 pop" id="a3" data-in="v13:3.4">實際幾克</div>
<div class="ask1 pop" id="a4" data-in="v13:4.2">檢驗資料</div>
<div class="abs" id="src">資料：旺報 2014・海大《大閘蟹養殖》2012・苗栗縣政府 2026・蘇州市陽澄湖大閘蟹行業協會 2026・澎湃 2026・世界日報 2026・食藥署<br>照片：Wikimedia Commons，非實際販售商品</div>""",
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
        if i < len(SCENES) - 1:
            tl.append(
                f'tl.to("#in-{sid}", {{opacity:0, duration:0.25, ease:"power1.in"}}, {s1 - 0.25:.2f});'
            )
            tl.append(f'tl.set("#in-{sid}", {{opacity:0}}, {s1:.2f});')
        if "polar" in BODY[sid]:
            tl.append(
                f'tl.fromTo("#in-{sid} .polar img", {{scale:1}}, {{scale:1.05, duration:{s1 - s0:.2f}, ease:"none"}}, {s0:.2f});'
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
<title>大閘蟹知識2</title>
<script src="vendor/gsap.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div id="root" data-composition-id="species03" data-start="0" data-duration="{total}" data-fps="24" data-width="1080" data-height="1920">
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
window.__timelines["species03"] = tl;
</script>
</body>
</html>
"""
    open(os.path.join(HERE, "index.html"), "w").write(page)
    print(f"index.html  {total}s  {len(lines)} 句")


if __name__ == "__main__":
    main()
