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
import math
import os
import platform
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 24
VOICE = os.environ.get("IG_VOICE", "zh-TW-YunJheNeural")  # 男聲
RATE = os.environ.get("IG_VOICE_RATE", "+8%")

# 擋掉「辨別型」題目：gpt-image 分不出頭足類的鰭形、相似魚種的體側差異，
# 教辨別卻配錯插圖比沒有插圖更糟，而且直接踩到產地真實性紅線。
# 這些角度一律退回靜態圖，不出影片。
BLOCKED_ANGLES = {"相似魚種比較", "外觀辨別", "選購技巧"}
# 分類擋不住的，再看內容有沒有這些字
BLOCKED_WORDS = {
    "誤認",
    "混用",
    "分辨",
    "辨別",
    "區別",
    "怎麼分",
    "相似",
    "誤把",
    "搞混",
    "區分",
}

CREAM = (243, 238, 226)
INK = (45, 65, 105)
GOLD = (176, 148, 96)
MUTED = (130, 112, 84)

BASE = os.path.dirname(os.path.abspath(__file__))
# 字型：macOS 用 PingFang，Linux（GitHub Actions）用 Noto CJK。
# ⚠️ 不要寫死 macOS 路徑——雲端是 Linux，那個檔不存在，影片這條路會每天直接爆掉。
# 邏輯與 generate_post 相同，但刻意各自持有：互相 import 會在 __main__ 情境下
# 載進第二份 generate_post，反而更難查。
if platform.system() == "Darwin":
    FONT, FONT_IDX = "/System/Library/Fonts/PingFang.ttc", 3
else:
    _fc = subprocess.run(
        ["fc-list", ":lang=zh", "--format=%{file}\n"], capture_output=True, text=True
    )
    _noto = [l.strip() for l in _fc.stdout.splitlines() if "Noto" in l and "CJK" in l]
    FONT = (
        _noto[0] if _noto else "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"
    )
    FONT_IDX = 3 if FONT.endswith(".ttc") else 0

PAD = 96  # 左右安全邊
ILLUS_TOP, ILLUS_H = 330, 980  # 插圖區
CAP_TOP = 1420  # 字幕區起點


def f(size):
    return ImageFont.truetype(FONT, size, index=FONT_IDX)


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
    d.text(
        (W - PAD - d.textlength("鉅鑫 · 龜吼現流", font=f(32)), H - 130),
        "鉅鑫 · 龜吼現流",
        font=f(32),
        fill=MUTED,
    )
    return im


def frame(canvas, illus, zoom, caption, cap_font, bleed, drift=(0, 0)):
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
        # 漂移要夾在裁切框的餘裕內，超出去會露出黑邊
        sx, sy = (w - W) // 2, (h - ILLUS_H) // 2
        x = max(0, min(w - W, sx + int(drift[0])))
        y = max(0, min(h - ILLUS_H, sy + int(drift[1])))
        im.paste(sm.crop((x, y, x + W, y + ILLUS_H)), (0, ILLUS_TOP))
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


async def _speak_all(text, path):
    """整段一次合成，並收下 word boundary 當時間軸。

    ⚠️ 不要逐句合成。逐句的話每一句都從同樣的平板語氣起頭、句間又是硬接，
    聽起來就是機械音；整段一次過，語氣才會連貫，標點自然帶出停頓。
    代價是要自己把每句對回時間軸——這就是 word boundary 的用處。
    """
    import edge_tts

    marks = []
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    with open(path, "wb") as fh:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                fh.write(ch["data"])
            elif ch["type"] in ("SentenceBoundary", "WordBoundary"):
                marks.append((ch["type"], ch["offset"] / 1e7, ch.get("text", "")))
    if os.path.getsize(path) < 800:
        raise RuntimeError("edge-tts 回傳空音檔")
    return marks


def speak_all(text, path):
    last = None
    for _ in range(6):  # edge-tts 偶爾 NoAudioReceived
        try:
            return asyncio.run(_speak_all(text, path))
        except Exception as e:
            last = e
    raise RuntimeError(f"edge-tts 失敗：{last}")


def _bare(t):
    """只留會被唸出來的字——標點不會出現在 word boundary 裡。"""
    return re.sub(r"[^\w]", "", t)


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


