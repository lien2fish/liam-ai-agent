#!/usr/bin/env python3
"""每日進入點：Claude生腳本 → 組裝影片 → 上傳 YouTube → 記錄主題去重。

環境變數：
  YT_PRIVACY  上傳隱私（private/unlisted/public，預設 private 保險）
"""
import os, tempfile, shutil
from datetime import datetime

import generate_script
import build_video
import upload

PRIVACY = os.environ.get("YT_PRIVACY", "private")


def log(m):
    print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


def main():
    recent = generate_script.load_recent()
    log(f"近期主題 {len(recent)} 個，生成新腳本...")
    script = generate_script.generate(recent)
    log(f"主題：{script['topic']} ─ {script['title']}")

    tmp = tempfile.mkdtemp(prefix="ytshort_")
    try:
        out = os.path.join(tmp, "short.mp4")
        build_video.build_video(script, out, workdir=tmp)

        log(f"上傳 YouTube（{PRIVACY}）...")
        desc = script.get("description", "")
        vid = upload.upload(
            out, script["title"], desc, script.get("tags", []), privacy=PRIVACY
        )

        generate_script.save_recent(recent, script["topic"])
        log(f"完成：https://youtu.be/{vid} ｜ 已記錄主題 {script['topic']}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
