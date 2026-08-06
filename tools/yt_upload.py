#!/usr/bin/env python3
"""把剪好的影片上傳到「連老闆-產地到餐桌」，可排定發布時間。

用法：
  python3 tools/yt_upload.py 成品/南寮漁港/香螺一斤一千五.mp4 \\
      --desc ~/Desktop/香螺一斤一千五_發文案.md \\
      --at "2026-08-07 18:00"

  --at 未給＝上傳為私人，你自己在 YouTube 決定何時發。
  標題未給＝用檔名（去副檔名）。9:16 且 ≤3 分鐘會自動加 #shorts。

憑證：config/youtube_oauth_lien.json（與 The Unknown Hour 分開，見 --setup）
"""
import argparse, os, re, subprocess, sys
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
sys.path.insert(0, os.path.join(REPO, "youtube_auto"))

import upload as yt

PROFILE = "lien"
TW = timezone(timedelta(hours=8))
SHORTS_MAX_SEC = 180  # 2024-10 起 Shorts 上限由 60 秒放寬到 3 分鐘


def probe(path):
    """回傳 (寬, 高, 秒數)。本機 ffmpeg 無 ffprobe，改解析 stderr。"""
    out = subprocess.run(["ffmpeg", "-i", path], capture_output=True, text=True).stderr
    wh = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", out)
    dur = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", out)
    if not wh or not dur:
        raise RuntimeError(f"讀不到影片規格：{path}")
    h, m, s = dur.groups()
    return int(wh.group(1)), int(wh.group(2)), int(h) * 3600 + int(m) * 60 + float(s)


def publish_at_utc(when):
    """'2026-08-07 18:00' (台灣) → RFC3339 UTC"""
    dt = datetime.strptime(when, "%Y-%m-%d %H:%M").replace(tzinfo=TW)
    if dt <= datetime.now(TW):
        raise SystemExit(f"❌ 排程時間 {when} 已過")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_desc(path):
    text = open(path, encoding="utf-8").read().strip()
    tags = re.findall(r"#(\w+)", text)
    return text, tags


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--title")
    p.add_argument("--desc", help="發文案 .md 路徑")
    p.add_argument("--at", help="排定發布時間，台灣時間 'YYYY-MM-DD HH:MM'")
    p.add_argument("--tags", help="逗號分隔，覆寫發文案裡抓到的 hashtag")
    p.add_argument("--public", action="store_true", help="立刻公開（預設私人）")
    a = p.parse_args()

    if not os.path.exists(a.video):
        raise SystemExit(f"❌ 找不到影片：{a.video}")

    w, h, dur = probe(a.video)
    is_short = h > w and dur <= SHORTS_MAX_SEC
    title = a.title or os.path.splitext(os.path.basename(a.video))[0]

    desc, tags = ("", [])
    if a.desc:
        desc, tags = read_desc(a.desc)
    if a.tags:
        tags = [t.strip() for t in a.tags.split(",") if t.strip()]
    if is_short and "#shorts" not in desc.lower():
        desc = (desc + "\n\n#shorts").strip()

    publish = publish_at_utc(a.at) if a.at else None
    privacy = "public" if a.public and not publish else "private"

    print(f"影片　：{a.video}")
    print(f"規格　：{w}x{h} {dur:.1f}秒{'（Shorts）' if is_short else ''}")
    print(f"標題　：{title}")
    print(f"標籤　：{tags}")
    print(f"發布　：{'排程 ' + a.at + ' (台灣)' if publish else privacy}")
    print(f"描述　：{desc[:80]}{'...' if len(desc) > 80 else ''}")
    if input("\n確認上傳？(y/N) ").strip().lower() != "y":
        raise SystemExit("已取消")

    yt.upload(
        a.video,
        title,
        desc,
        tags,
        privacy=privacy,
        publish_at=publish,
        profile=PROFILE,
    )


if __name__ == "__main__":
    main()
