#!/usr/bin/env python3
"""把剪好的影片上傳到自己的 YouTube 頻道，可排定發布時間。

用法：
  python3 tools/yt_upload.py 成品/南寮漁港/香螺一斤一千五.mp4 \\
      --desc ~/Desktop/香螺一斤一千五_發文案.md \\
      --at "2026-08-07 18:00"

  --at 未給＝上傳為私人，你自己在 YouTube 決定何時發。
  標題未給＝用檔名（去副檔名）。9:16 且 ≤3 分鐘會自動加 #shorts。

憑證：--profile 決定用哪一組，預設 lien（連老闆-產地到餐桌），
讀 config/youtube_oauth_<profile>.json。新頻道先跑：
  python3 youtube_auto/oauth_setup.py --profile <名稱>
"""
import argparse, os, re, subprocess, sys
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
sys.path.insert(0, os.path.join(REPO, "youtube_auto"))

import upload as yt

DEFAULT_PROFILE = "lien"
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


def find_thumb(video_path):
    """成品慣例：封面與影片同目錄、檔名為 <片名>_封面.jpg／.png"""
    stem = os.path.splitext(video_path)[0]
    for ext in (".jpg", ".jpeg", ".png"):
        p = f"{stem}_封面{ext}"
        if os.path.exists(p):
            return p
    return None


def publish_at_utc(when):
    """'2026-08-07 18:00' (台灣) → RFC3339 UTC"""
    dt = datetime.strptime(when, "%Y-%m-%d %H:%M").replace(tzinfo=TW)
    if dt <= datetime.now(TW):
        raise SystemExit(f"❌ 排程時間 {when} 已過")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


SKIP_TAGS = {"shorts", "foryou", "fyp"}


def read_desc(path):
    """解析發文案 .md，回傳 (標題, 描述, 標籤)。兩種格式都吃：

    A 連老闆（IG/YouTube/TikTok 三段式）：取 YouTube 段的「- 標題：」「- 描述：」。
    B 甜點頻道：**標題** 下一行、**描述** 的 ``` 區塊、**Tags** 的逗號清單。

    標籤預設收集全檔 hashtag（不顯示於描述、只影響搜尋，多蒐無妨），
    B 格式有明列 Tags 就以那行為準。都對不上則整檔當描述。
    """
    text = open(path, encoding="utf-8").read().strip()
    tags = [
        t
        for t in re.findall(r"#(\w+)", text)
        if t.lower() not in SKIP_TAGS and not t.isdigit()
    ]
    tags = list(dict.fromkeys(tags))

    block = re.search(r"\*\*YouTube[^*]*\*\*(.*?)(?=\n\*\*|\Z)", text, re.S)
    if block:
        seg = block.group(1)
        title = re.search(r"-\s*標題：\s*(.+)", seg)
        desc = re.search(r"-\s*描述：\s*(.+)", seg)
        return (
            title.group(1).strip() if title else None,
            desc.group(1).strip() if desc else seg.strip(),
            tags,
        )

    title = re.search(r"\*\*標題\*\*\s*\n+\s*(.+)", text)
    desc = re.search(r"\*\*描述\*\*\s*\n+```\w*\n(.*?)\n```", text, re.S)
    tagline = re.search(r"\*\*Tags\*\*\s*\n+\s*(.+)", text)
    if title or desc:
        if tagline:
            tags = [
                t.strip()
                for t in tagline.group(1).split(",")
                if t.strip() and t.strip().lower() not in SKIP_TAGS
            ]
        return (
            title.group(1).strip() if title else None,
            desc.group(1).strip() if desc else text,
            tags,
        )
    return None, text, tags


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--title")
    p.add_argument("--desc", help="發文案 .md 路徑")
    p.add_argument("--at", help="排定發布時間，台灣時間 'YYYY-MM-DD HH:MM'")
    p.add_argument("--tags", help="逗號分隔，覆寫發文案裡抓到的 hashtag")
    p.add_argument("--public", action="store_true", help="立刻公開（預設私人）")
    p.add_argument("--thumb", help="封面圖；未給則自動找 <片名>_封面.jpg/.png")
    p.add_argument("--no-thumb", action="store_true", help="不設封面")
    p.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help=f"憑證組／頻道，預設 {DEFAULT_PROFILE}（連老闆-產地到餐桌）",
    )
    a = p.parse_args()

    if not os.path.exists(a.video):
        raise SystemExit(f"❌ 找不到影片：{a.video}")
    cred = os.path.join(REPO, "config", f"youtube_oauth_{a.profile}.json")
    if not os.path.exists(cred):
        raise SystemExit(
            f"❌ 找不到憑證 {cred}\n"
            f"　 先跑：python3 youtube_auto/oauth_setup.py --profile {a.profile}"
        )

    w, h, dur = probe(a.video)
    is_short = h > w and dur <= SHORTS_MAX_SEC

    desc, tags, file_title = ("", [], None)
    if a.desc:
        file_title, desc, tags = read_desc(a.desc)
    title = a.title or file_title or os.path.splitext(os.path.basename(a.video))[0]
    if a.tags:
        tags = [t.strip() for t in a.tags.split(",") if t.strip()]
    if is_short and "#shorts" not in desc.lower():
        desc = (desc + "\n\n#shorts").strip()

    publish = publish_at_utc(a.at) if a.at else None
    privacy = "public" if a.public and not publish else "private"
    thumb = None if a.no_thumb else (a.thumb or find_thumb(a.video))

    print(f"影片　：{a.video}")
    print(f"頻道　：{a.profile}")
    print(f"規格　：{w}x{h} {dur:.1f}秒{'（Shorts）' if is_short else ''}")
    print(f"標題　：{title}")
    print(f"標籤　：{tags}")
    print(f"發布　：{'排程 ' + a.at + ' (台灣)' if publish else privacy}")
    if thumb and is_short:
        cover_note = f"{thumb}（⚠️ Shorts 需到 Studio 手動上傳，API 無效）"
    else:
        cover_note = thumb or "（無，將用影片畫面）"
    print(f"封面　：{cover_note}")
    print(f"描述　：{desc[:80]}{'...' if len(desc) > 80 else ''}")
    if input("\n確認上傳？(y/N) ").strip().lower() != "y":
        raise SystemExit("已取消")

    vid = yt.upload(
        a.video,
        title,
        desc,
        tags,
        privacy=privacy,
        publish_at=publish,
        profile=a.profile,
    )
    if thumb and is_short:
        # API 的 thumbnails/set 對 Shorts 會回 200 但不生效（靜默失敗），不如不呼叫
        print("⚠️ Shorts 不支援用 API 設縮圖，已跳過。要設封面請到 YouTube Studio：")
        print(f"   https://studio.youtube.com/video/{vid}/edit　←　上傳 {thumb}")
    elif thumb:
        yt.set_thumbnail(vid, thumb, profile=a.profile)


if __name__ == "__main__":
    main()
