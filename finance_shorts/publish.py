#!/usr/bin/env python3
"""金錢怪物上片：產生說明欄 → 排程上傳 → 驗收 → LINE 通知 Lien。

    python3 finance_shorts/publish.py jp-01 --dry-run        # 只印說明欄，不上傳
    python3 finance_shorts/publish.py jp-01                  # 排程隔天 18:00 公開
    python3 finance_shorts/publish.py jp-01 --at "2026-10-23 18:00"
    python3 finance_shorts/publish.py tw-01 --short a --dry-run   # Shorts（長片要先上傳）

每集的上片資料寫在 finance_shorts/<集>/youtube.json：
    video     成品路徑（相對 finance_shorts/）
    summary   說明欄第一段
    chapters  [[句子索引, "章節名"], ...]，第一個必須是 0
    sources   資料來源（每項一行）
    notes     額外聲明（每項一行，例如舊示威畫面）
    hashtags  說明欄最後一行的 hashtag（不含 #）
    tags      YouTube 標籤

Shorts 的上片資料寫在 <集>/shorts.json 每支的 "yt"：title／summary／hashtags／tags。
成品是 <集>/renders/short_<id>.mp4；資料來源只列用到的句子所引用的事實。
說明欄附長片連結（長片要先上傳）；長片沒公開的寫 "long": null 當獨立 Short，要用 --at 指定時間。
預設發布時間跟長片對齊：第 1 支同時、之後每支晚 2 天（RUNBOOK：B、C 各隔一個發片日）。

發布規則（Lien 2026-10-22 定）：排程公開＋LINE 傳連結，他回「停」就撤，沒回就照發。
不勾 AI 合成內容、不設自訂封面。
"""

import argparse, datetime, json, re, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "youtube_auto"))
from upload import upload  # noqa: E402

TW = datetime.timezone(datetime.timedelta(hours=8))
PROFILE = "fortune"
# ~/bin/gh 會自動帶 keychain 的 PAT；Homebrew 的 gh 沒登入，排程環境的 PATH 也不一定有 ~/bin
GH = str(Path.home() / "bin/gh") if (Path.home() / "bin/gh").exists() else "gh"
MAX_HASHTAGS = 15  # 標題＋說明合計超過 15 個，整支影片的 hashtag 全部失效


def mmss(t):
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def line_starts(ep_dir, speed):
    """成品裡每句旁白開始的秒數。渲染時間軸除以倍速就是成品時間。"""
    html = (ep_dir / "index.html").read_text()
    starts = {
        int(n) - 1: float(s)
        for s, n in re.findall(
            r'<audio[^>]*data-start="([0-9.]+)"[^>]*src="audio/l(\d+)\.mp3"', html
        )
    }
    first = starts[0]
    return {i: max(0.0, (s - first) / speed) for i, s in starts.items()}


YT_CC = "https://creativecommons.org/licenses/by/3.0/"  # YouTube「創用 CC」＝CC BY 3.0


def credits(ep_dir, only=None):
    """片中實際用到的照片與 CC 影片，作者標註是授權條件，一定要列。
    only：Short 實際用到的素材（make_shorts 產的 assets.json），不給就是整集。"""
    html = (ep_dir / "index.html").read_text()
    used = sorted(set(re.findall(r"(bg|broll)/([A-Za-z0-9_.-]+)", html)))
    if only is not None:
        stems = {f"{k}/{f.rsplit('.', 1)[0]}" for k, f in used}
        if only - stems:
            sys.exit(f"❌ Short 用到的素材在長片裡找不到，授權會漏列：{sorted(only - stems)}")
        used = [(k, f) for k, f in used if f"{k}/{f.rsplit('.', 1)[0]}" in only]
    bg = json.loads((ROOT / "shared/bg/credits.json").read_text())
    br = json.loads((ROOT / "shared/broll/credits.json").read_text())
    photos, videos, missing = [], [], []
    for kind, f in used:
        name = f.rsplit(".", 1)[0]
        c = (bg if kind == "bg" else br).get(name)
        if not c:
            missing.append(f"{kind}/{f}")
            continue
        if kind == "bg":
            artist = c["artist"].replace(
                "Unknown authorUnknown author", "Unknown author"
            )
            lic = c["license"] + (f"（{c['license_url']}）" if c.get("license_url") else "")
            line = f"・{artist}／{lic}／{c['page']}"
            bucket = photos
        else:
            # CC 影片的原標題可能自帶 #hashtag，抄進來會讓總數破 15 而全部失效
            title = re.sub(r"#(\w)", r"\1", c["title"])
            line = f"・{c['channel']}〈{title}〉／CC BY 3.0／{c['url']}"
            bucket = videos
        if line not in bucket:
            bucket.append(line)
    if missing:
        sys.exit(f"❌ 這些素材查不到授權紀錄，不能上片：{missing}")
    return photos, videos


