#!/usr/bin/env python3
"""IG Reels 預約發布。Graph API 沒有 publishAt，所以自己排：影片放 R2、清單放私人 repo，
由 liam-scheduler 每 :00／:30 觸發 ig_reel_scheduled.yml，時間到才呼叫 API 發布。

  python3 instagram/reel_schedule.py add 影片.mp4 發文案.md "2026-11-03 18:00"
  python3 instagram/reel_schedule.py list
  python3 instagram/reel_schedule.py cancel <id>
  python3 instagram/reel_schedule.py probe <id>   # 只建 container 驗 IG 抓得到，不發布
  python3 instagram/reel_schedule.py run --queue ws/ig_schedule/queue.json   # workflow 用

⛔ IG 發出去 API 刪不掉，所以：
  - 呼叫 IG 前先把狀態改成 publishing 並推上 repo，推不上去就不發（避免兩次 run 都發）
  - 任何錯誤都不自動重試，改推 LINE 讓人決定
  - 超過原定時間 LATE_LIMIT 還沒發的不補發（晚上 18:00 的片隔天早上冒出來比沒發更糟）
"""
import json, os, re, secrets, subprocess, sys, tempfile, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
WORKER_DIR = os.path.join(REPO, "scheduler_worker")
LOCAL_QUEUE = os.path.expanduser("~/liam-workspace/ig_schedule/queue.json")

GRAPH = "https://graph.facebook.com/v19.0"
BUCKET = "ig-reels"
SCHEDULER = "https://liam-scheduler.lien2fish.workers.dev"
TW = timezone(timedelta(hours=8))
LATE_LIMIT = timedelta(hours=2)
MAX_BYTES = 300 * 1024 * 1024  # wrangler r2 object put 的上限
CAPTION_MAX, HASHTAG_MAX = 2200, 30


def sh(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"❌ {' '.join(cmd[:4])}…\n{r.stdout}{r.stderr}")
    return r.stdout


