#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
music_reel — 樂器演奏長片轉 9:16 精華短影音（獨立工具，與 reel_maker 海鮮流程無關）

原則：音樂就是內容 — 保留原音、不降噪、不變速、不混 BGM、預設無字幕。

兩步流程：
  1) 選段輔助（聽力為主、能量分析為輔）：
       python3 tools/music_reel.py analyze "/path/長片.MOV"
     印出每秒能量曲線＋建議精華段落，並產 <長片>_music_config.json 範本

  2) 依設定產出 影片＋封面：
       python3 tools/music_reel.py build config.json
     產出（預設桌面）：<主題>.mp4、<主題>_封面.jpg

config 欄位：
  video / subject / out_dir(預設~/Desktop) / segments([[起,迄]秒,原片時間軸])
  cover({time, main, sub}) — main 放曲名或主題，可留空跳過封面
  fade(段落交界音訊淡入淡出秒數，預設0.15，防直切爆音)

樂譜跟隨（直笛/演奏教學風，選填；時間都是「輸出後」時間軸）：
  title({text, end}) — 開場曲名橫幅(格紋紙底+棕字)，0~end 秒顯示，全螢幕影片
  score([[起,迄,"樂譜圖路徑"],...]) — 頂部白底樂譜條，按時間換頁
  shift_y(預設400) — title 結束後影片下移 px，讓出頂部給樂譜
  score_y(預設170) — 樂譜條頂端 y 位置
  score_h — 設了就改用「白底大面板」蓋臉模式：樂譜去白邊放大置中於
            1080×score_h 白面板（例：shift_y=0+score_y=0+score_h=450
            → 影片不下移、面板蓋到鼻子，只露吹奏嘴型與手部）

