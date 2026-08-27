#!/usr/bin/env python3
"""排程巡邏——GitHub 的 schedule 會誤點，負載高時甚至整次跳過。

每小時檢查「今天該跑的有沒有跑」，超過寬限時間仍然一次都沒跑，
就用 workflow_dispatch 補觸發，並且回頭確認真的多出一次 run 才算數。

⛔ 會對外發布的三支只通知、不補跑（NOTIFY_ONLY）——自動補跑等於自動發文，
   IG 貼文與限動發出去 API 刪不掉。要不要補由本人決定。

⛔ IG 留言回覆（每 5 分鐘）不在巡邏範圍：它本來就常誤點 1.5~4 小時，
   而且同樣會對外發布。
"""

import json
import os
import re
import smtplib
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.utils import formataddr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from line_assistant.notify import notify

REPO = os.environ.get("GITHUB_REPOSITORY", "lien2fish/liam-ai-agent")
TOKEN = os.environ.get("GH_TOKEN", "")
GMAIL_PW = os.environ.get("GMAIL_APP_PASSWORD", "")
ADDR = "lien2fish@gmail.com"

TW = timezone(timedelta(hours=8))

# 誤點多久才算「這次被跳過了」。GitHub 誤點 1.5~4 小時是常態，
# 抓太短會在它只是慢的時候補一次，變成兩封信。
GRACE_MIN = 120

WF_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".github", "workflows"
)

# (workflow 檔名, 顯示名, 是否自動補跑)
# 時間不寫在這裡——直接讀 workflow 自己的 cron，改了排程這邊就跟著走。
TASKS = [
    ("daily_post.yml", "IG+FB 每日發文", False),
    ("gmail_automation.yml", "Gmail 清理＋新聞", True),
    ("policy_expiry_check.yml", "產險保單到期", True),
    ("birthday_reminder.yml", "壽險客戶生日", True),
    ("rotary_birthday_reminder.yml", "扶輪社友生日", True),
    ("yt_channel_report.yml", "YT 頻道日報", True),
    ("yt_comment_monitor.yml", "YT 留言通知", True),
    ("life_visit_reminder.yml", "壽險拜訪提醒", True),
    ("token_expiry_check.yml", "Token 到期檢查", True),
    ("weekly_revenue_sprint.yml", "營收衝刺週報", True),
    ("weekly_review.yml", "AI 工作週報", True),
    ("notion_monthly_report.yml", "Notion 月報", True),
    ("repurchase_reminder.yml", "回購提醒", True),
    ("seafood_prices.yml", "漁獲行情", True),
    ("yt_auto_post.yml", "YouTube 自動影片", False),
    ("market_daily.yml", "每日股市分析", True),
    ("ig_story_teaser.yml", "IG 限動 Reels 預告", False),
]


def parse_cron(wf):
    """從 workflow 檔讀 cron，換算成台灣時間與週期。"""
    text = open(os.path.join(WF_DIR, wf), encoding="utf-8").read()
    m = re.search(r"cron:\s*'([^']+)'", text)
    if not m:
        return None
    mm, hh, dom, _mon, dow = m.group(1).split()
    tw_hour = (int(hh) + 8) % 24
    if dow != "*":
        period = "mon" if dow == "1" else "dow%s" % dow
    elif dom != "*":
        period = "day%s" % dom
    else:
        period = "daily"
    return tw_hour, int(mm), period