def probe(path):
    d = json.loads(
        sh(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    )  # fmt: skip
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    a = [s for s in d["streams"] if s["codec_type"] == "audio"]
    return {
        "duration": float(d["format"]["duration"]),
        "w": int(v["width"]),
        "h": int(v["height"]),
        "vcodec": v["codec_name"],
        "acodec": a[0]["codec_name"] if a else None,
    }


def read_caption(path):
    """發文案 .md 取「**IG …**」段落的 ``` 區塊；.txt 整檔當文案。對不上就停，不猜。"""
    text = open(path, encoding="utf-8").read().strip()
    if path.endswith(".txt"):
        return text
    m = re.search(r"\*\*IG[^*]*\*\*\s*\n+```\w*\n(.*?)\n```", text, re.S)
    if not m:
        raise SystemExit("❌ 文案檔找不到「**IG … 文案**」底下的 ``` 區塊")
    return m.group(1).strip()


# ---------- 清單（私人 repo） ----------


def load(qpath):
    return json.load(open(qpath)) if os.path.exists(qpath) else []


def git(ws, *args):
    return subprocess.run(["git", "-C", ws, *args], capture_output=True, text=True)


def save(qpath, items, msg):
    """寫入並推上去。推不上去回 False——呼叫 IG 之前一定要看這個結果。"""
    os.makedirs(os.path.dirname(qpath), exist_ok=True)
    with open(qpath, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
        f.write("\n")
    ws = os.path.dirname(os.path.dirname(qpath))
    rel = os.path.relpath(qpath, ws)
    git(ws, "add", rel)
    if git(ws, "commit", "-q", "-m", msg).returncode:
        return True  # 沒有變更
    for _ in range(3):
        if (
            git(ws, "pull", "-q", "--rebase").returncode == 0
            and git(ws, "push", "-q").returncode == 0
        ):
            return True
        time.sleep(5)
    return False


def pull(qpath):
    ws = os.path.dirname(os.path.dirname(qpath))
    r = git(ws, "pull", "-q", "--rebase")
    if r.returncode:
        raise SystemExit(f"❌ 私人 repo pull 失敗，先處理再排：\n{r.stderr}")


# ---------- R2 ----------


def wrangler(*args):
    return sh(["npx", "wrangler", *args], cwd=WORKER_DIR)


def public_base():
    out = wrangler("r2", "bucket", "dev-url", "get", BUCKET)
    m = re.search(r"https://pub-[\w-]+\.r2\.dev", out)
    if not m:
        raise SystemExit(f"❌ {BUCKET} 沒有開公開網址：\n{out}")
    return m.group(0)


def head(url):
    # Cloudflare 擋 urllib 預設 User-Agent（回 403），同 line_assistant/notify.py 的坑
    req = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": "liam-notify/1"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return int(r.headers.get("Content-Length", -1))


def r2_delete(key):
    """本機走 wrangler，Actions 走 liam-scheduler 的 /r2/delete（Actions 沒有 Cloudflare 憑證）。"""
    tok = os.environ.get("LINE_NOTIFY_TOKEN")
    if not tok:
        wrangler("r2", "object", "delete", f"{BUCKET}/{key}", "--remote")
        return
    req = urllib.request.Request(
        f"{SCHEDULER}/r2/delete?key={urllib.parse.quote(key)}",
        method="POST",
        headers={"Authorization": f"Bearer {tok}", "User-Agent": "liam-notify/1"},
    )
    urllib.request.urlopen(req, timeout=30)


# ---------- IG ----------


def creds():
    tok, ig = os.environ.get("IG_TOKEN"), os.environ.get("IG_ID")
    if tok and ig:
        return tok, ig
    c = json.load(open(os.path.join(REPO, "config", "instagram_config.json")))
    return c["long_lived_user_token"], c["ig_account_id"]


def get(url):
    return json.load(urllib.request.urlopen(url, timeout=60))


def post(path, params):
    req = urllib.request.Request(
        f"{GRAPH}/{path}", data=urllib.parse.urlencode(params).encode(), method="POST"
    )
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} {e.read().decode()[:300]}")


def container(tok, ig, item):
    cid = post(
        f"{ig}/media",
        {
            "media_type": "REELS",
            "video_url": item["url"],
            "caption": item["caption"],
            "share_to_feed": "true",
            "thumb_offset": "0",  # 第一格＝reel_maker 接上去的封面卡
            "access_token": tok,
        },
    )["id"]
    for i in range(60):
        time.sleep(5)
        st = get(f"{GRAPH}/{cid}?fields=status_code,status&access_token={tok}")
        print(f"  [{i * 5 + 5:>3}s] {st.get('status_code')}", flush=True)
        if st.get("status_code") == "FINISHED":
            return cid
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"IG 轉檔失敗：{st.get('status')}")
    raise RuntimeError("IG 轉檔逾時（5 分鐘）")


def notify(text):
    try:
        sys.path.insert(0, REPO)
        from line_assistant.notify import notify as n

        n(text)
    except Exception as e:
        print(f"（LINE 推播失敗：{e}）")


# ---------- 指令 ----------


def parse_at(s):
    at = datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=TW)
    if at.minute not in (0, 30):
        raise SystemExit("❌ 時間只能是 :00 或 :30（Worker 只在這兩個時間點檢查）")
    if at < datetime.now(TW) + timedelta(minutes=15):
        raise SystemExit("❌ 至少要排在 15 分鐘以後")
    return at


