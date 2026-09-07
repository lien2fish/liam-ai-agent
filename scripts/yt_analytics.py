#!/usr/bin/env python3
"""YouTube 流量來源與留存分析——公開統計看不到的那一半。

    python3 scripts/yt_analytics.py --profile lien [--days 28] [--save]

前置兩件事，缺一就 403：
  1. Google Cloud Console 啟用 YouTube Analytics API
  2. python3 youtube_auto/oauth_setup.py --profile <名稱> --analytics 重新授權

Data API 給的是「多少人看過」，這支給的是「從哪來、看到第幾秒關掉」。
"""
import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"
DATA = "https://www.googleapis.com/youtube/v3"

SOURCE_NAMES = {
    "SHORTS": "Shorts 動態",
    "SUBSCRIBER": "訂閱／首頁推薦",
    "RELATED_VIDEO": "相關影片",
    "YT_SEARCH": "YouTube 搜尋",
    "NO_LINK_OTHER": "直接開啟／不明",
    "EXT_URL": "站外連結",
    "YT_CHANNEL": "頻道頁",
    "PLAYLIST": "播放清單",
    "NOTIFICATION": "通知",
    "YT_OTHER_PAGE": "YouTube 其他頁面",
    "ADVERTISING": "廣告",
    "END_SCREEN": "結束畫面",
    "HASHTAGS": "主題標籤",
    "SOUND_PAGE": "音訊頁面",
}


def access_token(profile):
    path = os.path.join(REPO, "config", f"youtube_oauth_{profile}.json")
    if not os.path.exists(path):
        raise SystemExit(
            f"❌ 找不到 {path}\n　 先跑：python3 youtube_auto/oauth_setup.py --profile {profile} --analytics"
        )
    c = json.load(open(path))
    body = urllib.parse.urlencode(
        {
            "client_id": c["client_id"],
            "client_secret": c["client_secret"],
            "refresh_token": c["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode()
    return json.load(
        urllib.request.urlopen("https://oauth2.googleapis.com/token", body, timeout=20)
    )["access_token"]


def get(url, token, params):
    req = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        msg = json.loads(e.read().decode()).get("error", {}).get("message", "")
        if "has not been used in project" in msg or "is disabled" in msg:
            raise SystemExit(
                "❌ 專案還沒啟用 YouTube Analytics API。\n　 到 Console 啟用後再跑一次（免費）。"
            )
        if e.code == 403 and "insufficient" in msg.lower():
            raise SystemExit(
                "❌ 憑證沒有 Analytics 權限。\n　 跑：python3 youtube_auto/oauth_setup.py --profile <名稱> --analytics"
            )
        raise SystemExit(f"❌ HTTP {e.code}：{msg}")


def report(token, start, end, **kw):
    return get(
        ANALYTICS,
        token,
        {"ids": "channel==MINE", "startDate": start, "endDate": end, **kw},
    )


def rows(res):
    return res.get("rows", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="lien")
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--save", action="store_true", help="另存到 reports/")
    a = ap.parse_args()

    token = access_token(a.profile)
    end = datetime.now().date() - timedelta(days=1)  # 當天資料未結算
    start = end - timedelta(days=a.days - 1)
    s, e = start.isoformat(), end.isoformat()

    total = rows(
        report(
            token,
            s,
            e,
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost",
        )
    )
    src = rows(
        report(
            token,
            s,
            e,
            metrics="views,averageViewDuration",
            dimensions="insightTrafficSourceType",
            sort="-views",
        )
    )
    dev = rows(
        report(token, s, e, metrics="views", dimensions="deviceType", sort="-views")
    )
    vids = rows(
        report(
            token,
            s,
            e,
            metrics="views,averageViewPercentage,averageViewDuration,subscribersGained",
            dimensions="video",
            sort="-views",
            maxResults=15,
        )
    )

    titles = {}
    if vids:
        ids = ",".join(r[0] for r in vids)
        for it in get(f"{DATA}/videos", token, {"part": "snippet", "id": ids})["items"]:
            titles[it["id"]] = it["snippet"]["title"]

    L = [f"# 📊 YouTube 流量分析（{a.profile}）{s} ~ {e}", ""]
    if total:
        v, mins, avgdur, avgpct, gained, lost = total[0]
        L += [
            f"> 觀看 **{int(v):,}**｜總觀看時長 **{int(mins):,} 分鐘**｜"
            f"平均看完 **{avgpct:.1f}%**（{int(avgdur)} 秒）｜訂閱 **+{int(gained)} / −{int(lost)}**",
            "",
        ]

    L += [
        "## 流量從哪來",
        "",
        "| 來源 | 觀看 | 佔比 | 平均觀看秒數 |",
        "|------|------|------|------|",
    ]
    tv = sum(r[1] for r in src) or 1
    for name, views, dur in src:
        L.append(
            f"| {SOURCE_NAMES.get(name, name)} | {int(views):,} | {views / tv * 100:.1f}% | {int(dur)} |"
        )

    L += ["", "## 裝置", "", "| 裝置 | 觀看 | 佔比 |", "|------|------|------|"]
    dv = sum(r[1] for r in dev) or 1
    for name, views in dev:
        L.append(f"| {name} | {int(views):,} | {views / dv * 100:.1f}% |")

    L += [
        "",
        "## 單支影片留存",
        "",
        "| 影片 | 觀看 | 看完比例 | 平均秒數 | 訂閱 |",
        "|------|------|------|------|------|",
    ]
    for vid, views, pct, dur, gained in vids:
        L.append(
            f"| {titles.get(vid, vid)[:34]} | {int(views):,} | {pct:.1f}% | {int(dur)} | +{int(gained)} |"
        )

    out = "\n".join(L)
    print(out)
    if a.save:
        d = os.path.join(REPO, "reports")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"yt流量分析_{a.profile}_{end}.md")
        open(path, "w", encoding="utf-8").write(out + "\n")
        print(f"\n✅ 已存 {path}")


if __name__ == "__main__":
    main()