def sentence_starts(sents, marks, total):
    """把每一句對到時間軸上的起點。

    edge-tts 7.x 吐的是 SentenceBoundary（直接給每句的 offset），舊版才是
    WordBoundary。⚠️ 2026-08-28 踩過：只認 WordBoundary 的話會拿到 0 個標記，
    每句起點全變 0.0，第一句字幕就從頭掛到尾——而且不會報錯。
    所以三層都要有：句級 → 字級 → 按字數比例分配。
    """
    sb = [(t, txt) for typ, t, txt in marks if typ == "SentenceBoundary"]
    if len(sb) == len(sents):
        return [t for t, _ in sb]

    wb = [(t, txt) for typ, t, txt in marks if typ == "WordBoundary"]
    if wb:
        acc, idx = [], 0
        for t, txt in wb:
            acc.append((idx, t))
            idx += len(_bare(txt))
        starts, pos = [], 0
        for x in sents:
            starts.append(next((tt for i, tt in acc if i >= pos), acc[-1][0]))
            pos += len(_bare(x))
        return starts

    # 最後手段：按字數比例分。不精準，但至少字幕會跟著往前走。
    print("  ⚠️ 沒有任何時間標記，字幕改用字數比例分配（會不夠準）", flush=True)
    lens = [max(1, len(_bare(x))) for x in sents]
    tot = sum(lens)
    out, acc = [], 0
    for L in lens:
        out.append(total * acc / tot)
        acc += L
    return out


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

    # ① 整段一次配音，再用 word boundary 把每句對回時間軸
    voice = os.path.join(tmp, "voice.mp3")
    marks = speak_all("".join(sents), voice)
    total = dur(voice)
    starts = sentence_starts(sents, marks, total)
    print(f"  旁白 {total:.1f}s（時間標記 {len(marks)} 個）", flush=True)
    for i, (x, t0) in enumerate(zip(sents, starts)):
        print(f"    [{i+1}] {t0:5.1f}s  {x[:18]}", flush=True)
    assert starts == sorted(starts), "句子起點沒有遞增，時間軸對錯了"

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
        # 起點就給 1.06 的餘裕，漂移才有空間可走（1.00 剛好貼齊，一動就露黑邊）
        zoom = (1.06 if bleed else 1.0) + (0.14 if bleed else 0.12) * (t / total)
        # 兩個不同週期的正弦：水流帶著整片景緩慢晃，比等速平移像「在游」
        drift = (
            (
                math.sin(t / 9.0 * 2 * math.pi) * 26,
                math.sin(t / 6.5 * 2 * math.pi + 1.1) * 16,
            )
            if bleed
            else (0, 0)
        )
        cap = ""
        for x, t0 in zip(sents, starts):
            if t >= t0:
                cap = x
        try:
            proc.stdin.write(
                frame(canvas, illus, zoom, cap, cap_font, bleed, drift).tobytes()
            )
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

    # generate_post 在本機是從 config/instagram_config.json 讀 anthropic_api_key，
    # 而那個檔沒有這個欄位 → 本機一定退到 Gemini。這裡直接補上，本機才跟雲端同一條路。
    if not gp.ANTHROPIC_KEY and os.environ.get("ANTHROPIC_API_KEY"):
        gp.ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]

    print("→ 產生今日知識（Claude）...", flush=True)
    k = gp.generate_knowledge(gp.load_recent_seafood())
    print(f"  {k['title_zh']}｜{k.get('category')}", flush=True)

    angle = k.get("category", "")
    text = k.get("title_zh", "") + k.get("content", "")
    # ⚠️ 只看分類擋不住。2026-08-28 出過「紅甘的身分謎團／常見誤解」——分類不在名單裡，
    #    內容卻整篇在講紅甘與油甘怎麼分，正是最需要正確插圖的那種題目。
    hit = [w for w in BLOCKED_WORDS if w in text]
    if angle in BLOCKED_ANGLES or hit:
        print(
            f"⛔ 今日角度「{angle}」屬辨別型，不出影片——AI 插圖分不出相似魚種的\n"
            f"   外型差異，教辨別卻配錯圖比沒有圖更糟。今天改用靜態圖即可。",
            flush=True,
        )
        return 0

    print("→ 產生插圖（OpenAI）...", flush=True)
    illus = gp.generate_illustration(k["illustration_prompt"])

    print("→ 配音與算圖...", flush=True)
    secs = build(k, illus, out, keep=keep)
    print(f"✅ {out}（{secs:.1f} 秒）", flush=True)


if __name__ == "__main__":
    main()