def cmd_add(video, caption_file, when, yes=False):
    at = parse_at(when)
    caption = read_caption(caption_file)
    info = probe(video)
    size = os.path.getsize(video)

    problems, warns = [], []
    if not 3 <= info["duration"] <= 900:
        problems.append(f"長度 {info['duration']:.1f} 秒（Reels 要 3~900 秒）")
    if size > MAX_BYTES:
        problems.append(f"檔案 {size / 1e6:.0f}MB 超過 300MB")
    if info["vcodec"] not in ("h264", "hevc"):
        problems.append(f"影像編碼 {info['vcodec']}（要 h264／hevc）")
    if info["acodec"] not in (None, "aac"):
        problems.append(f"音訊編碼 {info['acodec']}（要 aac）")
    if len(caption) > CAPTION_MAX:
        problems.append(f"文案 {len(caption)} 字超過 {CAPTION_MAX}")
    if len(re.findall(r"#\w+", caption)) > HASHTAG_MAX:
        problems.append(f"hashtag 超過 {HASHTAG_MAX} 個")
    if abs(info["w"] / info["h"] - 9 / 16) > 0.01:
        warns.append(f"比例 {info['w']}×{info['h']} 不是 9:16，IG 會裁切")

    pull(LOCAL_QUEUE)
    items = load(LOCAL_QUEUE)
    clash = [i for i in items if i["status"] == "pending" and i["at"] == at.isoformat()]
    if clash:
        problems.append(f"同一時間已排了 {clash[0]['video']}（{clash[0]['id']}）")

    print(
        f"影片：{os.path.basename(video)}  {info['w']}×{info['h']}  {info['duration']:.1f} 秒  {size / 1e6:.1f}MB"
    )
    print(f"發布：{at:%Y-%m-%d (%a) %H:%M} 台灣時間")
    print(f"文案（{len(caption)} 字）：\n{'-' * 40}\n{caption}\n{'-' * 40}")
    for w in warns:
        print(f"⚠️ {w}")
    if problems:
        raise SystemExit("❌ " + "\n❌ ".join(problems))
    if not yes and input("確定排程？發出去 API 刪不掉 [y/N] ").strip().lower() != "y":
        raise SystemExit("已取消")

    key = secrets.token_hex(16) + ".mp4"
    wrangler("r2", "object", "put", f"{BUCKET}/{key}", "--file", os.path.abspath(video),
             "--content-type", "video/mp4", "--remote")  # fmt: skip
    url = f"{public_base()}/{key}"
    got = head(url)
    if got != size:
        r2_delete(key)
        raise SystemExit(f"❌ 公開網址抓回 {got} bytes，本機是 {size}，已刪除上傳檔")

    item = {
        "id": key[:8],
        "at": at.isoformat(),
        "video": os.path.basename(video),
        "key": key,
        "url": url,
        "bytes": size,
        "duration": round(info["duration"], 2),
        "caption": caption,
        "status": "pending",
        "added": datetime.now(TW).isoformat(timespec="seconds"),
    }
    items.append(item)
    if not save(LOCAL_QUEUE, items, f"ig 排程：{item['video']} @ {at:%m-%d %H:%M}"):
        raise SystemExit(
            "❌ 清單推不上私人 repo——影片已在 R2，但雲端看不到這筆，修好再跑 push"
        )
    print(f"✅ 已排程 {item['id']}，公開網址已驗證（{got} bytes）")


def cmd_list():
    pull(LOCAL_QUEUE)
    items = sorted(load(LOCAL_QUEUE), key=lambda i: i["at"])
    if not items:
        print("（沒有排程）")
    for i in items:
        at = datetime.fromisoformat(i["at"])
        extra = i.get("permalink") or i.get("note") or ""
        print(
            f"{i['id']}  {at:%m-%d (%a) %H:%M}  {i['status']:<10} {i['video']}  {extra}"
        )


def find(items, iid):
    hit = [i for i in items if i["id"] == iid]
    if not hit:
        raise SystemExit(f"❌ 找不到 {iid}")
    return hit[0]


def cmd_cancel(iid):
    pull(LOCAL_QUEUE)
    items = load(LOCAL_QUEUE)
    it = find(items, iid)
    if it["status"] != "pending":
        raise SystemExit(f"❌ 狀態是 {it['status']}，只能取消 pending")
    it["status"] = "cancelled"
    if not save(LOCAL_QUEUE, items, f"ig 排程取消：{it['video']}"):
        raise SystemExit("❌ 推不上私人 repo，雲端仍會發——修好前不要離開")
    r2_delete(it["key"])
    print(f"✅ 已取消 {iid} 並刪除 R2 檔案")


