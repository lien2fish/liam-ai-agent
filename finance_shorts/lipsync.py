"""podcast 版：每句台詞＋說話者的近景圖 → fal.ai Kling AI Avatar v2 對嘴影片。

已經生成過的句子不重生（每次都是真的扣錢）。輪詢逾時不重送，用 request_id 續查。
不加 --go 只會列出要生哪幾句、預估花多少。

用法：
  python3 finance_shorts/lipsync.py ins-03p                 # 預估
  python3 finance_shorts/lipsync.py ins-03p --only l6 --go  # 只生一句試水溫
  python3 finance_shorts/lipsync.py ins-03p --go            # 全部
"""

import base64
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
SCRIPTS = json.loads((ROOT / "scripts.json").read_text())

MODELS = {
    "std": (
        "fal-ai/kling-video/ai-avatar/v2/standard",
        0.0562,
    ),  # 2026-10-15 fal.ai 官網牌價（USD／秒）
    "pro": ("fal-ai/kling-video/ai-avatar/v2/pro", 0.115),
}
TWD = 31.5
FACE = {
    "cat": ROOT / "shared/chars/studio_cat.png",
    "dog": ROOT / "shared/chars/studio_dog.png",
}
WIDE = ROOT / "shared/chars/studio_wide169.png"
PROMPT = {
    "cat": "The orange cat talks into the microphone with natural mouth movement, small head motion, keeps sitting, camera static.",
    "dog": "The Shiba Inu dog talks into the microphone with natural mouth movement, small head motion, keeps sitting, camera static.",
}
# 同框對談：只讓說話的那隻開口，嘴型刻意誇張
NAME = {"cat": "orange tabby cat on the left", "dog": "Shiba Inu dog on the right"}
EXAG = (
    "The {who} talks into the microphone with big, clearly visible mouth movements, its jaw opening wide on every syllable. "
    "Keep a realistic animal mouth: natural fur, animal lips, small animal teeth and tongue. "
    "No human lips, no lipstick, no human mouth. Lively expressive face, keeps sitting, camera static."
)
TWO_SHOT = (
    "Two-shot podcast, camera static. Only the {who} is speaking: big exaggerated cartoon-like mouth movements, "
    "jaw opening wide on every syllable, lively expressive face and head gestures. "
    "The {other} does NOT speak and does NOT smile with an open mouth: its jaw stays shut and lips sealed the whole time, it only listens quietly, blinks and nods slightly."
)


def padded(path, dur, min_sec=3.0):
    """Kling 對嘴太短的音檔會回 downstream_service_error（1.73 秒實測失敗），尾端補靜音到 3 秒（2.2 秒也失敗）。
    版面只取配音本身的長度，補的部分不會出現在成品。"""
    if dur >= min_sec:
        return path
    out = path.with_name(path.stem + "_pad.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-af", f"apad=whole_dur={min_sec}", str(out)], check=True)
    return out


def data_uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def call(url, key, body=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    eid = args[0]
    go = "--go" in sys.argv
    only = (
        sys.argv[sys.argv.index("--only") + 1].split(",")
        if "--only" in sys.argv
        else None
    )
    tier = "pro" if "--pro" in sys.argv else "std"
    two = "--two" in sys.argv
    close = "--close" in sys.argv  # 近景誇張嘴型，之後由 podcast.py 貼回同框畫面
    model, usd = MODELS[tier]
    studio = SCRIPTS["episodes"][eid].get("studio", "studio")  # 每集可換角色：shared/chars/{studio}_cat.png／_dog.png

    adir, vdir = ROOT / eid / "audio", ROOT / eid / (
        "lipsync" + ("_two" if two else "") + ("_close" if close else "") + ("_pro" if tier == "pro" else "")
    )
    vdir.mkdir(parents=True, exist_ok=True)
    jobs_path = vdir / "jobs.json"
    jobs = json.loads(jobs_path.read_text()) if jobs_path.exists() else {}
    dur = json.loads((adir / "durations.json").read_text())

    todo = []
    for i, line in enumerate(SCRIPTS["episodes"][eid]["lines"], 1):
        k = f"l{i}"
        if only and k not in only:
            continue
        if (vdir / f"{k}.mp4").exists() and jobs.get(k, {}).get("sig") == dur[k]["sig"]:
            continue
        todo.append((k, line["speaker"], dur[k]))

    secs = sum(d["dur"] for _, _, d in todo)
    print(
        f"要生 {len(todo)} 句、{secs:.1f} 秒 → 約 US${secs * usd:.2f}（NT${secs * usd * TWD:.0f}）"
    )
    for k, who, d in todo:
        print(f"  {k} {who} {d['dur']:.2f}s {d['text']}")
    if not go or not todo:
        return

    key = (REPO / "config/.fal_key").read_text().strip()
    for k, who, d in todo:
        job = jobs.get(k)
        if not job or job.get("sig") != d["sig"]:
            r = call(
                f"https://queue.fal.run/{model}",
                key,
                {
                    "image_url": data_uri(WIDE if two else ROOT / f"shared/chars/{studio}_{who}.png", "image/png"),
                    "audio_url": data_uri(padded(adir / f"{k}.mp3", d["dur"]), "audio/mpeg"),
                    "prompt": (
                        TWO_SHOT.format(
                            who=NAME[who], other=NAME["dog" if who == "cat" else "cat"]
                        )
                        if two
                        else EXAG.format(who=NAME[who].rsplit(" on the ", 1)[0])
                        if close and "--natural" not in sys.argv and not (who == "cat" and "--natural-cat" in sys.argv)
                        else PROMPT[who]
                    ),
                },
            )
            job = {
                "sig": d["sig"],
                "request_id": r["request_id"],
                "status_url": r["status_url"],
                "response_url": r["response_url"],
            }
            jobs[k] = job
            jobs_path.write_text(json.dumps(jobs, indent=2) + "\n")
            print(f"  {k} 已送出 {r['request_id']}")
        for _ in range(120):
            st = call(job["status_url"], key)["status"]
            if st == "COMPLETED":
                break
            time.sleep(5)
        else:
            raise SystemExit(
                f"⏳ {k} 10 分鐘還沒好，request_id 已存在 jobs.json，重跑會續查不會重送"
            )
        res = call(job["response_url"], key)
        urllib.request.urlretrieve(res["video"]["url"], vdir / f"{k}.mp4")
        print(f"  ✅ {k} {res.get('duration')}s → {vdir / f'{k}.mp4'}")


if __name__ == "__main__":
    main()
