# -*- coding: utf-8 -*-
"""一次性腳本：把 SessionEnd hook 上線前的 Claude Code 對話回填成每日工作日誌。

session_log.py 從 2026-08-19 才開始寫 daily/，更早的 transcript 還躺在
~/.claude/projects/ 底下。這支把它們用同一套去噪規則解析、依 session 開始時間
分日，補進 ~/liam-workspace/daily/，讓週報只要讀 daily/ 就有完整資料。

已寫入的 session（靠檔尾 `<!-- session <id> -->` 判斷）會跳過，可重複執行。
"""
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from session_log import DAILY_DIR, parse

TRANSCRIPT_DIR = os.path.expanduser(
    "~/.claude/projects/-Users-lien-Downloads-Liam-AI-agent"
)
DIGEST = os.path.expanduser("~/liam-workspace/reviews/_digest.md")
HOME = os.path.expanduser("~")


def first_timestamp(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"timestamp"' not in line:
                continue
            try:
                ts = json.loads(line).get("timestamp")
            except ValueError:
                continue
            if ts:
                return datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
    return datetime.fromtimestamp(os.path.getmtime(path))


def logged_sessions():
    done = set()
    if not os.path.isdir(DAILY_DIR):
        return done
    for name in os.listdir(DAILY_DIR):
        if not name.endswith(".md"):
            continue
        text = open(os.path.join(DAILY_DIR, name), encoding="utf-8").read()
        done.update(re.findall(r"<!-- session ([0-9a-f-]{36})", text))
    return done


def render(sid, when, prompts, title, tools, files):
    lines = [
        "",
        "## %02d:%02d — %s" % (when.hour, when.minute, title or prompts[0][:30]),
        "",
    ]
    for p in prompts:
        lines.append("- 我：" + p[:300])
    if files:
        lines += ["", "**改動的檔案**"]
        lines += ["- `%s`" % f.replace(HOME, "~") for f in files[:20]]
        if len(files) > 20:
            lines.append("- …另外 %d 個檔案" % (len(files) - 20))
    if tools:
        top = sorted(tools.items(), key=lambda kv: -kv[1])[:6]
        lines += ["", "工具：" + "、".join("%s×%d" % (k, v) for k, v in top)]
    lines += ["", "<!-- session %s · backfill -->" % sid]
    return "\n".join(lines) + "\n"


def main():
    done = logged_sessions()
    paths = sorted(
        os.path.join(TRANSCRIPT_DIR, n)
        for n in os.listdir(TRANSCRIPT_DIR)
        if n.endswith(".jsonl")
    )

    sessions = []
    for path in paths:
        sid = os.path.basename(path)[:-6]
        if sid in done:
            print("跳過（已記錄）：%s" % sid[:8])
            continue
        when = first_timestamp(path)
        prompts, title, tools, files = parse(path)
        if not prompts:
            print("跳過（無對話）：%s" % sid[:8])
            continue
        sessions.append((when, sid, prompts, title, tools, files))
        print(
            "解析 %s  %s  %d 則需求"
            % (when.strftime("%m-%d %H:%M"), sid[:8], len(prompts))
        )

    sessions.sort(key=lambda s: s[0])
    os.makedirs(DAILY_DIR, exist_ok=True)

    for when, sid, prompts, title, tools, files in sessions:
        log = os.path.join(DAILY_DIR, when.strftime("%Y-%m-%d") + ".md")
        new = not os.path.exists(log)
        with open(log, "a", encoding="utf-8") as f:
            if new:
                f.write(
                    "# 工作日誌 %s（%s）\n"
                    % (when.strftime("%Y-%m-%d"), "一二三四五六日"[when.weekday()])
                )
            f.write(render(sid, when, prompts, title, tools, files))

    os.makedirs(os.path.dirname(DIGEST), exist_ok=True)
    with open(DIGEST, "w", encoding="utf-8") as f:
        f.write("# 對話索引（回填自 Claude Code transcripts）\n\n")
        f.write("| 日期 | 時間 | 主題 | 需求數 | 改檔數 | session |\n")
        f.write("|---|---|---|---|---|---|\n")
        for when, sid, prompts, title, tools, files in sessions:
            topic = (title or prompts[0][:30]).replace("|", "／")
            f.write(
                "| %s | %02d:%02d | %s | %d | %d | `%s` |\n"
                % (
                    when.strftime("%m-%d"),
                    when.hour,
                    when.minute,
                    topic,
                    len(prompts),
                    len(files),
                    sid[:8],
                )
            )

    print("\n回填 %d 個 session，索引寫入 %s" % (len(sessions), DIGEST))


if __name__ == "__main__":
    main()
