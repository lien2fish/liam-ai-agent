#!/usr/bin/env python3
"""一次上傳多支影片並自動排出發布時間表。

用法：
  # 每 2 天一支 18:00（甜點頻道的節奏，--every 預設就是 2）
  python3 tools/yt_batch_schedule.py 成品/千層蛋糕研發日記 \\
      --profile dessert --start "2026-08-19 18:00"

  # 每週固定星期，如二、五
  python3 tools/yt_batch_schedule.py a.mp4 b.mp4 --profile dessert \\
      --start "2026-08-19 18:00" --days tue,fri

  # 用排好的時間表（可讓多支同一天發）
  python3 tools/yt_batch_schedule.py --plan dessert/千層排程.json --profile dessert

  --dry-run 只印時間表不上傳。給資料夾＝取底下 mp4 依檔名排序；
  給多個檔名＝照你打的順序排。文案與封面沿用 <片名>_發文案.md／_封面.jpg。

已上傳過的檔案記在資料夾裡的 .yt_uploaded_<profile>.json，中斷後重跑會自動跳過。
"""
import argparse, json, os, sys
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(REPO, "youtube_auto"))

import upload as yt
from yt_upload import (
    SHORTS_MAX_SEC,
    TW,
    desc_override,
    find_thumb,
    probe,
    publish_at_utc,
    read_desc,
)

WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
DAILY_UPLOAD_CAP = (
    6  # videos.insert 1600 單位／預設配額 10,000 一天，超過就 quotaExceeded
)


def collect(paths):
    vids = []
    for p in paths:
        if os.path.isdir(p):
            vids += [
                os.path.join(p, f)
                for f in sorted(os.listdir(p))
                if f.lower().endswith(".mp4")
            ]
        elif os.path.isfile(p):
            vids.append(p)
        else:
            raise SystemExit(f"❌ 找不到：{p}")
    return vids


def slots(start, n, days, every):
    """產生 n 個發布時刻（台灣時間 datetime）。"""
    if days:
        want = {WEEKDAYS[d.strip().lower()] for d in days.split(",")}
        out, cur = [], start
        while len(out) < n:
            if cur.weekday() in want and cur >= start:
                out.append(cur)
            cur += timedelta(days=1)
        return out
    return [start + timedelta(days=every * i) for i in range(n)]


def state_path(video, profile):
    return os.path.join(
        os.path.dirname(os.path.abspath(video)), f".yt_uploaded_{profile}.json"
    )


def load_state(videos, profile):
    done = {}
    for v in videos:
        p = state_path(v, profile)
        if os.path.exists(p):
            done.update(json.load(open(p, encoding="utf-8")))
    return done


def save_state(video, profile, key, vid):
    p = state_path(video, profile)
    d = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    d[key] = vid
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def plan_one(video):
    w, h, dur = probe(video)
    is_short = h > w and dur <= SHORTS_MAX_SEC
    stem = os.path.splitext(video)[0]
    md = f"{stem}_發文案.md"
    file_title, desc, tags = read_desc(md) if os.path.exists(md) else (None, "", [])
    title = file_title or os.path.basename(stem)
    ov = desc_override(video)
    if ov:
        desc = ov
    if is_short and "#shorts" not in desc.lower():
        desc = (desc + "\n\n#shorts").strip()
    # Shorts 不另外設封面：<片名>_封面.jpg 是壓進影片開頭那 1 秒的直式封面卡，
    # 不是 YouTube 縮圖，直立的它也當不成縮圖，一律用影片畫面。
    return dict(
        video=video, title=title, desc=desc, tags=tags,
        is_short=is_short, dur=dur, thumb=None if is_short else find_thumb(video),
    )  # fmt: skip


