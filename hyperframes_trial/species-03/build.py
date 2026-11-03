"""大閘蟹知識 2：為什麼大家都愛陽澄湖（紙感版）：依旁白長度排時間軸，產生 index.html。

旁白與字幕共用 lines.json：[key, 餵 TTS 的字, 字幕]。音檔在 audio/<key>.wav（不進公開 repo）。

事實出處：
- 2026 產量 1.01 萬噸（圍網約 1600、沿湖高標準池塘約 8500）、續用一蟹一扣、掃碼內容：蘇州市農業農村局 2026-09-28；蘇州工業園區陽澄湖半島度假區同日
- 全國 2026 有望破百萬噸（研究人員估）：澎湃 2026-10、世界日報 2026-10-28
- 環境與硬底說法：米其林指南 2017-10；香港01 2024-10（劉健威）；CSM 2006。屬見聞，旁白標「說法」，不當生物學因果
- 2005 首個活體地理標誌：農業農村部 2021-07-21；同年原產地域保護 113 平方公里、前一年防偽戒指滿天飛：農業農村部 2005-09-05
- 2020 農產品地理標誌含沿湖區域（516.04 平方公里）：農業農村部 2021-07-21；故池塘不等於假貨
⛔ 沒有消費者調查，「大家都愛」只當提問。不說池塘蟹較差、不比口感、不用南京蟹王推論陽澄湖輸、不暗示自家貨產地。
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
    ("ask", ["y01"]),
    ("ratio", ["y02"]),
    ("env", ["y03"]),
    ("claw", ["y04"]),
    ("brand", ["y05", "y06"]),
    ("scan", ["y07"]),
    ("pond", ["y08"]),
    ("why", ["y09"]),
    ("end", ["y10"]),
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

/* 開場 */
#ap { left:150px; top:190px; transform:rotate(-2deg); } #ap img { width:780px; height:560px; }
#qc { left:80px; top:910px; width:920px; height:380px; padding:56px 40px; text-align:center; }
#qc .q1 { font-size:54px; color:var(--dim); } #qc .q2 { font-size:82px; font-weight:900; margin-top:28px; white-space:nowrap; }
#qc .q2 i { font-style:normal; color:var(--seal); }

/* 比例 */
#rA { left:80px; top:260px; width:920px; height:300px; padding:48px 56px; }
#rA .h1 { font-size:44px; color:var(--dim); } #rA .big { font-size:104px; font-weight:900; color:var(--seal); margin-top:16px; white-space:nowrap; }
#ring { left:80px; top:610px; width:920px; height:660px; padding:44px 50px; display:flex; flex-direction:column; align-items:center; }
#ring svg { width:340px; height:340px; flex:none; }
#ring b { font-size:88px; font-weight:900; color:var(--seal); margin-top:20px; white-space:nowrap; }
#ring span { font-size:46px; margin-top:6px; white-space:nowrap; }

/* 環境 */
#ep1 { left:120px; top:190px; transform:rotate(-1.5deg); } #ep1 img { width:840px; height:540px; }
#c1 { top:870px; } #c2 { top:1010px; } #c3 { top:1150px; }

/* 說法 */
#cp { left:150px; top:190px; transform:rotate(1.5deg); } #cp img { width:780px; height:600px; }
#clawseal { left:230px; top:930px; transform:rotate(-5deg); }
#clawtx { left:0; right:0; top:1190px; text-align:center; font-size:56px; font-weight:800; white-space:nowrap; }

/* 招牌 */
#bp { left:150px; top:190px; transform:rotate(-1.5deg); } #bp img { width:780px; height:420px; }
.bcard { left:80px; width:920px; padding:36px 48px; }
#b1 { top:730px; height:270px; } #b2 { top:1030px; height:290px; }
.bcard .h1 { font-size:40px; color:var(--dim); } .bcard .v1 { font-size:62px; font-weight:900; margin-top:18px; white-space:nowrap; }
.bcard .v1 i { font-style:normal; color:var(--seal); }

/* 掃碼 */
#sp { left:150px; top:190px; transform:rotate(1.5deg); } #sp img { width:780px; height:440px; }
#scantt { left:80px; top:760px; width:920px; text-align:center; font-size:70px; font-weight:900; color:var(--seal); white-space:nowrap; }
#s1 { top:880px; } #s2 { top:1020px; } #s3 { top:1160px; }

/* 湖區與池塘 */
#pcard { left:80px; top:320px; width:920px; height:900px; padding:70px 50px; }
#pcard .h1 { font-size:46px; color:var(--dim); }
#pbar { display:flex; height:170px; border-radius:14px; overflow:hidden; margin:50px 0 70px; }
#pbar .lk { width:15.8%; background:var(--teal); } #pbar .pd { flex:1; background:var(--roe); }
.prow { font-size:62px; font-weight:900; margin-top:50px; }
.prow i { display:inline-block; width:34px; height:34px; border-radius:50%; margin-right:18px; }
.prow em { display:block; font-style:normal; font-size:50px; font-weight:700; color:var(--dim); margin:12px 0 0 52px; }

/* 收束 */
#yp { left:150px; top:190px; transform:rotate(-1.5deg); } #yp img { width:780px; height:600px; }
#w1 { top:950px; } #w2 { top:1100px; }

/* 結尾 */
#ep { left:190px; top:190px; transform:rotate(-2deg); } #ep img { width:700px; height:560px; }
.ask1 { position:absolute; width:440px; background:var(--sticky); box-shadow:0 10px 20px rgba(70,52,30,.18); font-size:54px; font-weight:900; padding:26px 0; text-align:center; white-space:nowrap; }
#a1 { left:80px; top:870px; transform:rotate(-1deg); } #a2 { left:560px; top:870px; transform:rotate(1deg); }
#a3 { left:320px; top:1030px; transform:rotate(1deg); }
#src { left:30px; right:30px; top:1720px; text-align:center; font-size:21px; color:var(--dim); font-weight:400; line-height:1.5; }
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
    "ask": polar("ap", "yc_large", "示意照片")
    + """
