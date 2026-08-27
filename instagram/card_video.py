# -*- coding: utf-8 -*-
"""把每日貼文那張卡「動起來」——同一個版面，字逐句浮現。

刻意不做遮罩、不換背景：卡紙本來就是米色底配深藍字，先天就看得清楚，
再疊遮罩只會讓它變濁。字幕清楚是唯一的標準。

畫面完全來自 generate_post.compose_image，只是分階段畫：
  S0 空卡 → S1 插圖淡入 → S2 標頭出現 → S3.. 內文逐句出現。
**版面永遠用完整內容算**，所以每一格的位置都跟同一天的靜態圖對得上。

    python3 instagram/card_video.py --demo out.mp4    # 本機試跑一支
"""
import subprocess
import sys
import time

FPS = 24
FADE = 0.35  # 每次轉場的交叉淡入秒數
T_AFTER_ILLUS = 0.7  # 插圖進來後的停頓
T_HEADER = 0.8  # 標頭出現後的停頓
T_LINE = 2.2  # 每一句停留
T_END = 2.0  # 最後一格停留


def _states(gp, knowledge, illustration):
    """回傳 (畫面, 停留秒數) 的清單。只算這幾張，不是每一格都重算。"""
    stats = {}
    full = gp.compose_image(knowledge, illustration, stats=stats)
    n = stats["lines"]

    out = [
        (
            gp.compose_image(
                knowledge, illustration, illus_alpha=0, show_header=False, max_lines=0
            ),
            0.25,
        ),
        (
            gp.compose_image(knowledge, illustration, show_header=False, max_lines=0),
            T_AFTER_ILLUS,
        ),
        (gp.compose_image(knowledge, illustration, max_lines=0), T_HEADER),
    ]
    for i in range(1, n + 1):
        img = full if i == n else gp.compose_image(knowledge, illustration, max_lines=i)
        out.append((img, T_LINE if i < n else T_LINE + T_END))
    return out


def _blend(a, b, t):
    from PIL import Image

    return Image.blend(a, b, t)


def render(gp, knowledge, illustration, out_path, fps=FPS):
    """算圖並輸出 mp4。回傳 (秒數, 花費秒數)。"""
    t0 = time.time()
    states = _states(gp, knowledge, illustration)
    W, H = states[0][0].size

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
        str(fps),
        "-i",
        "-",
        # IG 對無音軌的影片偶爾會轉檔失敗，補一條靜音軌最保險
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=48000:cl=stereo",
        "-shortest",
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
        "64k",
        out_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    n_frames = 0
    fade_frames = max(1, int(FADE * fps))
    prev = None
    for img, hold in states:
        if prev is not None:  # 轉場：交叉淡入
            for k in range(1, fade_frames + 1):
                proc.stdin.write(_blend(prev, img, k / fade_frames).tobytes())
                n_frames += 1
        buf = img.tobytes()
        for _ in range(max(1, int(hold * fps))):
            proc.stdin.write(buf)
            n_frames += 1
        prev = img

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg 失敗")
    return n_frames / fps, time.time() - t0


def _demo(out_path):
    import importlib.util, os

    os.environ.setdefault("OPENAI_API_KEY", "x")
    spec = importlib.util.spec_from_file_location(
        "gp",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_post.py"),
    )
    gp = importlib.util.module_from_spec(spec)
    sys.modules["gp"] = gp
    spec.loader.exec_module(gp)

    from PIL import Image, ImageDraw

    knowledge = {
        "title_zh": "白帶魚",
        "title_en": "Largehead Hairtail",
        "content": "白帶魚體側扁如帶，銀白色的表層不是鱗片。\n那是一層叫「鳥嘌呤」的結晶。\n這層結晶怕摩擦，一碰就掉。\n所以魚體銀亮完整的，代表從上鉤到上岸都被小心對待。\n挑的時候看銀膜是否均勻、魚眼是否清澈。\n比看大小更準。",
    }
    illus = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
    ImageDraw.Draw(illus).ellipse([180, 380, 850, 640], fill=(150, 165, 185, 255))

    dur, cost = render(gp, knowledge, illus, out_path)
    print(f"影片長度 {dur:.1f} 秒，算圖耗時 {cost:.1f} 秒 → {out_path}")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo(sys.argv[sys.argv.index("--demo") + 1])
    else:
        print(__doc__)