def cmd_probe(iid):
    """只建 container、等 FINISHED，不呼叫 media_publish。未發布的 container 24 小時後自動失效。"""
    pull(LOCAL_QUEUE)
    it = find(load(LOCAL_QUEUE), iid)
    tok, ig = creds()
    print(f"✅ IG 抓得到並轉檔完成（container {container(tok, ig, it)}），未發布")


def cmd_run(qpath):
    items = load(qpath)
    now = datetime.now(timezone.utc)
    due = sorted(
        (
            i
            for i in items
            if i["status"] == "pending" and datetime.fromisoformat(i["at"]) <= now
        ),
        key=lambda i: i["at"],
    )
    if not due:
        print("沒有到期的排程")
        return
    tok, ig = creds()
    failed = False
    for it in due:
        at = datetime.fromisoformat(it["at"])
        label = f"{it['video']}（原定 {at.astimezone(TW):%m-%d %H:%M}）"
        if now - at > LATE_LIMIT:
            it.update(
                status="missed", note=f"{now.astimezone(TW):%m-%d %H:%M} 才輪到，不補發"
            )
            save(qpath, items, f"ig 排程逾時：{it['video']}")
            notify(f"⚠️ IG 預約 Reels 錯過時間、未發布\n{label}\n要發請重新排程")
            failed = True
            continue

        it["status"] = "publishing"
        if not save(qpath, items, f"ig 排程發布中：{it['video']}"):
            raise SystemExit("❌ 狀態推不上私人 repo，為避免重複發布，這輪不發")

        try:
            got = head(it["url"])
            if got != it["bytes"]:
                raise RuntimeError(f"R2 檔案大小 {got} 與排程時 {it['bytes']} 不符")
            cid = container(tok, ig, it)
            mid = post(
                f"{ig}/media_publish", {"creation_id": cid, "access_token": tok}
            )["id"]
        except Exception as e:
            it.update(status="error", note=str(e)[:300])
            save(qpath, items, f"ig 排程失敗：{it['video']}")
            notify(f"❌ IG 預約 Reels 發布失敗（未發出）\n{label}\n{e}")
            failed = True
            continue

        it.update(status="published", media_id=mid)
        save(qpath, items, f"ig 排程已發布：{it['video']}")

        try:
            m = get(
                f"{GRAPH}/{mid}?fields=permalink,media_type,media_url&access_token={tok}"
            )
            it["permalink"] = m.get("permalink")
            with tempfile.TemporaryDirectory() as tmp:
                p = os.path.join(tmp, "check.mp4")
                open(p, "wb").write(
                    urllib.request.urlopen(m["media_url"], timeout=120).read()
                )
                dur = probe(p)["duration"]
            if abs(dur - it["duration"]) > 1:
                raise RuntimeError(f"抓回來 {dur:.1f} 秒，排程時 {it['duration']} 秒")
            it["verified"] = f"{m.get('media_type')} {dur:.1f}s"
            r2_delete(it["key"])
            notify(f"✅ IG 預約 Reels 已發布\n{label}\n{it['permalink']}")
        except Exception as e:
            it["note"] = f"已發布但驗收失敗：{e}"[:300]
            notify(
                f"⚠️ IG 預約 Reels 已發布，但驗收沒過，請手動看一下\n{label}\n{e}\n{it.get('permalink') or ''}"
            )
            failed = True
        save(qpath, items, f"ig 排程驗收：{it['video']}")
        print(f"{it['status']} {label} {it.get('permalink')} {it.get('note', '')}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    if a[0] == "add" and len(a) >= 4:
        cmd_add(a[1], a[2], a[3], yes="--yes" in a)
    elif a[0] == "list":
        cmd_list()
    elif a[0] == "cancel" and len(a) == 2:
        cmd_cancel(a[1])
    elif a[0] == "probe" and len(a) == 2:
        cmd_probe(a[1])
    elif a[0] == "run" and "--queue" in a:
        cmd_run(a[a.index("--queue") + 1])
    else:
        raise SystemExit(__doc__)
