#!/usr/bin/env python3
"""每日進入點：Claude生腳本 → 組裝影片 → 上傳 YouTube → 記錄主題去重。

環境變數：
  YT_PRIVACY        上傳隱私（private/unlisted/public，預設 private）
  YT_PUBLISH_HOUR   有設＝排程發布：影片先上傳，當天該台灣時間自動轉公開（如 18）
"""
import os, tempfile, shutil
from datetime import datetime, timezone, timedelta

import generate_script
import build_video
import upload

PRIVACY = os.environ.get("YT_PRIVACY", "private")
PUBLISH_HOUR = os.environ.get("YT_PUBLISH_HOUR")  # 台灣時間整點，有設則排程發布


def log(m):
    print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


def scheduled_publish_at():
    """回傳當天台灣 PUBLISH_HOUR 點的 RFC3339 UTC；若已過則排明天"""
    if not PUBLISH_HOUR:
        return None
    tw = timezone(timedelta(hours=8))
    now = datetime.now(tw)
    target = now.replace(hour=int(PUBLISH_HOUR), minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    recent = generate_script.load_recent()
    log(f"近期主題 {len(recent)} 個，生成新腳本...")
    script = generate_script.generate(recent)
    log(f"主題：{script['topic']} ─ {script['title']}")

    tmp = tempfile.mkdtemp(prefix="ytshort_")
    try:
        out = os.path.join(tmp, "short.mp4")
        build_video.build_video(script, out, workdir=tmp)

        publish_at = scheduled_publish_at()
        log(f"上傳 YouTube（{'排程 '+publish_at if publish_at else PRIVACY}）...")
        desc = script.get("description", "")
        vid = upload.upload(
            out,
            script["title"],
            desc,
            script.get("tags", []),
            privacy=PRIVACY,
            publish_at=publish_at,
        )

        generate_script.save_recent(recent, script["topic"])
        log(f"完成：https://youtu.be/{vid} ｜ 已記錄主題 {script['topic']}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