def check(title, desc, tags):
    n_tags = len(re.findall(r"#\w+", title + "\n" + desc))
    problems = []
    if n_tags > MAX_HASHTAGS:
        problems.append(f"hashtag {n_tags} 個，超過 {MAX_HASHTAGS}")
    if len(title) > 100:
        problems.append(f"標題 {len(title)} 字，超過 100")
    if len(desc) > 5000:
        problems.append(f"說明欄 {len(desc)} 字，超過 5000")
    if sum(len(t) + 2 for t in tags) > 500:
        problems.append("標籤總長超過 500")
    if any(c in desc + title for c in "<>"):
        problems.append("標題或說明欄有 < >，YouTube 會拒收")
    if problems:
        sys.exit("❌ " + "；".join(problems))
    if len(title) > 30:
        print(f"⚠️ 標題 {len(title)} 字，推薦版位約只顯示 30 字")
    return n_tags


def credit_block(ep_dir, only=None):
    photos, videos = credits(ep_dir, only)
    out = []
    if photos:
        out.append("📷 畫面照片（Wikimedia Commons；已裁切、加上文字）\n" + "\n".join(photos))
    if videos:
        out.append(
            f"🎬 畫面影片（YouTube 創用 CC 姓名標示 3.0 {YT_CC} ；已裁切、剪輯、加上文字）\n"
            + "\n".join(videos)
        )
    return out


def short_sources(ep_id, sh):
    """只列這支 Short 用到的句子所引用的事實來源。"""
    lines = json.loads((ROOT / "scripts.json").read_text())["episodes"][ep_id]["lines"]
    facts = json.loads((ROOT / "facts.json").read_text())["facts"]
    names = []
    for item in sh["lines"]:
        n = item if isinstance(item, int) else item["n"]
        for fid in lines[n - 1].get("facts", []):
            for src in facts[fid].get("sources", []):
                if src["name"] not in names:
                    names.append(src["name"])
    return names


