#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""連老闆頻道：知識短片成效 ＋ 主題被插斷與否的對照。

    python3 tools/yt_topic_check.py            # 全部
    python3 tools/yt_topic_check.py --days 14  # 只看發布滿 N 天的

純唯讀，用 config/youtube_oauth_lien.json 的 yt-analytics.readonly。

背景（2026-09-07）：四支知識短片排在 9/23、9/27、10/03、10/09，
剛好把「蝦」主題的兩支短片插斷、「蠔」主題沒有，形成一組現成對照。
⚠️ 每組各只有 1 支長片，且蝦與蠔本來熱度基準就不同——**能給方向，不能當結論**。
"""
import argparse, datetime, json, pathlib, re, sys, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
KNOWLEDGE = {"hm23abWZUKg": "冰箱", "K0LAveoJq8c": "鮪魚",
             "hFExnzAqzns": "魚探機", "sccOXoMvA6Y": "光之城"}
# 主題對照：被插斷 vs 連續
TOPICS = {"蝦（被知識片插斷）": ["虎蝦", "這隻蝦", "吃完一隻"],
          "蠔（連續）": ["撬開的生蠔", "生蠔開不開", "生蠔為什麼"]}


def token():
    """用 refresh token 換 access token。純唯讀用途。"""
    c = json.loads((ROOT / "config/youtube_oauth_lien.json").read_text())
    body = urllib.parse.urlencode({
        "client_id": c["client_id"],
        "client_secret": c["client_secret"],
        "refresh_token": c["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body)
    return json.loads(urllib.request.urlopen(req).read())["access_token"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7,
                    help="只列發布滿幾天的影片（預設 7）")
    a = ap.parse_args()
    at = token()

    def get(url, **q):
        r = urllib.request.Request(url + "?" + urllib.parse.urlencode(q),
                                   headers={"Authorization": f"Bearer {at}"})
        return json.loads(urllib.request.urlopen(r).read())

    YT = "https://www.googleapis.com/youtube/v3/"
    AN = "https://youtubeanalytics.googleapis.com/v2/reports"
    TW = datetime.timezone(datetime.timedelta(hours=8))
    now = datetime.datetime.now(TW)

    up = get(YT + "channels", part="contentDetails",
             mine="true")["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page = [], None
    while True:
        d = get(YT + "playlistItems", part="contentDetails", playlistId=up,
                maxResults=50, **({"pageToken": page} if page else {}))
        ids += [i["contentDetails"]["videoId"] for i in d["items"]]
        page = d.get("nextPageToken")
        if not page:
            break

    def secs(iso):
        m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
        h, mi, s = (int(x) if x else 0 for x in m.groups()) if m else (0, 0, 0)
        return h * 3600 + mi * 60 + s

    meta = {}
    for i in range(0, len(ids), 50):
        for v in get(YT + "videos", part="snippet,contentDetails,status",
                     id=",".join(ids[i:i + 50]))["items"]:
            if v["status"].get("publishAt"):
                continue                      # 還沒發的不算
            dt = datetime.datetime.fromisoformat(
                v["snippet"]["publishedAt"].replace("Z", "+00:00")).astimezone(TW)
            meta[v["id"]] = (dt, secs(v["contentDetails"]["duration"]),
                             v["snippet"]["title"])

    rep = get(AN, ids="channel==MINE", startDate="2026-06-01",
              endDate=now.strftime("%Y-%m-%d"), metrics="views,averageViewPercentage",
              dimensions="video", sort="-views", maxResults=200)
    stats = {r[0]: (r[1], r[2]) for r in rep.get("rows", [])}

    def line(vid, tag=""):
        dt, sec, t = meta[vid]
        age = (now - dt).days
        vw, pct = stats.get(vid, (0, 0))
        kind = "長片" if sec > 180 else "Shorts"
        return f"  {dt:%m/%d} {kind:6s} {age:>3d}天 {vw:>6,} 次 {pct:>5.1f}% {tag}{t[:30]}"

    print(f"※ 資料時間 {now:%Y-%m-%d %H:%M}（台灣）\n")
    print("=== 知識短片（新系列）===")
    got = [v for v in KNOWLEDGE if v in meta and (now - meta[v][0]).days >= a.days]
    if not got:
        print(f"  尚無發布滿 {a.days} 天的知識短片")
    for v in sorted(got, key=lambda x: meta[x][0]):
        print(line(v, "🆕 "))
    if got:
        vs = [stats.get(v, (0, 0))[0] for v in got]
        print(f"  → 中位 {sorted(vs)[len(vs)//2]:,} 次")
        print("     對照：破除迷思型約 1,400+／單純挑選知識約 200~400")

    print("\n=== 主題被插斷 vs 連續 ===")
    for label, keys in TOPICS.items():
        print(f"\n{label}")
        for k in keys:
            for v, (dt, sec, t) in sorted(meta.items(), key=lambda x: x[1][0]):
                if k in t and (now - dt).days >= a.days:
                    print(line(v))
    print("\n⚠️ 每組各只有 1 支長片，且蝦與蠔熱度基準不同——能給方向，不能當結論。")


if __name__ == "__main__":
    main()
