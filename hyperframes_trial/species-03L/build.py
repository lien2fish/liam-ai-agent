"""大閘蟹長片：買蟹常聽的三句話（16:9 紙感版）：依旁白長度排時間軸，產生 index.html。

旁白與字幕共用 lines.json：[key, 餵 TTS 的字, 字幕]。音檔在 audio/<key>.wav（不進公開 repo）。
data-in="key:比例"＝該句唸到該比例時出現，重配旁白不用改時間。成品再加速 1.2 倍。

事實出處：
- 台兩／市兩、2014 兩岸比較：旺報 2014-09-30（陸蟹 4 兩 200 克；台灣 5 兩「也近 200 克」，實算 187.5）
- 等級草案：江蘇省漁業協會《陽澄湖大閘蟹等級標準》徵求意見稿 2025
- 陽澄湖產量與防偽：蘇州市農業農村局 2026-09-28
- 地理標誌：農業農村部 2021-07-21（2020 農產品地理標誌，516.04 平方公里）；國家知識產權局 2020-09-23（地理標誌保護產品 113 平方公里，排除沿湖改造池塘）
- 防偽戒指：農業部門 2005-09-05
- 苗栗：苗栗縣政府農業處／中央社 2026-10-06
- 進口與 2024 案例：食藥署藥物食品安全週報第 1043 期 2025-09-12
- 2018 案例：中央社 2018-11-08
- 物種：海大《大閘蟹養殖》2012
⛔ 不下價差結論、不比口感、不用項目數排安全高低、不說池塘蟹較差、不虛構掃碼結果、不暗示自家貨產地。
"""

import json
import os
import re
import subprocess
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
GAP = 0.4
LEAD = 0.15
TAIL = 5.0
MEDIA_BOX = "left:80px; top:130px; width:960px; height:540px;"
VIDEO_CREDIT = "中新網 2020・CC BY 3.0"

