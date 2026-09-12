#!/usr/bin/env python3
"""從 script.md ＋ scenes.json ＋ 實測語音長度，產生四支 HyperFrames 專案。

  full-wide   完整版 1920×1080   提案、投影用
  full-tall   完整版 1080×1920   手機遞給對方看
  short-wide  精華版 1920×1080
  short-tall  精華版 1080×1920

橫式與直式共用同一份 HTML 與時間軸，版面差異全部在 shared/deck.css 的變數裡。
時間軸依「實際量到的語音長度」排，改稿重跑 gen_voice.py 再跑這支就會重新對齊，
不要手動去改各專案 index.html 的 data-start。
"""
import json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 24

# 節奏參數。提案影片要讓對方有時間消化，留白比社群短片大。
LEAD = 0.8  # 開場前導
GAP_IN = 0.9  # 同一場景內，句與句之間
GAP_SC = 1.0  # 場景與場景之間
TAIL_SC = 0.8  # 場景最後一句講完到場景結束
TITLE = 4.0  # 片頭標題卡
OUTRO = 6.0  # 片尾 CTA

FMT = {"wide": (1920, 1080, "landscape"), "tall": (1080, 1920, "portrait")}


def parse_script(section):
    body = open(f"{HERE}/script.md", encoding="utf-8").read()
    seg = body.split(f"## {section}")[1].split("\n## ")[0]
    return [m.group(1).strip() for m in re.finditer(r"^\d+\. (.+)$", seg, re.M)]


def layout(scenes, timing):
    """算出每個場景、每張字卡、每段旁白的時間點。"""
    t = LEAD + TITLE + GAP_SC
    plan = []
    for sc in scenes:
        start = round(t - 0.9, 2)
        cues = []
        for n in sc["lines"]:
            d = timing[n - 1]["dur"]
            cues.append({"n": n, "at": round(t, 2), "dur": d})
            t += d + GAP_IN
        t -= GAP_IN
        end = t + TAIL_SC
        plan.append({**sc, "start": start, "dur": round(end - start, 2), "cues": cues})
        t = end + GAP_SC
    return plan, round(t - GAP_SC + OUTRO, 2)


ART_BUILD = {
    "phone": "phoneMarkup(7)",
    "bubble": "bubbleMarkup(420, 170, -1, 7)",
    "sheet": "sheetMarkup(7)",
    "mic": "micMarkup(7)",
    "stack": "stackMarkup(4, 6)",
    "nodes": "nodesMarkup(6, 6)",
    "check": "checkMarkup(7)",
}

# 每種圖元的入場。回傳 GSAP 片段，{S}=場景 id、{T}=場景起點。
ART_ANIM = {
    "phone": """tl.fromTo("#{S}-art", {{autoAlpha:0, y:36}}, {{autoAlpha:1, y:0, duration:0.85, ease:"power2.out"}}, {T});""",
    "bubble": """tl.fromTo("#{S}-art", {{autoAlpha:0, scale:0.88, transformOrigin:"50% 50%"}}, {{autoAlpha:1, scale:1, duration:0.7, ease:"back.out(1.6)"}}, {T});
      tl.fromTo("#{S}-art .bd", {{autoAlpha:0.2, y:0}}, {{autoAlpha:1, y:-8, duration:0.4, stagger:{{each:0.16, repeat:5, yoyo:true}}, ease:"sine.inOut"}}, {T}+0.6);""",
    "sheet": """tl.fromTo("#{S}-art", {{autoAlpha:0, y:30}}, {{autoAlpha:1, y:0, duration:0.7, ease:"power2.out"}}, {T});
      tl.to("#{S}-art .sr", {{autoAlpha:0, duration:0.5, stagger:0.28, ease:"power1.in"}}, {T}+1.5);""",
    "mic": """tl.fromTo("#{S}-art", {{autoAlpha:0, scale:0.92, transformOrigin:"50% 50%"}}, {{autoAlpha:1, scale:1, duration:0.7, ease:"power2.out"}}, {T});
      tl.fromTo("#{S}-art .mw", {{autoAlpha:0.15}}, {{autoAlpha:0.95, duration:0.75, stagger:{{each:0.2, repeat:8, yoyo:true}}, ease:"sine.inOut"}}, {T}+0.5);""",
    "stack": """tl.fromTo("#{S}-art", {{autoAlpha:0}}, {{autoAlpha:1, duration:0.5}}, {T});
      tl.fromTo("#{S}-art .sl", {{autoAlpha:0, y:34}}, {{autoAlpha:1, y:0, duration:0.6, stagger:0.32, ease:"power2.out"}}, {T}+0.3);""",
    "nodes": """tl.fromTo("#{S}-art .hub", {{autoAlpha:0, scale:0.4, transformOrigin:"50% 50%"}}, {{autoAlpha:1, scale:1, duration:0.6, ease:"back.out(2)"}}, {T});
      tl.fromTo("#{S}-art .ne", {{autoAlpha:0, scaleX:0.1, scaleY:0.1, transformOrigin:"0% 0%"}}, {{autoAlpha:0.8, scaleX:1, scaleY:1, duration:0.5, stagger:0.13, ease:"power2.out"}}, {T}+0.55);
      tl.fromTo("#{S}-art .nd", {{autoAlpha:0, scale:0.3, transformOrigin:"50% 50%"}}, {{autoAlpha:1, scale:1, duration:0.45, stagger:0.13, ease:"back.out(2)"}}, {T}+0.8);""",
    "check": """tl.fromTo("#{S}-art", {{autoAlpha:0, scale:0.9, transformOrigin:"50% 50%"}}, {{autoAlpha:1, scale:1, duration:0.6, ease:"power2.out"}}, {T});
      tl.to("#{S}-art .ck", {{strokeDashoffset:0, duration:0.9, ease:"power1.inOut"}}, {T}+0.6);""",
    "cards": """tl.fromTo("#{S}-art .card", {{autoAlpha:0, y:40}}, {{autoAlpha:1, y:0, duration:0.7, stagger:0.9, ease:"power2.out"}}, {T});""",
}

