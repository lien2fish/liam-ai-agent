#!/usr/bin/env python3
"""逐句把旁白丟回 Whisper 比對，找出克隆聲音唸錯的字。

⛔ 不要只靠耳朵驗——聽過幾遍之後會自動把錯的音腦補成正確的字。
2026-09-11 的 36 歲生日影片，Lien 聽出 2 處，實際有 15 處。
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.expanduser("~/聲音素材/tts/check_say.py")

tag = sys.argv[1] if len(sys.argv) > 1 else "full"
timing = json.load(open(f"{HERE}/audio/{tag}_timing.json", encoding="utf-8"))

bad = []
for t in timing:
    mp3 = f"{HERE}/audio/{tag}/{t['id']}.mp3"
    r = subprocess.run([sys.executable, CHECK, mp3, t["text"]],
                       capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    n = next((l for l in lines if "確定唸錯" in l), "")
    hits = [l for l in lines if l.startswith("  ") and "原文" not in l]
    mark = "🔴" if r.returncode else "  "
    print(f"{mark} {t['id']}  {t['text'][:30]}")
    for h in hits:
        print(f"      {h.strip()}")
    if r.returncode:
        bad.append((t["id"], t["text"], hits))

print(f"\n{'='*60}\n{tag}：{len(timing)} 句，{len(bad)} 句有確定的發音錯誤")
for sid, text, hits in bad:
    print(f"  {sid}  {text}")
sys.exit(1 if bad else 0)