def build_short(ep_id, sid, dry_run):
    """shorts.json 的 "long"：{"id","title"} 指定要導流的長片；null＝獨立 Short（長片沒公開就用這個）。
    沒寫 "long" 就讀 youtube.json（同集長片走 publish.py 上傳的情況）。"""
    ep_dir = ROOT / ep_id
    cfg = json.loads((ep_dir / "shorts.json").read_text())
    ids = [x["id"] for x in cfg["shorts"]]
    if sid not in ids:
        sys.exit(f"❌ shorts.json 沒有 {sid}，現有 {ids}")
    sh = cfg["shorts"][ids.index(sid)]
    if sh.get("video_id"):
        sys.exit(f"❌ short {sid} 已經上傳過：https://youtu.be/{sh['video_id']}")
    yt = sh["yt"]
    default_when = None
    if "long" in cfg:
        long = cfg["long"]
    else:
        long_yt = json.loads((ep_dir / "youtube.json").read_text())
        long = {"id": long_yt.get("video_id"), "title": long_yt.get("title", "")}
        if not long["id"] and not dry_run:
            sys.exit("❌ 長片還沒上傳，Shorts 說明欄要放完整版連結，先傳長片")
        if long_yt.get("publish_at"):
            base = datetime.datetime.strptime(long_yt["publish_at"], "%Y-%m-%dT%H:%M:%SZ")
            base = base.replace(tzinfo=datetime.timezone.utc).astimezone(TW)
            default_when = base + datetime.timedelta(days=2 * ids.index(sid))
    af = ep_dir / "renders" / f"short_{sid}.assets.json"
    if not af.exists():
        sys.exit(f"❌ 沒有 {af.name}，請先用 make_shorts.py 重產這支")
    assets = set(json.loads(af.read_text()))
    sources = short_sources(ep_id, sh)
    if not sources:
        sys.exit("❌ 這支 Short 用到的句子沒有對到任何事實來源")
    parts = [yt["summary"]]
    if long:
        link = f"https://youtu.be/{long['id']}" if long.get("id") else "（長片上傳後自動填入）"
        parts.append(f"▶ 完整版：{long['title']}\n{link}")
    parts += [
        "📌 資料來源\n" + "\n".join(f"・{s}" for s in sources),
        "⚠️ 本影片為公開資訊整理，非投資建議。旁白為 AI 合成語音。",
        *credit_block(ep_dir, assets),
        " ".join(f"#{h}" for h in yt["hashtags"]),
    ]
    desc = "\n\n".join(parts)
    title = yt["title"]
    n_tags = check(title, desc, yt["tags"])
    video = ep_dir / "renders" / f"short_{sid}.mp4"

    def save(vid, publish_at):
        # 重新讀檔再寫，避免蓋掉別支剛寫入的 video_id；暫存檔＋替換，寫到一半不會壞檔
        path = ep_dir / "shorts.json"
        latest = json.loads(path.read_text())
        for x in latest["shorts"]:
            if x["id"] == sid:
                x.update({"video_id": vid, "publish_at": publish_at})
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(latest, ensure_ascii=False, indent=1))
        tmp.replace(path)

    return yt, title, desc, n_tags, video, default_when, save


def build(ep_id):
    ep = json.loads((ROOT / "scripts.json").read_text())["episodes"][ep_id]
    ep_dir = ROOT / ep_id
    yt = json.loads((ep_dir / "youtube.json").read_text())
    starts = line_starts(ep_dir, ep.get("speed", 1))

    chapters = yt["chapters"]
    if chapters[0][0] != 0 or len(chapters) < 3:
        sys.exit("❌ 章節第一個要從第 0 句開始，且至少 3 個")
    times = [0.0] + [starts[i] for i, _ in chapters[1:]]
    for a, b in zip(times, times[1:]):
        if b - a < 10:
            sys.exit(
                f"❌ 章節間隔不到 10 秒（{mmss(a)} → {mmss(b)}），YouTube 會整組不認"
            )
    chap = "\n".join(f"{mmss(t)} {name}" for t, (_, name) in zip(times, chapters))

    parts = [
        yt["summary"],
        chap,
        "📌 資料來源\n" + "\n".join(f"・{s}" for s in yt["sources"]),
    ]
    parts.append(
        "\n".join(
            ["⚠️ 本影片為公開資訊整理，非投資建議。旁白為 AI 合成語音。"]
            + [f"⚠️ {n}" for n in yt.get("notes", [])]
        )
    )
    parts += credit_block(ep_dir)
    parts.append(" ".join(f"#{h}" for h in yt["hashtags"]))
    desc = "\n\n".join(parts)

    title = yt.get("title", ep["title"])
    n_tags = check(title, desc, yt["tags"])
    return yt, title, desc, n_tags


def token():
    c = json.loads((REPO / f"config/youtube_oauth_{PROFILE}.json").read_text())
    d = urllib.parse.urlencode(
        {
            **{k: c[k] for k in ("client_id", "client_secret", "refresh_token")},
            "grant_type": "refresh_token",
        }
    ).encode()
    return json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", d))[
        "access_token"
    ]


