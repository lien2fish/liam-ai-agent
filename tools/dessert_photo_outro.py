#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dessert_photo_outro — 把一張成品照片補成影片段，接到甜點頻道長片結尾。

用法：
  python3 tools/dessert_photo_outro.py append <照片> <成品.mp4> [秒數] [逆時針旋轉角度]

作法：照片滿版＋極慢推近（1.00→1.06）＋底部漸層壓黑上一行品牌小字，
最後 0.8 秒淡出到黑；音軌是同款 happy BGM（自帶淡入淡出）。
編碼參數與 dessert_longform 產出完全一致，接縫用 concat 畫面 copy 不重編正片。
"""
import sys, os, shutil, subprocess, tempfile, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dessert_longform import ZHF, gen_happy_bgm

W, H = 1080, 1920
SS = 2  # 先在 2 倍尺寸做推近再降回 1080p，避免 zoompan 整數位移的顫抖
BRAND = "泥馬的真心話"  # 頻道台名；「甜點輕鬆做．師傅真心話」是標語，用在封面卡
BGM_RMS = 0.055  # 無人聲段，比墊在人聲下的 0.016 大得多才不會突然變安靜


def load_photo(path, rotate=0):
    from PIL import Image, ImageOps

    if path.lower().endswith((".heic", ".heif")):
        png = tempfile.mktemp(suffix=".png")
        subprocess.run(
            ["sips", "-s", "format", "png", path, "--out", png], capture_output=True
        )
        if not os.path.exists(png):
            raise RuntimeError(f"HEIC 轉檔失敗：{path}")
        img = Image.open(png).convert("RGB")
        os.remove(png)
    else:
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    # 手機直拍有時不帶 EXIF orientation，sips 轉出來是躺的，只能靠 --rotate 補
    return img.rotate(rotate, expand=True) if rotate else img


def make_base(photo, fit):
    """產出 2160×3840 底圖。cover=滿版裁切；contain=完整照片置中＋模糊底。"""
    from PIL import Image, ImageFilter

    tw, th = W * SS, H * SS
    ap, at = photo.width / photo.height, tw / th
    kept = min(ap, at) / max(ap, at)  # 滿版裁切後照片剩下的面積比例
    if fit == "auto":
        fit = "cover" if kept >= 0.45 else "contain"

    if fit == "cover":
        s = max(tw / photo.width, th / photo.height)
        im = photo.resize(
            (round(photo.width * s), round(photo.height * s)), Image.LANCZOS
        )
        x, y = (im.width - tw) // 2, (im.height - th) // 2
        return im.crop((x, y, x + tw, y + th)), fit

    s = max(tw / photo.width, th / photo.height)
    bg = photo.resize((round(photo.width * s), round(photo.height * s)), Image.LANCZOS)
    x, y = (bg.width - tw) // 2, (bg.height - th) // 2
    bg = bg.crop((x, y, x + tw, y + th)).filter(ImageFilter.GaussianBlur(60))
    bg = Image.blend(bg, Image.new("RGB", (tw, th), (0, 0, 0)), 0.35)
    s2 = min(tw / photo.width, th / photo.height)
    fg = photo.resize(
        (round(photo.width * s2), round(photo.height * s2)), Image.LANCZOS
    )
    bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2))
    return bg, fit


def make_overlay(out):
    """1080×1920 透明疊層：底部漸層 ＋ 一行品牌小字（不隨畫面推近）。"""
    from PIL import Image, ImageDraw, ImageFont

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad_h = 420
    g = Image.new("RGBA", (1, grad_h))
    for i in range(grad_h):
        g.putpixel((0, i), (0, 0, 0, int(200 * (i / (grad_h - 1)) ** 1.6)))
    ov.paste(g.resize((W, grad_h)), (0, H - grad_h))

    d = ImageDraw.Draw(ov)
    f = ImageFont.truetype(ZHF, 52)
    tw = d.textlength(BRAND, font=f)
    d.text(
        ((W - tw) / 2, H - 178),
        BRAND,
        font=f,
        fill=(255, 255, 255, 236),
        stroke_width=3,
        stroke_fill=(0, 0, 0, 150),
    )
    ov.save(out)


def build_clip(photo_path, dur, fit, out_mp4, rotate=0):
    tmp = tempfile.mkdtemp()
    base_png = os.path.join(tmp, "base.png")
    ov_png = os.path.join(tmp, "ov.png")

    photo = load_photo(photo_path, rotate)
    base, used = make_base(photo, fit)
    base.save(base_png)
    make_overlay(ov_png)
    print(f"照片 {photo.width}×{photo.height} → {used}")

    bed = gen_happy_bgm(dur, vol=BGM_RMS)
    frames = int(round(dur * 24))
    zoom = f"min(1.0+0.06*on/{frames - 1},1.06)"
    vf = (
        f"zoompan=z='{zoom}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":s={W*SS}x{H*SS}:fps=24,scale={W}:{H}:flags=lanczos[z];"
        f"[z][1:v]overlay=0:0,fade=t=out:st={dur-0.8:.2f}:d=0.8,"
        f"format=yuv420p"
    )
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-t",
            str(dur),
            "-i",
            base_png,
            "-i",
            ov_png,
            "-i",
            bed,
            "-filter_complex",
            f"[0:v]{vf}[v]",
            "-map",
            "[v]",
            "-map",
            "2:a",
            "-t",
            str(dur),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-color_range",
            "tv",
            "-colorspace",
            "bt470bg",
            "-color_primaries",
            "bt470bg",
            "-color_trc",
            "bt709",
            # profile/level/fps 必須與正片一致，否則 concat copy 之後 YouTube 會退件
            "-profile:v",
            "high",
            "-level",
            "4.0",
            "-r",
            "24",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "160k",
            out_mp4,
        ],  # fmt: skip
        capture_output=True,
        text=True,
    )
    os.remove(bed)
    if r.returncode != 0 or not os.path.exists(out_mp4):
        raise RuntimeError("成品展示段產生失敗：\n" + r.stderr[-2000:])


def append(photo_path, video, dur=8.0, fit="auto", rotate=0):
    video = os.path.abspath(video)
    bdir = os.path.join(
        os.path.dirname(video),
        f"備份_加成品展示前_{datetime.date.today():%Y%m%d}",
    )
    os.makedirs(bdir, exist_ok=True)
    backup = os.path.join(bdir, os.path.basename(video))
    if not os.path.exists(backup):
        shutil.copy2(video, backup)
    print(f"原檔已備份：{backup}")

    tmp = tempfile.mkdtemp()
    clip = os.path.join(tmp, "outro.mp4")
    build_clip(photo_path, dur, fit, clip, rotate)

    cc = os.path.join(tmp, "cc.txt")
    open(cc, "w").write(f"file '{video}'\nfile '{clip}'\n")
    merged = os.path.join(tmp, "merged.mp4")
    # 音訊重編（純 -c copy 接縫會出 non-monotonic DTS），畫面 copy 故正片零損失
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            cc,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            merged,
        ],  # fmt: skip
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or os.path.getsize(merged) <= os.path.getsize(video) * 0.9:
        raise RuntimeError("concat 失敗：\n" + r.stderr[-2000:])
    os.replace(merged, video)
    print(f"✅ 已接上 {dur:.0f} 秒成品展示：{video}")


def main():
    if len(sys.argv) < 4 or sys.argv[1] != "append":
        print(__doc__)
        return
    dur = float(sys.argv[4]) if len(sys.argv) > 4 else 8.0
    rotate = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    append(sys.argv[2], sys.argv[3], dur, rotate=rotate)


if __name__ == "__main__":
    main()
