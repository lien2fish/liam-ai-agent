# -*- coding: utf-8 -*-
"""IG 每日發文的「解說動畫」版本——插圖當主角，逐句旁白＋字幕。

跟 card_video.py 的差別：
  card_video  ＝ 把現有那張卡動起來（安靜、克制、無旁白）
  explainer   ＝ 插圖放大當主角、鏡頭緩推、逐句字幕、**有旁白**

刻意不做遮罩：底是米色紙、字是深藍，先天就清楚。疊遮罩只會讓它變濁。

⚠️ 這條路只適合「講一個現象」的題目。**辨別型題目（分清楚魷魚／中卷／花枝／軟絲
   這種）不要用**——gpt-image 分不出頭足類的鰭形差異，教辨別卻配錯插圖，
   比沒有插圖更糟，而且直接踩到產地真實性紅線。

    python3 instagram/explainer_video.py out.mp4          # 走真的產線做一支
    python3 instagram/explainer_video.py out.mp4 --keep   # 保留中間檔好檢查
"""
import asyncio
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 24
VOICE = os.environ.get("IG_VOICE", "zh-TW-HsiaoChenNeural")
RATE = os.environ.get("IG_VOICE_RATE", "-4%")  # 稍慢一點，海鮮知識要聽得進去

CREAM = (243, 238, 226)
INK = (45, 65, 105)
GOLD = (176, 148, 96)
MUTED = (130, 112, 84)

BASE = os.path.dirname(os.path.abspath(__file__))
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
LOGO = os.path.join(BASE, "logo.png")

PAD = 96  # 左右安全邊
ILLUS_TOP, ILLUS_H = 330, 980  # 插圖區
CAP_TOP = 1420  # 字幕區起點


def f(size):
    return ImageFont.truetype(FONT, size)


CLOSERS = "。？！，、；：）」』"


def wrap(draw, text, font, max_w):
    """逐字斷行。標點不落單——句尾的「。」被擠到下一行看起來像沒排版。"""
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) <= max_w:
            cur += ch
        elif ch in CLOSERS and cur:
            cur += ch  # 收尾標點寧可讓該行稍微超出，也不要自己佔一行
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def cutout(im):
    """去掉接近白的背景，裁到主體。與 generate_post 同一套做法。"""
    import numpy as np

    a = np.array(im.convert("RGBA"), dtype=np.float32)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    a[:, :, 3] = np.where(
        (r > 228) & (g > 228) & (b > 228) & (abs(r - g) < 25), 0, a[:, :, 3]
    )
    out = Image.fromarray(a.astype("uint8"))
    return out.crop(out.getbbox() or (0, 0, im.width, im.height))


def base_canvas(title_zh, title_en, today):
    """不會變動的底：米色紙、頁首、金線、logo。每一格都疊在這上面。"""
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    d.text((PAD, 118), "今日海鮮小知識", font=f(46), fill=MUTED)
    d.text((PAD, 186), f"{today}　|　{title_zh}", font=f(64), fill=INK)
    d.text((PAD, 262), f"（{title_en}）", font=f(34), fill=MUTED)
    d.line([(PAD, 1360), (W - PAD, 1360)], fill=GOLD, width=3)
    try:
        lg = Image.open(LOGO).convert("RGBA")
        h = 74
        lg = lg.resize((int(lg.width * h / lg.height), h), Image.LANCZOS)
        im.paste(lg, (PAD, H - 150), lg)
    except Exception:
        pass
    d.text(
        (W - PAD - d.textlength("鉅鑫 · 龜吼現流", font=f(32)), H - 130),
        "鉅鑫 · 龜吼現流",
        font=f(32),
        fill=MUTED,
    )
    return im


def frame(canvas, illus, zoom, caption, cap_font, bleed):
    """一格＝底 ＋ 插圖 ＋ 目前這句字幕。

    bleed=True：插圖是完整場景（gpt-image 常常不理會「白底」的指示），
    就滿版裁切填滿插圖區——不然會是一塊硬邊矩形浮在米色紙上，像沒做完。
    bleed=False：插圖真的去得掉背景，維持置中留白，比較克制。
    """
    im = canvas.copy()
    if bleed:
        # cover：先按較大的邊縮放再置中裁切，並隨 zoom 緩推
        r = max(W / illus.width, ILLUS_H / illus.height) * zoom
        w, h = int(illus.width * r), int(illus.height * r)
        sm = illus.resize((w, h), Image.LANCZOS)
        im.paste(
            sm.crop(
                (
                    (w - W) // 2,
                    (h - ILLUS_H) // 2,
                    (w - W) // 2 + W,
                    (h - ILLUS_H) // 2 + ILLUS_H,
                )
            ),
            (0, ILLUS_TOP),
        )
    else:
        box = int(min(ILLUS_H, 820) * zoom)
        ratio = min(box / illus.width, box / illus.height)
        w, h = max(1, int(illus.width * ratio)), max(1, int(illus.height * ratio))
        sm = illus.convert("RGBA").resize((w, h), Image.LANCZOS)
        im.paste(sm, ((W - w) // 2, ILLUS_TOP + (ILLUS_H - h) // 2), sm)
    if caption:
        d = ImageDraw.Draw(im)
        lines = wrap(d, caption, cap_font, W - PAD * 2)
        lh = int(cap_font.size * 1.5)
        y = CAP_TOP + max(0, (330 - len(lines) * lh) // 2)
        for i, ln in enumerate(lines):
            d.text((PAD, y + i * lh), ln, font=cap_font, fill=INK)
    return im


async def _speak(text, path):
    import edge_tts

    for attempt in range(6):  # 雲端與本機都偶爾 NoAudioReceived，要重試
        try:
            await edge_tts.Communicate(text, VOICE, rate=RATE).save(path)
            if os.path.getsize(path) > 800:
                return
        except Exception as e:
            last = e
    raise RuntimeError(f"edge-tts 失敗：{last}")


def speak(text, path):
    asyncio.run(_speak(text, path))


def dur(path):
    """用 ffmpeg 讀時長——這台只裝了 ffmpeg，沒有 ffprobe。"""
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path], capture_output=True, text=True
    ).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", err)
    if not m:
        raise RuntimeError("讀不出時長：" + path)
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)