SCENES = [
    ("hookl", ["l01"]),
    ("hookw", ["l02"]),
    ("hookr", ["l03"]),
    ("three", ["l04", "l05"]),
    ("conv", ["l06", "l07"]),
    ("five", ["l08"]),
    ("four", ["l09"]),
    ("report", ["l10", "l11"]),
    ("ask1", ["l12", "l13"]),
    ("notonly", ["l14"]),
    ("grade", ["l15", "l16", "l17"]),
    ("ch2", ["l18"]),
    ("split", ["l19", "l20", "l21"]),
    ("notfake", ["l22"]),
    ("gi", ["l23", "l24", "l25"]),
    ("ring", ["l26"]),
    ("clasp", ["l27", "l28"]),
    ("ask2", ["l29"]),
    ("ch3", ["l30"]),
    ("species", ["l31"]),
    ("miaoli", ["l32", "l33"]),
    ("imp", ["l34"]),
    ("nocmp", ["l35"]),
    ("y2024", ["l36"]),
    ("y2018", ["l37", "l38", "l39"]),
    ("tagis", ["l40", "l41"]),
    ("price", ["l42", "l43"]),
    ("align", ["l44", "l45"]),
    ("end", ["l46", "l47", "l48", "l49", "l50"]),
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
html, body { width:1920px; height:1080px; overflow:hidden; background:var(--paper); }
body { font-family:"PingFang TC",sans-serif; font-weight:600; color:var(--ink); }
#root { position:relative; width:1920px; height:1080px; overflow:hidden; }
.clip { position:absolute; inset:0; }
#bg { background:radial-gradient(80% 70% at 50% 40%, #f3eee4 0%, var(--paper) 60%, #ddd5c6 100%); }
#head { position:absolute; left:80px; top:54px; font-size:28px; color:var(--dim); letter-spacing:.24em; }
.abs { position:absolute; }
.card { position:absolute; background:var(--card); border-radius:16px; box-shadow:var(--shadow); }
.kraft { position:absolute; background:var(--kraft); color:var(--kraft-ink); font-size:38px; padding:10px 28px; border-radius:6px;
  box-shadow:0 8px 18px rgba(70,52,30,.22); white-space:nowrap; letter-spacing:.06em; z-index:3; }
.seal { position:absolute; color:var(--seal); border:8px solid var(--seal); border-radius:16px; padding:4px 26px;
  font-size:84px; font-weight:900; letter-spacing:.1em; outline:3px solid var(--seal); outline-offset:7px; white-space:nowrap;
  background:rgba(248,245,238,.82); z-index:4; }
.frame { position:absolute; background:#fff; padding:14px; box-shadow:var(--shadow); overflow:hidden; }
.frame img { display:block; width:100%; height:100%; object-fit:cover; }
.fnote { position:absolute; right:26px; top:26px; background:rgba(43,38,33,.74); color:#fff; font-size:24px; padding:4px 14px; border-radius:6px; font-weight:500; z-index:2; }
.fcred { position:absolute; left:26px; bottom:22px; background:rgba(43,38,33,.62); color:#fff; font-size:18px; padding:2px 10px; border-radius:4px; font-weight:400; z-index:2; white-space:nowrap; }
.vid { position:absolute; object-fit:cover; }
.r { left:1080px; width:760px; }
.chip { position:absolute; background:var(--card); border:2px solid var(--line); border-radius:14px; font-size:44px; padding:22px 26px 22px 94px;
  box-shadow:0 8px 18px rgba(70,52,30,.12); white-space:nowrap; }
.chip .ck { position:absolute; left:24px; top:22px; width:50px; height:50px; border-radius:50%; background:var(--teal); color:#fff; font-size:32px; display:flex; align-items:center; justify-content:center; }
.chip .dm { color:var(--dim); font-size:32px; margin-left:14px; }
.nc { padding:30px 40px; }
.nc .h1 { font-size:34px; color:var(--dim); white-space:nowrap; }
.nc .v1 { font-size:62px; font-weight:900; margin-top:12px; white-space:nowrap; }
.nc .v1 i { font-style:normal; color:var(--seal); }
.nc .v1 u { text-decoration:none; color:var(--teal); }
.nc .v2 { font-size:38px; margin-top:12px; color:var(--dim); white-space:nowrap; font-weight:500; }
.sub { position:absolute; left:120px; right:120px; top:820px; display:flex; justify-content:center; align-items:flex-start; }
.sub span { background:rgba(248,245,238,.96); border-radius:12px; padding:14px 30px; font-size:44px; line-height:1.38; text-align:center; box-shadow:0 6px 14px rgba(70,52,30,.12); }
.num { font-family:Menlo,monospace; }

/* 兩台秤 */
.sc { top:150px; width:640px; height:540px; padding:34px; text-align:center; }
.sc .tt { font-size:56px; font-weight:900; margin-bottom:26px; }
.sc .lcd { background:#2f3b37; border-radius:14px; height:230px; display:flex; align-items:flex-end; justify-content:center; padding-bottom:32px; color:#9fe0c8; font-family:Menlo,monospace; font-weight:700; }
.sc .lcd b { font-size:128px; line-height:1; } .sc .lcd i { font-style:normal; font-size:54px; margin-left:12px; }
.sc .plate { margin:44px auto 0; width:420px; height:22px; border-radius:11px; background:var(--line); }
#hdiff { left:0; right:0; top:372px; text-align:center; z-index:4; }
#hdiff span { display:inline-block; background:var(--seal); color:#fff; font-size:48px; font-weight:900; padding:10px 22px; border-radius:8px; transform:rotate(-2deg); }

/* 三句話 */
.say { top:210px; width:540px; height:400px; display:flex; align-items:center; justify-content:center; text-align:center; font-size:60px; font-weight:900; line-height:1.3; padding:30px; }

/* 換算表 */
#ctable { left:260px; top:130px; width:1400px; height:600px; padding:30px 60px; }
.tr { display:flex; align-items:center; height:230px; border-bottom:2px solid var(--line); }
.tr.h { height:90px; font-size:40px; color:var(--dim); }
.tr .k { width:260px; text-align:center; font-size:62px; font-weight:900; color:var(--kraft-ink); }
.tr .c { flex:1; text-align:center; }
.tr .c b { display:block; font-size:84px; font-weight:900; font-family:Menlo,monospace; }
.tr .c span { font-size:36px; color:var(--dim); }

/* 長條 */
.bars { left:160px; top:150px; width:1600px; height:560px; padding:44px 60px; }
.bl { font-size:42px; font-weight:800; margin-top:30px; white-space:nowrap; }
.bt { height:96px; border-radius:10px; margin-top:12px; display:flex; align-items:center; padding-left:26px; color:#fff; font-size:50px; font-weight:900; font-family:Menlo,monospace; white-space:nowrap; }

/* 章節 */
.chap { left:1080px; top:230px; width:760px; height:340px; padding:50px 44px; text-align:center; }
.chap .n { font-size:40px; color:var(--dim); } .chap .t { font-size:70px; font-weight:900; margin-top:28px; color:var(--seal); white-space:nowrap; }

/* 問題 */
.ask { position:absolute; background:var(--sticky); box-shadow:0 10px 20px rgba(70,52,30,.18); font-size:48px; font-weight:900; padding:30px 34px; text-align:center; white-space:nowrap; }
.row { position:absolute; left:160px; width:1600px; height:128px; display:flex; align-items:center; font-size:48px; }
.row .a { width:600px; color:var(--dim); font-weight:600; white-space:nowrap; }
.row .b { font-weight:900; color:var(--seal); white-space:nowrap; }
#src { left:80px; right:80px; top:952px; text-align:center; font-size:21px; color:var(--dim); font-weight:400; line-height:1.45; }
#endcard { z-index:9; background:var(--paper); }
#endcard .box { position:absolute; left:160px; right:160px; top:120px; font-size:30px; line-height:1.72; color:var(--ink); font-weight:500; }
#endcard h3 { font-size:38px; margin:18px 0 6px; color:var(--kraft-ink); }
"""


def credit(key):
    c = CREDITS[key]
    return f'Photo: {c["artist"]} / {c["license"]}'


def photo(key, note="示意照片", box=MEDIA_BOX):
    return (
        f'<div class="frame pop" style="{box}" data-in="{{first}}:0"><img src="assets/{key}.jpg" alt="" />'
        f'<div class="fnote">{note}</div><div class="fcred">{credit(key)}</div></div>'
    )


def clip(key, note):
    """影片底下墊最後一格防露底；片段長度由 cut_clips.py 保證超過旁白，不會停住。"""
    return (
        f'<div class="frame pop" style="{MEDIA_BOX}" data-in="{{first}}:0" data-clip="{key}">'
        f'<img src="assets/{key}_end.jpg" alt="" /></div>'
    )


def chip(top, at, text, dim=""):
    d = f'<span class="dm">{dim}</span>' if dim else ""
    return f'<div class="chip r pop" style="top:{top}px" data-in="{at}"><span class="ck">✓</span>{text}{d}</div>'


def nc(top, height, at, h1, v1, v2="", cls="r", extra=""):
    v = f'<div class="v2">{v2}</div>' if v2 else ""
    return (
        f'<div class="card nc pop {cls}" style="top:{top}px; height:{height}px; {extra}" data-in="{at}">'
        f'<div class="h1">{h1}</div><div class="v1">{v1}</div>{v}</div>'
    )


def chap(n, t):
    return f'<div class="card chap pop" data-in="{{first}}:0"><div class="n">{n}</div><div class="t">{t}</div></div>'


def bar(label, grams, full, color, at):
    return (
        f'<div class="pop" data-in="{at}"><div class="bl">{label}</div>'
        f'<div class="bt" style="width:{grams / full * 100:.1f}%; background:var(--{color})">{grams:g} 克</div></div>'
    )


BODY = {
    "hookw": """
<div class="abs" id="hdiff"><span>差 62.5 克</span></div>
<div class="card sc" style="left:230px"><div class="tt">大陸五兩</div><div class="lcd"><b>250</b><i>g</i></div><div class="plate"></div></div>
<div class="card sc" style="left:1050px"><div class="tt">台灣五兩</div><div class="lcd"><b>187.5</b><i>g</i></div><div class="plate"></div></div>""",
    "hookl": clip("v_net", "2020 開捕資料畫面")
    + nc(190, 240, "l01:0.1", "2026 官方預估・陽澄湖大閘蟹", "<i>八成多</i>", "不是養在湖裡"),
    "hookr": clip("v_tags", "2020 開捕資料畫面")
    + nc(190, 240, "l03:0.1", "蟹環", "不等於", "一句安全保證"),
    "three": """
<div class="card say pop" style="left:90px" data-in="l04:0">這隻<br>五兩</div>
<div class="card say pop" style="left:690px" data-in="l04:0.2">這是<br>陽澄湖的</div>
<div class="card say pop" style="left:1290px" data-in="l04:0.4">有蟹環<br>很安全</div>""",
    "conv": """
<div class="card pop" id="ctable" data-in="l06:0">
 <div class="tr h"><div class="k"></div><div class="c">台兩</div><div class="c">大陸市兩</div></div>
 <div class="tr"><div class="k">一斤</div><div class="c"><b>600</b><span>克（16 兩）</span></div><div class="c"><b>500</b><span>克（10 兩）</span></div></div>
 <div class="tr"><div class="k">一兩</div><div class="c"><b>37.5</b><span>克</span></div><div class="c"><b>50</b><span>克</span></div></div>
</div>""",
    "five": '<div class="card bars pop" data-in="l08:0"><div class="nc"><div class="h1">同樣五兩</div></div>'
    + bar("台灣五兩", 187.5, 300, "teal", "l08:0.15")
    + bar("大陸五兩", 250, 300, "seal", "l08:0.55")
    + "</div>",
    "four": photo("yc_large")
    + nc(190, 240, "l09:0.1", "大陸四兩", "<i>200</i> 克", "")
    + nc(450, 220, "l09:0.55", "換成台兩", "<u>5.33</u> 兩", ""),
    "report": '<div class="card bars pop" data-in="l10:0"><div class="nc"><div class="h1">2014 年報導的比較</div></div>'
    + bar("陸蟹四兩", 200, 300, "seal", "l10:0.3")
    + bar("台灣五兩（報導寫「也近 200 克」）", 187.5, 300, "teal", "l10:0.65")
    + "</div>",
    "ask1": clip("v_ask1", "2020 開捕資料畫面")
    + nc(150, 200, "l12:0.1", "產地在大陸", "不一定用市兩")
    + chip(390, "l13:0.25", "問幾克")
    + chip(510, "l13:0.6", "每隻至少，還是範圍"),
    "notonly": photo("cut_half")
    + '<div class="seal stamp" style="left:1200px; top:280px; transform:rotate(-5deg)" data-in="l14:0.45">不一定</div>',
    "grade": photo("roe")
    + nc(
        130,
        250,
        "l15:0.5",
        "陽澄湖等級標準（2025 徵求意見稿）",
        "A：公 <i>200</i>／母 <i>175</i>",
        "克以上",
    )
    + chip(410, "l16:0.1", "這是草案")
    + chip(530, "l16:0.65", "另外看肥滿度"),
    "ch2": photo("yc_scenery", "陽澄湖") + chap("第二句", "這是陽澄湖的"),
    "split": clip("v_split", "2020 開捕資料畫面")
    + nc(130, 190, "l19:0.2", "2026 官方預估", "約 1.01 萬噸")
    + nc(335, 190, "l20:0.15", "湖區圍網", "<u>約 1600 噸</u>")
    + nc(540, 190, "l20:0.6", "沿湖高標準池塘", "<i>約 8500 噸</i>"),
    "notfake": photo("yc_cooked")
    + '<div class="seal stamp" style="left:1110px; top:270px; transform:rotate(-4deg); font-size:68px" data-in="l22:0.2">池塘≠冒牌</div>',
    "gi": nc(
        230,
        300,
        "l23:0",
        "農產品地理標誌（2020 登記）",
        "<u>湖區＋沿岸</u>",
        "指定區域，共 516 平方公里",
        "",
        "left:120px; width:800px;",
    )
    + nc(
        230,
        300,
        "l24:0.1",
        "地理標誌保護產品（資料 2020）",
        "<i>113 平方公里水域</i>",
        "沿湖改造池塘不在範圍內",
        "",
        "left:1000px; width:800px;",
    ),
    "ring": photo("mini")
    + nc(250, 220, "l26:0.45", "農業部門 2005 年資料：前一年", "防偽戒指滿天飛"),
    "clasp": clip("v_clasp", "2020 開捕資料畫面")
    + nc(120, 195, "l27:0.05", "今年官方公告", "一蟹一扣・一箱一貼")
    + chip(330, "l27:0.45", "養殖水域")
    + chip(445, "l27:0.65", "苗種來源")
    + chip(560, "l27:0.85", "上市時間"),
    "ask2": photo("yc_scenery", "陽澄湖")
    + chip(150, "l29:0.1", "湖裡還是池塘")
    + chip(310, "l29:0.4", "用哪一種標示")
    + chip(470, "l29:0.7", "資料對不對得上"),
    "ch3": clip("v_ch3", "2020 開捕資料畫面") + chap("第三句", "有蟹環，很安全"),
    "species": photo("yc_raw")
    + nc(180, 240, "l31:0.3", "台灣養的＝大陸的", "中華絨螯蟹")
    + nc(440, 220, "l31:0.65", "台灣原生毛蟹", "日本絨螯蟹等"),
    "miaoli": photo("tied_red")
    + nc(130, 250, "l32:0.15", "苗栗縣府・2026", "<u>68</u> 項檢測", "藥物殘留及戴奧辛")
    + chip(410, "l32:0.7", "符合才掛蟹環")
    + chip(530, "l33:0.1", "查養殖戶、來源、檢驗"),
    "imp": photo("steamed")
    + chip(130, "l34:0.1", "准許輸台的養殖場")
    + chip(250, "l34:0.3", "逐批查核、抽樣檢驗")
    + nc(
        370,
        300,
        "l34:0.55",
        "動物用藥、重金屬、戴奧辛等",
        "<i>16</i> 項",
        "合格才能上市",
    ),
    "nocmp": """
<div class="card pop say" style="left:260px; width:560px" data-in="l35:0"><span class="num" style="font-size:150px; color:var(--teal)">68</span></div>
<div class="card pop say" style="left:1100px; width:560px" data-in="l35:0"><span class="num" style="font-size:150px; color:var(--seal)">16</span></div>
<div class="seal stamp" style="left:740px; top:310px; transform:rotate(-6deg)" data-in="l35:0.3">不要比</div>""",
    "y2024": nc(
        230,
        300,
        "l36:0.2",
        "食藥署：2024 年輸入 31 批",
        "<i>1 批</i>・14.6 噸",
        "戴奧辛及多氯聯苯超標，全數銷毀",
        "",
        "left:360px; width:1200px; text-align:center;",
    ),
    "y2018": """
<div class="card nc pop" style="left:120px; top:230px; width:800px; height:300px;" data-in="l37:0.3"><div class="h1">2018 年</div><div class="v1">中國進口蟹</div><div class="v2">進口後曾先放在苗栗</div></div>
<div class="card nc pop" style="left:1000px; top:230px; width:800px; height:300px;" data-in="l38:0.2"><div class="h1">衛福部長在立法院澄清</div><div class="v1"><u>不是苗栗生產</u></div><div class="v2">放在哪裡不等於產地</div></div>""",
    "tagis": photo("yc_large")
    + chip(150, "l40:0.45", "誰發的")
    + chip(290, "l40:0.7", "連到哪個系統")
    + chip(430, "l41:0.2", "實際重量要自己秤"),
    "price": photo("steamed")
    + '<div class="seal stamp" style="left:1120px; top:280px; transform:rotate(-4deg); font-size:70px" data-in="l43:0.5">不下結論</div>',
    "align": """
<div class="ask pop" style="left:150px; top:200px; transform:rotate(-1deg)" data-in="l44:0.2">克數</div>
<div class="ask pop" style="left:550px; top:200px; transform:rotate(1deg)" data-in="l44:0.35">公母</div>
<div class="ask pop" style="left:790px; top:200px; transform:rotate(-1deg)" data-in="l44:0.5">產區</div>
<div class="ask pop" style="left:1030px; top:200px; transform:rotate(1deg)" data-in="l44:0.62">通路</div>
<div class="ask pop" style="left:1270px; top:200px; transform:rotate(-1deg)" data-in="l44:0.78">時間</div>
<div class="card nc pop" style="left:460px; top:430px; width:1000px; height:210px; text-align:center" data-in="l45:0"><div class="v1">對齊之前，都只是印象</div></div>""",
    "end": """
<div class="row pop" style="top:170px" data-in="l47:0"><div class="a">這隻五兩</div><div class="b">實際幾克？</div></div>
<div class="row pop" style="top:330px" data-in="l48:0"><div class="a">這是陽澄湖的</div><div class="b">養在哪裡？資料對得上嗎？</div></div>
<div class="row pop" style="top:490px" data-in="l49:0"><div class="a">有蟹環，很安全</div><div class="b">誰發的？查得到什麼？</div></div>""",
}

END_CARD = """<div class="box">
<h3>資料</h3>蘇州市農業農村局 2026・農業農村部 2005、2021・國家知識產權局 2020・江蘇省漁業協會 2025 徵求意見稿・苗栗縣政府農業處 2026・中央社 2018、2026・食藥署 2025・旺報 2014・海大《大閘蟹養殖》2012
<h3>影片</h3>中國新聞網「2020 蘇州陽澄湖大閘蟹開捕」，CC BY 3.0，經 Wikimedia Commons；已剪輯、去除聲音
<h3>照片（Wikimedia Commons，非實際販售商品）</h3>Fumikas Sagisavas (CC0)・ProjectManhattan (CC0)・Makecat (CC BY-SA 3.0)・Walter Grassroot (CC BY-SA 3.0)・Jpatokal (CC BY-SA 4.0)・Kentaro Iemoto (CC BY-SA 2.0)
</div>"""


def dur(key):
    with wave.open(os.path.join(HERE, "audio", f"{key}.wav")) as w:
        return w.getnframes() / w.getframerate()


def clip_len(key):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
         os.path.join(HERE, "assets", f"{key}.mp4")],
        capture_output=True, text=True,
    ).stdout  # fmt: skip
    return float(out)


def main():
    lines = {k: sub for k, _, sub in json.load(open(os.path.join(HERE, "lines.json")))}
    t, starts, ends, durs, audio, scene_t = 0.0, {}, {}, {}, [], []
    for _, keys in SCENES:
        scene_t.append(t)
        for k in keys:
            durs[k] = d = dur(k)
            starts[k], ends[k] = t, t + LEAD + d
            audio.append(
                f'<audio id="a-{k}" data-start="{t + LEAD:.2f}" data-duration="{d:.2f}" src="audio/{k}.wav"></audio>'
            )
            t += LEAD + d + GAP
    speech_end = t - GAP
    total = round(speech_end + TAIL, 2)
    scene_t.append(speech_end + 0.6)

    html, tl, videos, n = [], [], [], 0
    for i, (sid, keys) in enumerate(SCENES):
        s0, s1 = scene_t[i], scene_t[i + 1]
        body = BODY[sid].replace("{first}", keys[0])

        def tag(m):
            nonlocal n
            n += 1
            k, frac = m.group(2).split(":")
            at = starts[k] + float(frac) * durs[k]
            sel = f'[data-anim=\\"{n}\\"]'
            if at < 0.2:
                pass
            elif "stamp" in m.group(1):
                tl.append(
                    f'tl.fromTo("{sel}", {{autoAlpha:0, scale:1.7}}, {{autoAlpha:1, scale:1, duration:0.35, ease:"power3.in"}}, {at:.2f});'
                )
            else:
                tl.append(
                    f'tl.fromTo("{sel}", {{autoAlpha:0, y:24}}, {{autoAlpha:1, y:0, duration:0.45, ease:"power2.out"}}, {at:.2f});'
                )
            return f'{m.group(1)}data-anim="{n}"'

        body = re.sub(r'(<\w+[^>]*?)data-in="([^"]+)"', tag, body)
        for key in re.findall(r'data-clip="(\w+)"', body):
            length = clip_len(key)
            videos.append(
                f'<video id="vid-{sid}" class="vid" style="left:94px; top:144px; width:932px; height:512px" src="assets/{key}.mp4" muted playsinline '
                f'data-start="{s0:.2f}" data-duration="{min(length, s1 - s0):.2f}" data-track-index="{100 + i}"></video>'
            )
            videos.append(
                f'<div class="clip" data-start="{s0:.2f}" data-duration="{s1 - s0 - 0.22:.2f}" data-track-index="{130 + i}">'
                f'<div class="fnote" style="left:auto; right:906px; top:156px">2020 開捕資料畫面</div>'
                f'<div class="fcred" style="left:106px; bottom:auto; top:616px">{VIDEO_CREDIT}</div></div>'
            )
        html.append(
            f'<section id="sc-{sid}" class="clip" data-start="{s0:.2f}" data-duration="{s1 - s0:.2f}" data-track-index="{i + 2}">'
            f'<div class="clip" id="in-{sid}">{body}</div></section>'
        )
        tl.append(
            f'tl.to("#in-{sid}", {{opacity:0, duration:0.22, ease:"power1.in"}}, {s1 - 0.22:.2f});'
        )
        tl.append(f'tl.set("#in-{sid}", {{opacity:0}}, {s1:.2f});')
        if 'class="frame' in BODY[sid] and "data-clip" not in body:
            tl.append(
                f'tl.fromTo("#in-{sid} .frame img", {{scale:1}}, {{scale:1.05, duration:{s1 - s0:.2f}, ease:"none"}}, {s0:.2f});'
            )

    subs = [
        f'<div class="sub clip" data-start="{starts[k]:.2f}" data-duration="{ends[k] - starts[k] + GAP:.2f}" '
        f'data-track-index="60"><span>{sub}</span></div>'
        for k, sub in lines.items()
    ]
    nl = "\n"
    page = f"""<!doctype html>
<html lang="zh-Hant" data-resolution="landscape">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1920, height=1080" />
<title>買蟹常聽的三句話</title>
<script src="vendor/gsap.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div id="root" data-composition-id="species03l" data-start="0" data-duration="{total}" data-fps="24" data-width="1920" data-height="1080">
<div id="bg" class="clip" data-start="0" data-duration="{total}" data-track-index="0"></div>
<div class="clip" data-start="0" data-duration="{total}" data-track-index="1"><div id="head">連老闆・產地到餐桌</div></div>
{nl.join(html)}
{nl.join(videos)}
<div id="endcard" class="clip" data-start="{speech_end + 0.6:.2f}" data-duration="{total - speech_end - 0.6:.2f}" data-track-index="90">{END_CARD}</div>
{nl.join(subs)}
{nl.join(audio)}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{nl.join(tl)}
window.__timelines["species03l"] = tl;
</script>
</body>
</html>
"""
    open(os.path.join(HERE, "index.html"), "w").write(page)
    print(f"index.html  {total}s  {len(lines)} 句  {len(videos)} 段影片")


if __name__ == "__main__":
    main()