def verify(vid, title, desc, tags):
    """驗收＝processingStatus succeeded，且標題、說明、標籤都跟送出的一樣。"""
    h = {"Authorization": "Bearer " + token()}
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,status,processingDetails&id={vid}"
    for _ in range(60):
        x = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=h)))[
            "items"
        ][0]
        status = x["processingDetails"]["processingStatus"]
        if status != "processing":
            break
        time.sleep(15)
    s = x["snippet"]
    checks = {
        "處理完成": status == "succeeded",
        "標題": s["title"] == title,
        "說明": s["description"] == desc,
        "標籤": sorted(s.get("tags", [])) == sorted(tags),
        "排程": bool(x["status"].get("publishAt")),
    }
    for k, ok in checks.items():
        print(f"  {'✅' if ok else '❌'} {k}")
    return all(checks.values()), x["status"].get("publishAt")


def line(text):
    r = subprocess.run(
        [GH, "workflow", "run", "line_notify.yml", "-f", f"text={text}"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    print(
        "📱 已觸發 LINE 通知"
        if r.returncode == 0
        else f"⚠️ LINE 通知沒送出：{r.stderr.strip()}"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep")
    ap.add_argument("--at", help="台灣時間 'YYYY-MM-DD HH:MM'，預設隔天 18:00")
    ap.add_argument("--short", help="上傳 shorts.json 裡這個 id 的 Short")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    tomorrow = (datetime.datetime.now(TW) + datetime.timedelta(days=1)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )
    if a.short:
        yt, title, desc, n_tags, video, default_when, save = build_short(
            a.ep, a.short, a.dry_run
        )
        kind = "Short"
    else:
        yt, title, desc, n_tags = build(a.ep)
        video, default_when, kind = ROOT / yt["video"], None, "新片"

        def save(vid, publish_at):
            yt.update({"video_id": vid, "publish_at": publish_at})
            (ROOT / a.ep / "youtube.json").write_text(
                json.dumps(yt, ensure_ascii=False, indent=1)
            )

    if a.at:
        when = datetime.datetime.strptime(a.at, "%Y-%m-%d %H:%M").replace(tzinfo=TW)
    elif default_when:
        when = default_when
    elif a.short and a.dry_run:
        when = tomorrow
        print("⚠️ 長片還沒排程，先用隔天 18:00 預覽")
    elif a.short:
        sys.exit("❌ 長片沒有排程時間可對齊，請用 --at 指定")
    else:
        when = tomorrow
    if when <= datetime.datetime.now(TW) + datetime.timedelta(hours=1):
        sys.exit(f"❌ 發布時間 {when:%m/%d %H:%M} 太近，Lien 沒有時間否決")

    print(
        f"標題：{title}\n發布：{when:%Y-%m-%d %H:%M}（台灣）\nhashtag {n_tags} 個、說明 {len(desc)} 字\n"
    )
    if a.dry_run:
        print(desc)
        return

    if not video.exists():
        sys.exit(f"❌ 找不到成品：{video}")
    if a.short:
        w, h, dur = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
             "stream=width,height:format=duration", "-of", "default=nw=1:nk=1", str(video)],
            capture_output=True, text=True,
        ).stdout.split()
        if int(w) >= int(h) or float(dur) > 180:
            sys.exit(f"❌ 不符合 Shorts 條件（{w}×{h}、{float(dur):.0f} 秒）：要直式且 ≤180 秒")
    publish_at = when.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    vid = upload(
        str(video),
        title,
        desc,
        yt["tags"],
        privacy="private",
        publish_at=publish_at,
        synthetic_media=False,
        profile=PROFILE,
    )
    print(f"⬆️ 已上傳 https://youtu.be/{vid}（若下面寫檔失敗，不要重跑，手動補這個 ID）")
    save(vid, publish_at)

    ok, _ = verify(vid, title, desc, yt["tags"])
    if not ok:
        line(
            f"🔴 金錢怪物{kind}驗收沒過：{title}\nhttps://youtu.be/{vid}\n已排程但請先看一下"
        )
        sys.exit(1)
    line(
        f"📺 金錢怪物{kind}排好了\n{title}\n{when:%m/%d %H:%M} 自動公開\nhttps://youtu.be/{vid}\n\n不想發的話回「停」"
    )


if __name__ == "__main__":
    main()
