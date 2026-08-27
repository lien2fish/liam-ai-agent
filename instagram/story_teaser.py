#!/usr/bin/env python3
"""從已發布的 Reels 剪 3 秒預告，貼到 IG 限時動態導流。

挑片規則：取「30 天內沒用過」的 Reels 中最新的一支——新片優先，用完才往回翻舊片。
片長固定 3.00 秒：使用者要求上限 3 秒，而 IG 限動影片下限也是 3 秒，只有這個值同時成立。

  python3 instagram/story_teaser.py --dry-run   # 只剪不發，成品留在 out/
  python3 instagram/story_teaser.py             # 剪完直接發

憑證：環境變數 IG_TOKEN / IG_ID（GitHub Actions），本機 fallback config/instagram_config.json。
影片要有公開網址才能發，所以先推到 repo 的 instagram/stories/ 再用 raw.githubusercontent.com。
"""
import base64, json, os, subprocess, sys, tempfile, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
STATE = os.path.join(BASE, "story_teaser_state.json")
OUTDIR = os.path.join(BASE, "stories")

GRAPH = "https://graph.facebook.com/v19.0"
OWNER, REPO_NAME = "lien2fish", "liam-ai-agent"

COOLDOWN_DAYS = 30  # 同一支 Reel 至少隔這麼久才會再被選中
DUR = 3.00  # IG 限動影片下限＝3 秒，使用者上限也是 3 秒
NSEG = 3  # 拼幾段
HEAD_SKIP = 1.2  # 跳過開頭封面／標題卡：預告一開始就爆雷就沒意義了
TAIL_SKIP = 2.5  # 跳過結尾「記得訂閱」卡
TAG = "Reels完整版～"
TAG_SHOW = 2.00  # 標記顯示幾秒（從結尾往前算）。3 秒的片子留 1 秒讓觀眾先看到畫面

if sys.platform == "darwin":
    FONT, FONT_IDX = "/System/Library/Fonts/STHeiti Medium.ttc", 0
else:
    fc = subprocess.run(
        ["fc-list", ":lang=zh", "--format=%{file}\n"], capture_output=True, text=True
    )
    noto = [l.strip() for l in fc.stdout.splitlines() if "Noto" in l and "CJK" in l]
    FONT = noto[0] if noto else "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"
    FONT_IDX = 3 if FONT.endswith(".ttc") else 0


def creds():
    tok, ig = os.environ.get("IG_TOKEN"), os.environ.get("IG_ID")
    if tok and ig:
        return tok, ig
    c = json.load(open(os.path.join(REPO, "config", "instagram_config.json")))
    return c["long_lived_user_token"], c["ig_account_id"]


def get(url):
    return json.load(urllib.request.urlopen(url))


def post(path, params):
    return json.load(
        urllib.request.urlopen(
            urllib.request.Request(
                f"{GRAPH}/{path}", data=urllib.parse.urlencode(params).encode(), method="POST"
            )
        )
    )  # fmt: skip


def all_reels(tok, ig):
    out, url = (
        [],
        f"{GRAPH}/{ig}/media?fields=id,media_product_type,media_url,caption,timestamp&limit=100&access_token={tok}",
    )
    while url:
        r = get(url)
        out += [x for x in r["data"] if x.get("media_product_type") == "REELS"]
        url = r.get("paging", {}).get("next")
    return out


def pick(reels):
    """30 天內用過的排除，剩下取最新的一支。"""
    used = json.load(open(STATE)) if os.path.exists(STATE) else {}
    cutoff = date.today() - timedelta(days=COOLDOWN_DAYS)
    fresh = [
        r
        for r in reels
        if r["id"] not in used or date.fromisoformat(used[r["id"]]) < cutoff
    ]
    if not fresh:
        raise SystemExit(f"❌ 全部 {len(reels)} 支都在 {COOLDOWN_DAYS} 天內用過了")
    fresh.sort(key=lambda r: r["timestamp"], reverse=True)
    return fresh[0], used


