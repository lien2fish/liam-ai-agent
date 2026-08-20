# -*- coding: utf-8 -*-
"""SessionEnd hook：把這次 session 做了什麼追加寫進每日工作日誌。

輸出到私人 repo ~/liam-workspace/daily/YYYY-MM-DD.md（提問內容可能含客戶/財務資料，
絕不進公開 repo）。純文字萃取，不呼叫任何 API。
"""
import json
import os
import sys
from datetime import datetime

DAILY_DIR = os.path.expanduser("~/liam-workspace/daily")
NOISE_PREFIX = (
    "<command-name>",
    "<local-command",
    "Caveat:",
    "<system-reminder>",
    "<task-notification>",
    "[Image:",  # 圖片附件的尺寸描述
    "[Usage limit",  # 系統插話
    "Base directory for this skill:",  # Skill 載入的內容
    "The following skills are available",
)


def parse(path):
    prompts, title, tools, files = [], None, {}, []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        t = d.get("type")
        if t == "ai-title":
            title = d.get("aiTitle") or title
        elif t == "user":
            c = d.get("message", {}).get("content")
            if isinstance(c, list):
                c = "".join(b.get("text", "") for b in c if b.get("type") == "text")
            if (
                isinstance(c, str)
                and c.strip()
                and not c.lstrip().startswith(NOISE_PREFIX)
            ):
                text = " ".join(c.split())
                if text not in prompts:
                    prompts.append(text)
        elif t == "assistant":
            for b in d.get("message", {}).get("content", []):
                if b.get("type") != "tool_use":
                    continue
                name = b.get("name", "?")
                tools[name] = tools.get(name, 0) + 1
                fp = b.get("input", {}).get("file_path")
                if name in ("Edit", "Write", "NotebookEdit") and fp and fp not in files:
                    files.append(fp)
    return prompts, title, tools, files


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    path = payload.get("transcript_path")
    if not path or not os.path.exists(path):
        return

    prompts, title, tools, files = parse(path)
    if not prompts:
        return

    os.makedirs(DAILY_DIR, exist_ok=True)
    now = datetime.now()
    log = os.path.join(DAILY_DIR, now.strftime("%Y-%m-%d") + ".md")
    new = not os.path.exists(log)

    home = os.path.expanduser("~")
    lines = [
        "",
        "## %02d:%02d — %s" % (now.hour, now.minute, title or prompts[0][:30]),
        "",
    ]
    for p in prompts:
        lines.append("- 我：" + p[:300])
    if files:
        lines += ["", "**改動的檔案**"]
        lines += ["- `%s`" % f.replace(home, "~") for f in files[:20]]
        if len(files) > 20:
            lines.append("- …另外 %d 個檔案" % (len(files) - 20))
    if tools:
        top = sorted(tools.items(), key=lambda kv: -kv[1])[:6]
        lines += ["", "工具：" + "、".join("%s×%d" % (k, v) for k, v in top)]
    lines += [
        "",
        "<!-- session %s · %s -->"
        % (payload.get("session_id", "?"), payload.get("reason", "")),
    ]

    with open(log, "a", encoding="utf-8") as f:
        if new:
            f.write(
                "# 工作日誌 %s（%s）\n"
                % (now.strftime("%Y-%m-%d"), "一二三四五六日"[now.weekday()])
            )
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