DELIVER = [
    ("一", "設定", "一步卡住就整組不動"),
    ("二", "調整", "它的口氣、你這一行的說法"),
    ("三", "教會你用", "第一週就養成習慣"),
]


def scene_html(sc):
    art = ""
    if sc["art"] == "cards":
        items = "".join(
            f'<div class="card"><span class="k">第 {k} 步</span>'
            f'<span class="v">{v}</span><span class="d">{d}</span></div>'
            for k, v, d in DELIVER
        )
        art = f'<div class="art" id="{sc["id"]}-art"><div class="cards">{items}</div></div>'
    elif sc["art"] != "none":
        cls = "art is-gold" if sc["art"] == "check" else "art"
        art = f'<div class="{cls}" id="{sc["id"]}-art"></div>'

    cards = "".join(
        '<div class="stack" id="{}-c{}">{}</div>'.format(
            sc["id"],
            i,
            "".join(f'<span class="line {c["cls"]}">{t}</span>' for t in c["text"]),
        )
        for i, c in enumerate(sc["cards"])
    )

    cardzone = f'            <div class="cardzone">{cards}</div>' if cards else ""

    return f"""      <section id="{sc['id']}" class="clip" data-start="{sc['start']}" data-duration="{sc['dur']}" data-track-index="{sc['idx']}">
        <div class="sin" id="{sc['id']}-in">
          <div class="stage">
{art and '            ' + art}
{cardzone}
          </div>
        </div>
      </section>"""


def scene_js(sc):
    out = []
    t0 = sc["start"] + 0.9
    if sc["art"] in ART_BUILD:
        out.append(
            f'      document.getElementById("{sc["id"]}-art").innerHTML = {ART_BUILD[sc["art"]]};'
        )
    if sc["art"] in ART_ANIM:
        out.append("      " + ART_ANIM[sc["art"]].format(S=sc["id"], T=round(t0, 2)))

    at_of = {c["n"]: c["at"] for c in sc["cues"]}
    for i, c in enumerate(sc["cards"]):
        show = round(at_of[c["at"]] - 0.15, 2)
        out.append(
            f'      tl.fromTo("#{sc["id"]}-c{i}", {{autoAlpha:0, y:32}}, '
            f'{{autoAlpha:1, y:0, duration:0.6, ease:"power2.out"}}, {show});'
        )
        if i + 1 < len(sc["cards"]):
            nxt = round(at_of[sc["cards"][i + 1]["at"]] - 0.55, 2)
            out.append(
                f'      tl.to("#{sc["id"]}-c{i}", {{autoAlpha:0, y:-22, duration:0.45, ease:"power1.in"}}, {nxt});'
            )

    end = round(sc["start"] + sc["dur"], 2)
    out.append(
        f'      tl.to("#{sc["id"]}-in", {{opacity:0, duration:0.4, ease:"power1.in"}}, {round(end - 0.4, 2)});'
    )
    out.append(f'      tl.set("#{sc["id"]}-in", {{opacity:0}}, {end});')
    return "\n".join(out)


