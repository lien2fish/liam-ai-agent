#!/usr/bin/env python3
"""每日進入點：自動決定長片/Shorts → Claude生腳本 → 組裝影片 → 上傳 → 記錄去重。

格式策略（由系統自動決定，可用 YT_FORMAT 手動覆寫 long/short）：
  長片(16:9, 2-3分鐘)：週二/週五/週日
  Shorts(9:16, ~50秒)：其餘四天
環境變數：
  YT_FORMAT         手動指定 long / short（覆寫自動排程）
  YT_PRIVACY        上傳隱私（預設 private）
  YT_PUBLISH_HOUR   有設＝排程發布：影片先上傳，當天該台灣時間自動轉公開（如 18）
"""
import os, tempfile, shutil
from datetime import datetime, date, timezone, timedelta

import generate_script
import upload

PRIVACY = os.environ.get("YT_PRIVACY", "private")
PUBLISH_HOUR = os.environ.get("YT_PUBLISH_HOUR")

# 長片日：週二(1)/週五(4)/週日(6)，其餘為 Shorts
LONG_WEEKDAYS = {1, 4, 6}


def log(m):
    print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


def decide_format():
    override = os.environ.get("YT_FORMAT")
    if override in ("long", "short"):
        return override
    return "long" if date.today().weekday() in LONG_WEEKDAYS else "short"


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
    fmt = decide_format()
    os.environ["YT_ASPECT"] = "16:9" if fmt == "long" else "9:16"
    log(f"今日格式：{'長片 16:9 (2-3分鐘)' if fmt=='long' else 'Shorts 9:16 (~50秒)'}")

    import build_video  # 延後 import，讓 YT_ASPECT 生效

    recent = generate_script.load_recent()
    log(f"近期主題 {len(recent)} 個，生成新腳本...")
    script = generate_script.generate(recent, mode=fmt)
    log(f"主題：{script['topic']} ─ {script['title']}")

    tmp = tempfile.mkdtemp(prefix="ytvid_")
    try:
        out = os.path.join(tmp, "video.mp4")
        build_video.build_video(script, out, workdir=tmp)

        publish_at = scheduled_publish_at()
        log(f"上傳 YouTube（{'排程 '+publish_at if publish_at else PRIVACY}）...")
        desc = script.get("description", "")
        if fmt == "short":
            desc += "\n\n#shorts"
        vid = upload.upload(
            out,
            script["title"],
            desc,
            script.get("tags", []),
            privacy=PRIVACY,
            publish_at=publish_at,
        )

        generate_script.save_recent(recent, script["topic"])
        log(f"完成：https://youtu.be/{vid} ｜ {fmt} ｜ 主題 {script['topic']}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
