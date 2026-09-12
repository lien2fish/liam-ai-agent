#!/usr/bin/env python3
"""從 script.md 產生逐句旁白，並量出每句長度供時間軸使用。

旁白＝Lien 的克隆聲音，屬生物特徵資料，audio/ 不進版控（見 .gitignore）。
已產出的句子會跳過，改稿後只要刪掉那一句的檔案就會重生。
"""
import json, re, subprocess, sys, os

SAY = os.path.expanduser("~/聲音素材/tts/say.py")
HERE = os.path.dirname(os.path.abspath(__file__))


def parse(section):
    body = open(f"{HERE}/script.md", encoding="utf-8").read()
    seg = body.split(f"## {section}")[1].split("\n## ")[0]
    return [m.group(1).strip() for m in re.finditer(r"^\d+\. (.+)$", seg, re.M)]


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "full"
    section, tag = {"full": ("完整版", "full"), "short": ("精華版", "short")}[which]
    lines = parse(section)
    out = f"{HERE}/audio/{tag}"
    os.makedirs(out, exist_ok=True)

    timing = []
    for i, text in enumerate(lines, 1):
        sid = f"s{i:02d}"
        mp3 = f"{out}/{sid}.mp3"
        if not os.path.exists(mp3):
            wav = f"{out}/{sid}_000.wav"
            subprocess.run([SAY, text, "-o", f"{out}/{sid}"], check=True,
                           stdout=subprocess.DEVNULL)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
                            "-b:a", "192k", mp3], check=True)
            os.remove(wav)
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", mp3],
            capture_output=True, text=True, check=True).stdout.strip())
        timing.append({"id": sid, "text": text, "dur": round(dur, 2)})
        print(f"  {sid}  {dur:5.2f}s  {text[:26]}")

    json.dump(timing, open(f"{HERE}/audio/{tag}_timing.json", "w"),
              ensure_ascii=False, indent=2)
    total = sum(t["dur"] for t in timing)
    print(f"\n{section}：{len(timing)} 句，語音合計 {total:.1f} 秒")


if __name__ == "__main__":
    main()