<div class="card pop" id="qc" data-in="y01:0"><div class="q1">產地那麼多</div><div class="q2">為什麼都愛<i>陽澄湖</i>？</div></div>""",
    "ratio": """
<div class="card pop" id="rA" data-in="y02:0"><div class="h1">全大陸・2026 研究人員估計</div><div class="big">可能破 100 萬噸</div></div>
<div class="card pop" id="ring" data-in="y02:2.6">
 <svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="none" stroke="#cfc6b6" stroke-width="16"/>
 <circle cx="50" cy="50" r="40" fill="none" stroke="#b5322a" stroke-width="16" stroke-dasharray="2.5 251" transform="rotate(-90 50 50)"/></svg>
 <b>約 1%</b><span>陽澄湖預估 1.01 萬噸</span>
</div>""",
    "env": polar("ep1", "yc_scenery", "陽澄湖")
    + """
<div class="chip pop" id="c1" data-in="y03:2.0"><span class="ck">✓</span>水淺</div>
<div class="chip pop" id="c2" data-in="y03:2.8"><span class="ck">✓</span>陽光照得到湖底</div>
<div class="chip pop" id="c3" data-in="y03:4.2"><span class="ck">✓</span>水草生長<span class="dm">常見說法</span></div>""",
    "claw": polar("cp", "yc_raw", "示意照片")
    + """
<div class="seal stamp" id="clawseal" data-in="y04:0.3">一種說法</div>
<div class="abs pop" id="clawtx" data-in="y04:1.8">湖底硬・水流急・蟹爪有力</div>""",
    "brand": polar("bp", "mini", "示意照片")
    + """
<div class="card bcard pop" id="b1" data-in="y05:1.0"><div class="h1">2005 年</div><div class="v1">全國第一個<i>活體地理標誌</i></div></div>
<div class="card bcard pop" id="b2" data-in="y06:1.6"><div class="h1">農業部門 2005 年資料</div><div class="v1">前一年<i>防偽戒指滿天飛</i></div></div>""",
    "scan": polar("sp", "yc_cooked", "示意照片")
    + """
<div class="abs pop" id="scantt" data-in="y07:0">一蟹一扣・掃碼可查</div>
<div class="chip pop" id="s1" data-in="y07:2.0"><span class="ck">✓</span>養殖水域</div>
<div class="chip pop" id="s2" data-in="y07:3.0"><span class="ck">✓</span>苗種來源</div>
<div class="chip pop" id="s3" data-in="y07:4.0"><span class="ck">✓</span>上市時間</div>""",
    "pond": """
<div class="kraft pop" data-in="y08:0">招牌不代表全在湖裡</div>
<div class="card pop" id="pcard" data-in="y08:0.6"><div class="h1">2026 官方預估產量 1.01 萬噸</div>
 <div id="pbar"><div class="lk"></div><div class="pd"></div></div>
 <div class="prow"><i style="background:var(--teal)"></i>湖區圍網<em>約 1600 噸・16%</em></div>
 <div class="prow"><i style="background:var(--roe)"></i>沿湖高標準池塘<em>約 8500 噸・84%</em></div>
</div>""",
    "why": polar("yp", "steamed", "示意照片")
    + """
<div class="chip pop" id="w1" data-in="y09:0.4"><span class="ck">✓</span>環境的說法</div>
<div class="chip pop" id="w2" data-in="y09:1.6"><span class="ck">✓</span>長年累積的招牌</div>""",
    "end": polar("ep", "roe", "示意照片")
    + """
<div class="ask1 pop" id="a1" data-in="y10:2.4">湖裡還是池塘</div>
<div class="ask1 pop" id="a2" data-in="y10:3.8">掃一掃查到什麼</div>
<div class="ask1 pop" id="a3" data-in="y10:5.0">單隻實際幾克</div>
<div class="abs" id="src">資料：蘇州市農業農村局 2026・農業農村部 2005、2021・澎湃 2026・世界日報 2026・米其林指南 2017・香港01 2024<br>照片：Wikimedia Commons，非實際販售商品</div>""",
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
<title>為什麼都愛陽澄湖</title>
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