def build(knowledge, illustration, out_path, tmp=None, keep=False):
    tmp = tmp or tempfile.mkdtemp(prefix="igexp_")
    from datetime import datetime

    # 用「。？！」一起斷句並保留原標點——只切 。 的話問句會被吃掉問號，
    # 再無條件補上句號就會變成「…哪裡？。」（2026-08-28 實際出現過）。
    sents = [
        x.strip()
        for x in re.findall(r"[^\n。？！]+[。？！]?", knowledge["content"])
        if x.strip()
    ]
    sents = [x if x[-1] in "。？！" else x + "。" for x in sents]
    print(f"  拆成 {len(sents)} 句", flush=True)

    # ① 逐句配音——每句的停留時間由它自己的旁白長度決定，不是硬給秒數
    # ⚠️ 句尾的呼吸必須真的寫進音軌。只在畫面那邊加秒數的話，字幕會愈跑愈落後——
    #    到第六句會差快 3 秒，而且 -shortest 會讓影片在音檔結束時直接被截掉。
    PAUSE = 0.45
    parts, durs = [], []
    for i, s in enumerate(sents):
        raw = os.path.join(tmp, f"v{i}.mp3")
        speak(s, raw)
        d0 = dur(raw)
        padded = os.path.join(tmp, f"p{i}.mp3")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                raw,
                "-af",
                f"apad=pad_dur={PAUSE}",
                "-t",
                f"{d0 + PAUSE:.3f}",
                padded,
            ],
            check=True,
        )
        parts.append(padded)
        durs.append(dur(padded))
        print(f"    [{i+1}/{len(sents)}] {durs[-1]:.1f}s", flush=True)

    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as fh:
        for p in parts:
            fh.write(f"file '{p}'\n")
    voice = os.path.join(tmp, "voice.mp3")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            lst,
            "-c",
            "copy",
            voice,
        ],
        check=True,
    )

    # ② 逐格算圖
    # gpt-image 常常無視「pure white background」直接畫整片場景。去背之後若幾乎沒縮小，
    # 代表本來就沒有白底可去 → 改走滿版，不要硬擠成一塊浮在紙上的方框。
    cut = cutout(illustration)
    bleed = cut.width * cut.height > 0.82 * illustration.width * illustration.height
    illus = illustration.convert("RGB") if bleed else cut
    print(
        f"  插圖版式：{'滿版（原圖是完整場景）' if bleed else '去背置中'}", flush=True
    )
    canvas = base_canvas(
        knowledge["title_zh"],
        knowledge["title_en"],
        datetime.now().strftime("%Y.%m.%d"),
    )
    cap_font = f(60)
    total = dur(voice)  # 直接以音軌為準，畫面與聲音才不會各走各的
    assert (
        abs(total - sum(durs)) < 0.6
    ), f"音軌 {total:.2f}s 與逐句加總 {sum(durs):.2f}s 對不上"

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{W}x{H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-i",
        voice,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level",
        "4.0",
        "-movflags",
        "+faststart",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        out_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    t, n = 0.0, 0
    while t < total:
        # 鏡頭：整支從 0.94 緩推到 1.06，不做花俏運鏡——內容是主角
        zoom = 1.0 + (0.16 if bleed else 0.12) * (t / total)
        acc, cap = 0.0, ""
        for s, d_ in zip(sents, durs):
            if t < acc + d_:
                cap = s
                break
            acc += d_
        try:
            proc.stdin.write(frame(canvas, illus, zoom, cap, cap_font, bleed).tobytes())
        except BrokenPipeError:
            raise RuntimeError(
                f"ffmpeg 在第 {n} 格（{t:.1f}s / 共 {total:.1f}s）就結束了——"
                "通常是影片長度算得比音軌長"
            )
        n += 1
        t = n / FPS
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg 失敗")
    if keep:
        print(f"  中間檔保留在 {tmp}", flush=True)
    return total


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "explainer.mp4"
    keep = "--keep" in sys.argv

    for name, path in (
        ("ANTHROPIC_API_KEY", "config/.anthropic_key"),
        ("OPENAI_API_KEY", "config/.openai_key"),
    ):
        if not os.environ.get(name) and os.path.exists(path):
            os.environ[name] = open(path).read().strip()

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gp", os.path.join(BASE, "generate_post.py")
    )
    gp = importlib.util.module_from_spec(spec)
    sys.modules["gp"] = gp
    spec.loader.exec_module(gp)

    print("→ 產生今日知識（Claude）...", flush=True)
    k = gp.generate_knowledge(gp.load_recent_seafood())
    print(f"  {k['title_zh']}｜{k.get('category')}", flush=True)

    print("→ 產生插圖（OpenAI）...", flush=True)
    illus = gp.generate_illustration(k["illustration_prompt"])

    print("→ 配音與算圖...", flush=True)
    secs = build(k, illus, out, keep=keep)
    print(f"✅ {out}（{secs:.1f} 秒）", flush=True)


if __name__ == "__main__":
    main()