def probe(path):
    out = subprocess.run(["ffmpeg", "-i", path], capture_output=True, text=True).stderr
    import re

    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", out)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def make_tag(png, w, h):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, int(h * 0.045), index=FONT_IDX)
    bb = d.textbbox((0, 0), TAG, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    cy = int(h * 0.745)  # IG 上下各約 250/1920 是 UI 安全區，壓在這裡不會被回覆框蓋到
    px, py = int(w * 0.05), int(h * 0.018)
    d.rounded_rectangle(
        [(w - tw) // 2 - px, cy - th // 2 - py, (w + tw) // 2 + px, cy + th // 2 + py],
        radius=int(h * 0.016), fill=(18, 18, 18, 235),
    )  # fmt: skip
    d.text(
        ((w - tw) // 2 - bb[0], cy - th // 2 - bb[1]),
        TAG,
        font=f,
        fill=(255, 205, 35, 255),
    )
    img.save(png)


def sharpness(src, t, tmp):
    """抽一格算梯度能量。運鏡糊掉的畫面分數低，用來避開它們。"""
    import numpy as np
    from PIL import Image

    p = os.path.join(tmp, "probe.jpg")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{t:.2f}",
            "-i",
            src,
            "-frames:v",
            "1",
            "-q:v",
            "4",
            p,
        ],
        capture_output=True,
    )
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        return 0.0
    a = np.asarray(Image.open(p).convert("L").resize((270, 480)), dtype=float)
    return float(np.abs(np.diff(a, axis=0)).mean() + np.abs(np.diff(a, axis=1)).mean())


def cut(src, out_mp4, tmp):
    """把可用區間切成 NSEG 個時段，每段挑最清晰的一格當起點，拼成 DUR 秒。"""
    total = probe(src)
    span = total - HEAD_SKIP - TAIL_SKIP
    if span < NSEG:  # 太短就整支拿來用，只避開封面卡
        span, start0 = max(total - HEAD_SKIP, NSEG), HEAD_SKIP
    else:
        start0 = HEAD_SKIP
    seg = DUR / NSEG

    marks = []
    for z in range(NSEG):
        lo = start0 + span * z / NSEG
        hi = start0 + span * (z + 1) / NSEG - seg
        cands = [lo + (hi - lo) * k / 5 for k in range(6)] if hi > lo else [lo]
        best = max(cands, key=lambda t: sharpness(src, t, tmp))
        marks.append(best)
    print("  取樣點：" + "  ".join(f"{m:.1f}s" for m in marks), flush=True)

    parts = []
    for i, ss in enumerate(marks):
        p = os.path.join(tmp, f"s{i}.mp4")
        subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{ss:.2f}", "-i", src, "-t", f"{seg + 0.10:.2f}",
             "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=24,format=yuv420p",
             "-af", f"afade=t=in:st=0:d=0.04,afade=t=out:st={seg + 0.04:.2f}:d=0.06",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", p],
            capture_output=True,
        )  # fmt: skip
        parts.append(p)

    tag = os.path.join(tmp, "tag.png")
    make_tag(tag, 1080, 1920)

    # concat 一定要用 filter 不能用 demuxer：demuxer 的時間戳每段從 0 重算，
    # overlay 的 enable='gte(t,N)' 會永遠不觸發，字卡靜默消失且不報錯。
    ins, lab = [], ""
    for p in parts:
        ins += ["-i", p]
    for i in range(len(parts)):
        lab += f"[{i}:v][{i}:a]"
    fc = (
        f"{lab}concat=n={len(parts)}:v=1:a=1[cv][ca];"
        f"[cv][{len(parts)}:v]overlay=0:0:enable='gte(t,{DUR - TAG_SHOW:.2f})'[v]"
    )
    subprocess.run(
        ["ffmpeg", "-y", *ins, "-i", tag, "-filter_complex", fc,
         "-map", "[v]", "-map", "[ca]", "-t", f"{DUR:.2f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
         "-movflags", "+faststart", out_mp4],
        capture_output=True,
    )  # fmt: skip
    return probe(out_mp4)


def _pat():
    """Actions 用 GITHUB_TOKEN，本機 fallback git credential helper（keychain）。"""
    pat = os.environ.get("GITHUB_TOKEN")
    if pat:
        return pat
    import re

    out = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    ).stdout
    m = re.search(r"^password=(.+)$", out, re.M)
    if m:
        return m.group(1)
    raise SystemExit("❌ git credential 取不到 GitHub token")