相依：ffmpeg、numpy、Pillow。無 ffprobe（時長由 segments 數學計算）。
"""
import sys, os, json, subprocess, wave, tempfile
import numpy as np

ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"

LB = (
    "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
    "boxblur=25:2,eq=brightness=-0.08[bg];"
    "[0:v]scale=1080:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
)


# ---------- analyze：能量曲線＋選段建議 ----------
def extract_audio(video):
    out = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", out],
        capture_output=True,
    )
    return out


def analyze(video):
    wav = extract_audio(video)
    w = wave.open(wav, "rb")
    sr = w.getframerate()
    a = (
        np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
        / 32768.0
    )
    os.remove(wav)
    n = len(a) // sr
    db = np.array(
        [
            20 * np.log10(np.sqrt(np.mean(a[i * sr : (i + 1) * sr] ** 2)) + 1e-9)
            for i in range(n)
        ]
    )
    thr = float(np.percentile(db, 70))
    hot = db >= thr

    segs = []
    i = 0
    while i < n:
        if not hot[i]:
            i += 1
            continue
        j = i
        gap = 0
        k = i
        while k < n and gap <= 2:
            if hot[k]:
                j = k
                gap = 0
            else:
                gap += 1
            k += 1
        if j - i + 1 >= 8:
            segs.append([i, j + 1])
        i = k

    print(f"總長約 {n} 秒｜能量門檻 {thr:.1f} dB（70 百分位）")
    for i in range(0, n, 10):
        blk = db[i : i + 10]
        bar = "".join("█" if x >= thr else "▁" for x in blk)
        print(f"{i:5d}s {bar}  峰值{blk.max():.0f}dB")
    print("\n建議精華段落（原片秒數，僅供參考，以耳朵為準）：")
    for s, e in segs:
        print(f"  [{s}, {e}]  {e - s}秒")

    base = os.path.splitext(video)[0]
    cfg = {
        "video": video,
        "subject": "主題名",
        "out_dir": os.path.expanduser("~/Desktop"),
        "fade": 0.15,
        "segments": [[float(s), float(e)] for s, e in segs],
        "cover": {
            "time": float(segs[0][0] + 2) if segs else 2.0,
            "main": "曲名",
            "sub": "",
        },
    }
    path = base + "_music_config.json"
    json.dump(cfg, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n已產出 config 範本：", path)
    print("→ 填好 subject / 確認 segments / 封面曲名後跑：")
    print(f"   python3 tools/music_reel.py build '{path}'")


# ---------- 封面 ----------
def make_cover(video, t, main, sub, out):
    from PIL import Image, ImageDraw, ImageFont

    base = tempfile.mktemp(suffix=".jpg")
    fc = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "boxblur=25:2,eq=brightness=-0.12[bg];"
        "[0:v]scale=1080:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(t),
            "-i",
            video,
            "-frames:v",
            "1",
            "-filter_complex",
            fc,
            base,
        ],
        capture_output=True,
    )
    img = Image.open(base).convert("RGB")
    d = ImageDraw.Draw(img)
    W, H = img.size

    scrim = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(scrim)
    for y in range(H):
        a = int(150 * ((y - H * 0.45) / (H * 0.55))) if y > H * 0.45 else 0
        sd.line([(0, y), (W, y)], fill=max(0, min(a, 150)))
    img.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), scrim)
    d = ImageDraw.Draw(img)

    fs = 200
    while fs > 44:
        f = ImageFont.truetype(ZHF, fs)
        if d.textlength(main, font=f) <= W - 160:
            break
        fs -= 6
    tw = d.textlength(main, font=f)
    y = int(H * 0.62)
    d.text(
        ((W - tw) / 2, y),
        main,
        font=f,
        fill=(255, 255, 255),
        stroke_width=max(10, fs // 12),
        stroke_fill=(18, 18, 18),
    )
    if sub:
        f2 = ImageFont.truetype(ZHF, 56)
        tw2 = d.textlength(sub, font=f2)
        d.text(
            ((W - tw2) / 2, y + fs + 40),
            sub,
            font=f2,
            fill=(235, 235, 235),
            stroke_width=6,
            stroke_fill=(18, 18, 18),
        )
    img.save(out, quality=92)
    os.remove(base)


# ---------- 樂譜面板（白底、去邊放大、可蓋臉） ----------
def score_panel(img_path, out, w=1080, h=450):
    from PIL import Image, ImageOps

    im = Image.open(os.path.expanduser(img_path)).convert("RGB")
    bbox = (
        ImageOps.invert(im.convert("L")).point(lambda x: 255 if x > 40 else 0).getbbox()
    )
    if bbox:
        pad = 14
        im = im.crop(
            (
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(im.width, bbox[2] + pad),
                min(im.height, bbox[3] + pad),
            )
        )
    r = min((w - 40) / im.width, (h - 24) / im.height)
    im = im.resize((int(im.width * r), int(im.height * r)))
    panel = Image.new("RGB", (w, h), (255, 255, 255))
    panel.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    panel.save(out)


# ---------- 曲名橫幅（格紋紙底＋棕色手寫感大字） ----------
MARKER_FONT = "/System/Library/Fonts/MarkerFelt.ttc"
BANNER_TXT = (128, 100, 84)
GRID_LINE = (216, 220, 228)


def make_title_banner(text, out, w=1080, h=340):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (w, h), (252, 252, 250))
    d = ImageDraw.Draw(img)
    for x in range(0, w, 54):
        d.line([(x, 0), (x, h)], fill=GRID_LINE, width=2)
    for y in range(0, h, 54):
        d.line([(0, y), (w, y)], fill=GRID_LINE, width=2)
    fs = 190
    while fs > 60:
        f = ImageFont.truetype(MARKER_FONT, fs)
        bb = d.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= w - 110:
            break
        fs -= 8
    bb = d.textbbox((0, 0), text, font=f)
    d.text(
        ((w - (bb[2] - bb[0])) / 2 - bb[0], (h - (bb[3] - bb[1])) / 2 - bb[1]),
        text,
        font=f,
        fill=BANNER_TXT,
    )
    img.save(out)


# ---------- build ----------
def build(cfg):
    video = cfg["video"]
    subject = cfg["subject"]
    out_dir = os.path.expanduser(cfg.get("out_dir", "~/Desktop"))
    fade = float(cfg.get("fade", 0.15))
    segs = cfg["segments"]
    os.makedirs(out_dir, exist_ok=True)

    tmp = tempfile.mkdtemp()
    parts = []
    total = 0.0
    for i, (s, e) in enumerate(segs):
        dur = e - s
        total += dur
        af = (
            f"afade=t=in:st=0:d={fade},"
            f"afade=t=out:st={max(0.0, dur - fade):.3f}:d={fade}"
        )
        p = os.path.join(tmp, f"seg{i}.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(s),
                "-t",
                str(dur),
                "-i",
                video,
                "-filter_complex",
                LB,
                "-map",
                "[v]",
                "-map",
                "0:a",
                "-af",
                af,
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-b:a",
                "192k",
                "-r",
                "24",
                p,
            ],
            capture_output=True,
        )
        parts.append(p)

    cc = os.path.join(tmp, "cc.txt")
    open(cc, "w").write("\n".join(f"file '{p}'" for p in parts))
    out_mp4 = os.path.join(out_dir, f"{subject}.mp4")
    title = cfg.get("title")
    score = cfg.get("score", [])
    if not title and not score:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                cc,
                "-c",
                "copy",
                out_mp4,
            ],
            capture_output=True,
        )
    else:
        joined = os.path.join(tmp, "joined.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                cc,
                "-c",
                "copy",
                joined,
            ],
            capture_output=True,
        )
        shift = int(cfg.get("shift_y", 400))
        score_y = int(cfg.get("score_y", 170))
        te = float(title.get("end", 2.0)) if title else 0.0
        inputs = ["-i", joined]
        fc = [f"color=c=black:s=1080x1920:r=24:d={total:.2f}[bg]", "[0:v]setsar=1[vid]"]
        y_expr = f"'if(lt(t,{te}),0,{shift})'" if title else str(shift)
        fc.append(f"[bg][vid]overlay=0:{y_expr}:shortest=1[b0]")
        idx = 1
        cur = "b0"
        score_h = cfg.get("score_h")
        for k, (s, e, img) in enumerate(score):
            if score_h:
                pimg = os.path.join(tmp, f"panel{k}.png")
                score_panel(img, pimg, h=int(score_h))
                inputs += ["-i", pimg]
                fc.append(
                    f"[{cur}][{idx}:v]overlay=0:{score_y}:enable='between(t,{s},{e})'[b{idx}]"
                )
            else:
                inputs += ["-i", os.path.expanduser(img)]
                fc.append(f"[{idx}:v]scale=1080:-1[sc{k}]")
                fc.append(
                    f"[{cur}][sc{k}]overlay=0:{score_y}:enable='between(t,{s},{e})'[b{idx}]"
                )
            cur = f"b{idx}"
            idx += 1
        if title:
            banner = os.path.join(tmp, "title.png")
            make_title_banner(title["text"], banner)
            inputs += ["-i", banner]
            fc.append(f"[{cur}][{idx}:v]overlay=0:700:enable='lt(t,{te})'[b{idx}]")
            cur = f"b{idx}"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                *inputs,
                "-filter_complex",
                ";".join(fc),
                "-map",
                f"[{cur}]",
                "-map",
                "0:a",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "copy",
                "-r",
                "24",
                out_mp4,
            ],
            capture_output=True,
        )

    cov = cfg.get("cover")
    if cov and cov.get("main"):
        make_cover(
            video,
            cov["time"],
            cov["main"],
            cov.get("sub", ""),
            os.path.join(out_dir, f"{subject}_封面.jpg"),
        )

    print("完成，已存到", out_dir)
    print(" ", f"{subject}.mp4  (約{total:.0f}秒, 原速原音)")
    if cov and cov.get("main"):
        print(" ", f"{subject}_封面.jpg")


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("analyze", "build"):
        print(__doc__)
        return
    if sys.argv[1] == "analyze":
        analyze(sys.argv[2])
    else:
        build(json.load(open(sys.argv[2], encoding="utf-8")))


if __name__ == "__main__":
    main()
