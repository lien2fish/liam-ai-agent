# -*- coding: utf-8 -*-
"""列出還沒萃取過記憶的工作日誌段落，給「萃取記憶」skill 用。

    python3 scripts/memory_extract.py                              # 印出待萃取的對話
    python3 scripts/memory_extract.py --count                      # 只印數量
    python3 scripts/memory_extract.py --mark "2026-09-15 12:40"    # 標記萃取到這一段為止

--mark 要帶列表最後印出的時間點，不是「現在」：列表和寫入之間若又結束了新的 session，
用「現在」標記會把沒看過的對話一起標掉。

進度記在 ~/liam-workspace/daily/.extracted.json，跟日誌一起被 SessionEnd hook 推上私人 repo，
雲端週報才讀得到還剩幾段沒萃取。只讀日誌、不呼叫任何 API；內容只印在終端機。
"""
import argparse
import glob
import json
import os
import re
from datetime import date, timedelta

HOME = os.path.expanduser("~")
DAILY_DIR = os.path.join(HOME, "liam-workspace/daily")
TRANSCRIPTS = os.path.join(HOME, ".claude/projects")
MARK_FILE = ".extracted.json"
# 沒有進度紀錄時只看最近兩週——第一次就把全部日誌倒出來，候選會多到沒人想看
FIRST_RUN_DAYS = 14
# 萃取記憶那段對話本身不用再萃取一次
SKIP_WORDS = ("萃取記憶",)
HEAD_RE = re.compile(r"^## (\d\d:\d\d) — (.*)$", re.M)
SESSION_RE = re.compile(r"<!-- session (\S+)")


def load_mark(daily_dir):
    try:
        with open(os.path.join(daily_dir, MARK_FILE), encoding="utf-8") as f:
            return json.load(f).get("through")
    except (OSError, ValueError):
        return None


def pending_sessions(daily_dir=DAILY_DIR):
    through = load_mark(daily_dir)
    if not through:
        start = date.today() - timedelta(days=FIRST_RUN_DAYS)
        through = start.isoformat() + " 99:99"
    out = []
    for path in sorted(glob.glob(os.path.join(daily_dir, "20??-??-??.md"))):
        day = os.path.basename(path)[:10]
        if day + " 99:99" <= through:
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        heads = list(HEAD_RE.finditer(text))
        for i, m in enumerate(heads):
            key = "%s %s" % (day, m.group(1))
            if key <= through:
                continue
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            block = text[m.start() : end].strip()
            if any(w in block for w in SKIP_WORDS):
                continue
            sid = SESSION_RE.search(block)
            out.append(
                {
                    "key": key,
                    "title": m.group(2),
                    "text": block,
                    "session": sid.group(1) if sid else None,
                }
            )
    return out


def transcript(session_id):
    if not session_id:
        return None
    hits = glob.glob(os.path.join(TRANSCRIPTS, "*", session_id + ".jsonl"))
    return hits[0] if hits else None


def main():
    ap = argparse.ArgumentParser(description="列出還沒萃取過記憶的工作日誌段落")
    ap.add_argument("--count", action="store_true", help="只印待萃取的數量")
    ap.add_argument(
        "--mark", metavar="時間點", help="標記萃取到這一段為止，例如 '2026-09-15 12:40'"
    )
    ap.add_argument("--daily", default=DAILY_DIR, help="工作日誌資料夾")
    args = ap.parse_args()

    sessions = pending_sessions(args.daily)

    if args.count:
        print(len(sessions))
        return

    if args.mark:
        if not re.match(r"^20\d\d-\d\d-\d\d \d\d:\d\d$", args.mark):
            ap.error("--mark 格式要像 '2026-09-15 12:40'")
        with open(os.path.join(args.daily, MARK_FILE), "w", encoding="utf-8") as f:
            json.dump({"through": args.mark}, f, ensure_ascii=False)
        left = len(pending_sessions(args.daily))
        print("✅ 已標記萃取到 %s，還剩 %d 段" % (args.mark, left))
        return

    progress = load_mark(args.daily) or "尚未萃取過，只看最近 %d 天" % FIRST_RUN_DAYS
    if not sessions:
        print("✅ 沒有待萃取的對話（進度：%s）" % progress)
        return

    print("📝 待萃取 %d 段對話（進度：%s）\n" % (len(sessions), progress))
    for s in sessions:
        # 日誌標題只有時分，跨天列出時要補日期才分得出是哪天講的
        print("【%s】" % s["key"][:10])
        print(s["text"])
        path = transcript(s["session"])
        if path:
            print("完整對話：" + path.replace(HOME, "~"))
        print()
    last = max(s["key"] for s in sessions)
    print("寫入記憶之後跑：python3 scripts/memory_extract.py --mark '%s'" % last)


if __name__ == "__main__":
    main()