def gh_upload(local, path):
    """推到 repo 取得 raw 公開網址（IG 只吃公開 URL）。"""
    H = {"Authorization": f"token {_pat()}", "Accept": "application/vnd.github+json"}
    api = f"https://api.github.com/repos/{OWNER}/{REPO_NAME}/contents/{path}"
    body = {
        "message": "chore(ig): 限動預告影片（暫存）",
        "content": base64.b64encode(open(local, "rb").read()).decode(),
    }
    try:
        body["sha"] = json.load(
            urllib.request.urlopen(urllib.request.Request(api, headers=H))
        )["sha"]
    except Exception:
        pass
    urllib.request.urlopen(
        urllib.request.Request(api, data=json.dumps(body).encode(), headers=H, method="PUT")
    )  # fmt: skip
    return f"https://raw.githubusercontent.com/{OWNER}/{REPO_NAME}/main/{path}"


def gh_prune(keep):
    """限動 24 小時就失效，舊影片留著只會讓 public repo 無限膨脹（每天約 6MB）。"""
    pat = _pat()
    H = {"Authorization": f"token {pat}", "Accept": "application/vnd.github+json"}
    base = (
        f"https://api.github.com/repos/{OWNER}/{REPO_NAME}/contents/instagram/stories"
    )
    try:
        items = json.load(
            urllib.request.urlopen(urllib.request.Request(base, headers=H))
        )
    except Exception:
        return
    for it in items:
        if (
            it["type"] != "file"
            or it["name"] == keep
            or not it["name"].endswith(".mp4")
        ):
            continue
        body = {
            "message": f"chore(ig): 清掉過期限動影片 {it['name']}",
            "sha": it["sha"],
        }
        urllib.request.urlopen(
            urllib.request.Request(
                f"{base}/{it['name']}", data=json.dumps(body).encode(), headers=H, method="DELETE"
            )
        )  # fmt: skip
        print(f"  已清除舊影片 {it['name']}", flush=True)


def publish(tok, ig, url):
    cid = post(
        f"{ig}/media", {"media_type": "STORIES", "video_url": url, "access_token": tok}
    )["id"]
    for i in range(45):
        time.sleep(4)
        st = get(f"{GRAPH}/{cid}?fields=status_code,status&access_token={tok}")
        code = st.get("status_code")
        print(f"  [{i * 4 + 4:>3}s] {code}", flush=True)
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise SystemExit(f"❌ 轉檔失敗：{st.get('status')}")
    else:
        raise SystemExit("❌ 轉檔逾時")
    return post(f"{ig}/media_publish", {"creation_id": cid, "access_token": tok})["id"]


def verify(tok, mid, tmp):
    """發出去的不一定是想發的那支（raw CDN 覆蓋有延遲），抓回來量一次長度。"""
    u = get(f"{GRAPH}/{mid}?fields=media_url&access_token={tok}").get("media_url")
    if not u:
        return None
    p = os.path.join(tmp, "check.mp4")
    open(p, "wb").write(urllib.request.urlopen(u).read())
    return probe(p)


def main():
    dry = "--dry-run" in sys.argv
    tok, ig = creds()
    reels = all_reels(tok, ig)
    r, used = pick(reels)
    cap = (r.get("caption") or "").split("\n")[0]
    print(f"已發布 Reels {len(reels)} 支")
    print(f"選中：{r['timestamp'][:10]}  {cap[:44]}")

    os.makedirs(OUTDIR, exist_ok=True)
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "src.mp4")
    open(src, "wb").write(urllib.request.urlopen(r["media_url"]).read())
    print(f"原片 {probe(src):.1f} 秒")

    out = os.path.join(OUTDIR, f"teaser_{date.today():%Y%m%d}.mp4")
    print(f"預告 {cut(src, out, tmp):.2f} 秒 → {out}")
    if dry:
        print("— dry-run，未發布 —")
        return

    url = gh_upload(out, f"instagram/stories/{os.path.basename(out)}")
    time.sleep(10)  # raw CDN 需要一點時間才拿得到新內容
    mid = publish(tok, ig, url)
    print(f"✅ 已發布：https://www.instagram.com/stories/lienstable/  (media {mid})")
    got = verify(tok, mid, tmp)
    print(f"驗證：線上限動 {got:.2f} 秒" if got else "驗證：抓不到 media_url")
    gh_prune(os.path.basename(out))

    used[r["id"]] = date.today().isoformat()
    json.dump(used, open(STATE, "w"), indent=2)
    print(f"已記錄，{COOLDOWN_DAYS} 天內不會再選到這支")


if __name__ == "__main__":
    main()