def main():
    p = argparse.ArgumentParser()
    p.add_argument("paths", nargs="*", help="資料夾或影片檔（多個檔＝照順序排程）")
    p.add_argument("--profile", required=True, help="憑證組／頻道，如 dessert")
    p.add_argument(
        "--plan", help='排程表 JSON：[{"video":路徑, "at":"YYYY-MM-DD HH:MM"}]'
    )
    p.add_argument("--start", help="第一支發布時間，台灣時間 'YYYY-MM-DD HH:MM'")
    p.add_argument(
        "--max",
        type=int,
        default=DAILY_UPLOAD_CAP,
        help=f"這次最多傳幾支，預設 {DAILY_UPLOAD_CAP}（一天的配額上限）",
    )
    p.add_argument("--days", help="每週固定星期，逗號分隔，如 tue,fri")
    p.add_argument(
        "--every", type=int, default=2, help="每隔幾天一支（未給 --days 時生效）"
    )
    p.add_argument("--dry-run", action="store_true", help="只印時間表，不上傳")
    a = p.parse_args()

    cred = os.path.join(REPO, "config", f"youtube_oauth_{a.profile}.json")
    if not os.path.exists(cred):
        raise SystemExit(
            f"❌ 找不到憑證 {cred}\n"
            f"　 先跑：python3 youtube_auto/oauth_setup.py --profile {a.profile}"
        )

    if a.plan:
        rows = json.load(open(a.plan, encoding="utf-8"))
        videos = [r["video"] for r in rows]
        missing = [v for v in videos if not os.path.exists(v)]
        if missing:
            raise SystemExit("❌ 排程表裡這些檔案不存在：\n  " + "\n  ".join(missing))
        at = {r["video"]: r["at"] for r in rows}
    else:
        if not a.paths or not a.start:
            raise SystemExit("❌ 沒給 --plan 時，paths 與 --start 都必填")
        videos = collect(a.paths)
        at = None

    done = load_state(videos, a.profile)
    todo = [v for v in videos if os.path.basename(v) not in done]
    if not todo:
        raise SystemExit("全部都上傳過了（見 .yt_uploaded_*.json）")

    if at:
        times = [
            datetime.strptime(at[v], "%Y-%m-%d %H:%M").replace(tzinfo=TW) for v in todo
        ]
        past = [
            f"{os.path.basename(v)} {at[v]}"
            for v, t in zip(todo, times)
            if t <= datetime.now(TW)
        ]
        if past:
            raise SystemExit("❌ 這些排程時間已過：\n  " + "\n  ".join(past))
    else:
        start = datetime.strptime(a.start, "%Y-%m-%d %H:%M").replace(tzinfo=TW)
        if start <= datetime.now(TW):
            raise SystemExit(f"❌ 起始時間 {a.start} 已過")
        times = slots(start, len(todo), a.days, a.every)

    plans = [plan_one(v) for v in todo]

    print(
        f"頻道：{a.profile}　共 {len(plans)} 支"
        + (f"（已跳過 {len(videos) - len(todo)} 支上傳過的）" if done else "")
    )
    print("-" * 72)
    for pl, t in zip(plans, times):
        kind = "Shorts" if pl["is_short"] else "長片　"
        cover = "＋封面" if pl["thumb"] else ""
        print(
            f"{t:%Y-%m-%d(%a) %H:%M}　{kind}　{pl['dur']:>6.0f}s　{pl['title']}{cover}"
        )
    print("-" * 72)

    if len(plans) > a.max:
        print(
            f"⚠️ 一天配額只夠 {DAILY_UPLOAD_CAP} 支（每支上傳吃 1600 單位／每日 10,000）。"
            f"這次只傳前 {a.max} 支，剩下 {len(plans) - a.max} 支"
            "明天重跑同一行指令會接續。"
        )
    if a.dry_run:
        return
    if input("\n確認上傳？(y/N) ").strip().lower() != "y":
        raise SystemExit("已取消")

    for pl, t in zip(plans[: a.max], times[: a.max]):
        name = os.path.basename(pl["video"])
        try:
            vid = yt.upload(
                pl["video"], pl["title"], pl["desc"], pl["tags"],
                privacy="private",
                publish_at=publish_at_utc(f"{t:%Y-%m-%d %H:%M}"),
                profile=a.profile,
            )  # fmt: skip
        except Exception as e:
            print(f"❌ {name}：{e}")
            print("　 已上傳的有記錄，排除問題後重跑同一行指令即可接續。")
            raise SystemExit(1)
        save_state(pl["video"], a.profile, name, vid)
        print(f"✅ {t:%m-%d %H:%M}　{pl['title']}　→ {vid}")
        if pl["thumb"]:
            # 影片本身已經上傳成功，縮圖失敗不該讓整批中斷（常見＝頻道未做電話驗證，403）
            try:
                yt.set_thumbnail(vid, pl["thumb"], profile=a.profile)
            except Exception as e:
                body = e.read().decode()[:200] if hasattr(e, "read") else ""
                print(f"⚠️ 縮圖設定失敗（{e}）{body}")
                print(f"　 手動上傳：https://studio.youtube.com/video/{vid}/edit")

    left = len(plans) - a.max
    if left > 0:
        print(f"\n今天的配額用完了，還有 {left} 支。明天重跑同一行指令即可接續。")


if __name__ == "__main__":
    main()