def build(which, fmt, plan, total, timing, tag):
    W, H, res = FMT[fmt]
    name = f"{which}-{fmt}"
    d = f"{HERE}/{name}"
    os.makedirs(f"{d}/audio", exist_ok=True)

    for i, sc in enumerate(plan):
        sc["idx"] = i + 2

    audio = "\n".join(
        f'      <audio id="vo-{c["n"]}" data-start="{c["at"]}" '
        f'data-duration="{c["dur"]}" src="audio/s{c["n"]:02d}.mp3"></audio>'
        for sc in plan
        for c in sc["cues"]
    )

    title_end = round(LEAD + TITLE, 2)
    outro_at = round(total - OUTRO, 2)

    html = f"""<!doctype html>
<html lang="zh-Hant" data-resolution="{res}" data-fmt="{fmt}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>AI 導入包 · {'完整版' if which == 'full' else '精華版'}</title>
    <link rel="stylesheet" href="shared/deck.css" />
    <script src="vendor/gsap.min.js"></script>
    <script src="shared/deck.js"></script>
  </head>
  <body>
    <div id="root" data-composition-id="{which}{fmt}" data-start="0" data-duration="{total}"
         data-fps="{FPS}" data-width="{W}" data-height="{H}">
      <div id="bg" class="clip" data-start="0" data-duration="{total}" data-track-index="0"></div>

      <section id="intro" class="clip" data-start="0" data-duration="{title_end}" data-track-index="1">
        <div class="sin" id="intro-in">
          <div class="stage">
            <div class="cardzone">
              <div class="stack" id="intro-c">
                <span class="line l-hook">把老闆腦袋裡的東西</span>
                <span class="line l-hook gold">留下來</span>
              </div>
            </div>
            <div class="tag" id="intro-t">A I 導 入 包</div>
          </div>
        </div>
      </section>

{chr(10).join(scene_html(sc) for sc in plan)}

      <section id="outro" class="clip" data-start="{outro_at}" data-duration="{OUTRO}" data-track-index="{len(plan) + 2}">
        <div class="sin" id="outro-in">
          <div class="stage">
            <div class="cardzone">
              <div class="stack" id="outro-c">
                <span class="line l-hook gold">我們可以聊聊</span>
                <span class="line l-small">鉅鑫管理顧問有限公司</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 品牌標記獨立一層放最上面，不被場景的淡出帶走 -->
      <div id="chrome" class="clip" data-start="0" data-duration="{total}" data-track-index="{len(plan) + 3}"></div>

      <!-- 旁白：Lien 克隆聲音（say.py），時間點由 build.py 依實測長度排 -->
{audio}
    </div>

    <script>
      brandChrome("bg", "chrome");

      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});

      tl.fromTo("#intro-c", {{autoAlpha:0, y:38}}, {{autoAlpha:1, y:0, duration:1.0, ease:"power2.out"}}, 0.3);
      tl.fromTo("#intro-t", {{autoAlpha:0}}, {{autoAlpha:1, duration:0.8}}, 1.1);
      tl.to("#intro-in", {{opacity:0, duration:0.5, ease:"power1.in"}}, {round(title_end - 0.5, 2)});
      tl.set("#intro-in", {{opacity:0}}, {title_end});

{chr(10).join(scene_js(sc) for sc in plan)}

      tl.fromTo("#outro-c", {{autoAlpha:0, y:34}}, {{autoAlpha:1, y:0, duration:0.9, ease:"power2.out"}}, {round(outro_at + 0.4, 2)});

      window.__timelines["{which}{fmt}"] = tl;
    </script>
  </body>
</html>
"""
    open(f"{d}/index.html", "w", encoding="utf-8").write(html)
    json.dump(
        {
            "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
            "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
            "paths": {
                "blocks": "compositions",
                "components": "compositions/components",
                "assets": "assets",
            },
            "media": {"autoProxy": True},
        },
        open(f"{d}/hyperframes.json", "w"),
        indent=2,
    )
    json.dump(
        {"id": name, "name": f"AI 導入包提案 {which} {fmt}"},
        open(f"{d}/meta.json", "w"),
        ensure_ascii=False,
        indent=2,
    )
    json.dump(
        {
            "name": name,
            "private": True,
            "type": "module",
            "scripts": {
                "dev": "npx --yes hyperframes@0.8.30 preview",
                "check": "npx --yes hyperframes@0.8.30 check",
                "render": "npx --yes hyperframes@0.8.30 render",
            },
        },
        open(f"{d}/package.json", "w"),
        indent=2,
    )

    for sub in ("shared", "vendor"):
        shutil.rmtree(f"{d}/{sub}", ignore_errors=True)
        shutil.copytree(f"{HERE}/{sub}", f"{d}/{sub}")
    for f in os.listdir(f"{HERE}/audio/{tag}"):
        if f.endswith(".mp3"):
            shutil.copy(f"{HERE}/audio/{tag}/{f}", f"{d}/audio/{f}")
    return name, total


def main():
    scenes_all = json.load(open(f"{HERE}/scenes.json", encoding="utf-8"))
    for which, section, tag in (
        ("full", "完整版", "full"),
        ("short", "精華版", "short"),
    ):
        tpath = f"{HERE}/audio/{tag}_timing.json"
        if not os.path.exists(tpath):
            print(f"⏭  {which}：還沒有 {tag}_timing.json，先跑 gen_voice.py {tag}")
            continue
        timing = json.load(open(tpath, encoding="utf-8"))
        lines = parse_script(section)
        assert len(timing) == len(
            lines
        ), f"{which} 旁白 {len(timing)} 句對不上腳本 {len(lines)} 句"
        plan, total = layout(json.loads(json.dumps(scenes_all[which])), timing)
        for fmt in ("wide", "tall"):
            name, t = build(
                which, fmt, json.loads(json.dumps(plan)), total, timing, tag
            )
            m, s = divmod(t, 60)
            print(
                f"✅ {name}  {int(m)}:{s:04.1f}  {len(plan)} 場景 / {len(timing)} 句旁白"
            )


if __name__ == "__main__":
    main()