def api(path, method="GET", body=None):
    req = urllib.request.Request(
        "https://api.github.com/repos/%s%s" % (REPO, path),
        data=json.dumps(body).encode() if body else None,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + TOKEN,
            "User-Agent": "schedule-watchdog/1",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def runs_today(wf, today):
    """今天（台灣時間）這支 workflow 的執行紀錄，不分排程或手動。"""
    data = api("/actions/workflows/%s/runs?per_page=20" % wf)
    out = []
    for r in data.get("workflow_runs", []):
        dt = datetime.strptime(r["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        if dt.astimezone(TW).date() == today:
            out.append(r)
    return out


def due(hh, mm, period, now):
    """該跑的時間已經過了寬限期就回傳 True；今天不該跑回傳 False。"""
    if period == "mon" and now.weekday() != 0:
        return False
    if period.startswith("day") and now.day != int(period[3:]):
        return False
    expected = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return now >= expected + timedelta(minutes=GRACE_MIN)


def dispatch(wf, today):
    """補觸發，然後確認真的生出一次 run——API 回 204 不等於跑起來了。"""
    api("/actions/workflows/%s/dispatches" % wf, "POST", {"ref": "main"})
    for _ in range(6):
        time.sleep(8)
        for r in runs_today(wf, today):
            if r["event"] == "workflow_dispatch":
                return True
    return False


def send_mail(subject, lines):
    if not GMAIL_PW:
        print("⚠️ 未設 GMAIL_APP_PASSWORD，跳過寄信")
        return
    msg = MIMEText("<br>".join(lines), "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("排程巡邏", ADDR))
    msg["To"] = ADDR
    with smtplib.SMTP_SSL(
        "smtp.gmail.com", 465, context=ssl.create_default_context()
    ) as s:
        s.login(ADDR, GMAIL_PW)
        s.send_message(msg)
    print("📧 已寄出")


def main():
    if not TOKEN:
        print("🔴 沒有 GH_TOKEN，無法查詢也無法補跑")
        sys.exit(1)

    now = datetime.now(timezone.utc).astimezone(TW)
    today = now.date()
    print("巡邏時間（台灣）：%s" % now.strftime("%Y-%m-%d %H:%M"))

    fixed, failed, manual, broken = [], [], [], []

    for wf, name, auto in TASKS:
        cron = parse_cron(wf)
        if not cron:
            print("⚠️ %s 沒有 cron，跳過" % wf)
            continue
        hh, mm, period = cron
        if not due(hh, mm, period, now):
            continue

        got = runs_today(wf, today)
        if got:
            bad = [r for r in got if r["conclusion"] == "failure"]
            if bad and not [r for r in got if r["conclusion"] == "success"]:
                broken.append("%s（%02d:%02d）今天跑了但失敗" % (name, hh, mm))
                print("❌ %s 今天跑過但失敗" % name)
            else:
                print("✅ %s 今天已執行" % name)
            continue

        if not auto:
            manual.append("%s（原定 %02d:%02d）" % (name, hh, mm))
            print("⏸ %s 今天沒跑——會對外發布，只通知不補" % name)
            continue

        print("🔧 %s 今天沒跑，補觸發……" % name)
        try:
            ok = dispatch(wf, today)
        except urllib.error.HTTPError as e:
            ok = False
            print("   API 錯誤 HTTP %s" % e.code)
        (fixed if ok else failed).append("%s（原定 %02d:%02d）" % (name, hh, mm))
        print("   %s" % ("已補跑" if ok else "補跑失敗"))

    if not (fixed or failed or manual or broken):
        print("✅ 今天該跑的都跑了，不發通知")
        return

    lines = []
    if failed:
        lines += ["<b>🔴 補跑失敗，要人工處理：</b>", ""]
        lines += ["• %s" % x for x in failed]
        lines += [
            "",
            "多半是 token 沒有 actions:write 權限，補觸發打得出去但生不出 run。",
            "",
        ]
    if manual:
        lines += ["<b>🟡 沒跑，但不自動補（會對外發布，要你決定）：</b>", ""]
        lines += ["• %s" % x for x in manual]
        lines += [
            "",
            "要補的話到 Actions 頁面手動 dispatch。發出去 API 刪不掉，想清楚再按。",
            "",
        ]
    if broken:
        lines += ["<b>❌ 有跑但失敗（巡邏不自動重試）：</b>", ""]
        lines += ["• %s" % x for x in broken]
        lines += [""]
    if fixed:
        lines += ["<b>✅ 已自動補跑：</b>", ""]
        lines += ["• %s" % x for x in fixed]
        lines += [""]
    lines += ["─" * 30, "", "巡邏時間：%s（台灣）" % now.strftime("%Y-%m-%d %H:%M")]

    head = (
        "🔴 排程補跑失敗"
        if failed
        else ("🟡 有排程沒跑" if manual or broken else "✅ 排程已自動補跑")
    )
    send_mail("%s（%s）" % (head, today.isoformat()), lines)

    # LINE 只推需要決策或壞掉的，補跑成功不吵
    if failed or manual or broken:
        push = ["%s %s" % (head, today.isoformat())]
        push += ["・" + x for x in failed + manual + broken]
        if fixed:
            push += ["", "已自動補跑 %d 支" % len(fixed)]
        notify("\n".join(push))

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
