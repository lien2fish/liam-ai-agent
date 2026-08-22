# -*- coding: utf-8 -*-
"""把訊息推到 LINE（透過 liam-assistant Worker 的 /notify）。

給 GitHub Actions 與本機腳本共用。沒設定環境變數時靜默跳過，
所以任何腳本都可以無條件呼叫，不會因為沒配置就壞掉。

⚠️ 這會走 LINE 的 push 訊息，計入免費額度（輕用量方案 200 則／月，
約每天 6 則）。只推「失敗警報」與「需要決策的事」，成功訊息不要推。

環境變數：
    LINE_NOTIFY_URL    Worker 網址，例如 https://liam-assistant.xxx.workers.dev
    LINE_NOTIFY_TOKEN  與 Worker secret NOTIFY_TOKEN 相同的字串

用法：
    from telegram_bot.notify import notify
    notify("IG 有 3 則新留言")

    python3 telegram_bot/notify.py "測試訊息"
"""
import json
import os
import sys
import urllib.error
import urllib.request

MAX_LEN = 4000


def notify(text, silent_fail=True):
    url = os.environ.get("LINE_NOTIFY_URL", "").rstrip("/")
    token = os.environ.get("LINE_NOTIFY_TOKEN", "")
    if not url or not token:
        return False

    req = urllib.request.Request(
        url + "/notify",
        data=json.dumps({"text": str(text)[:MAX_LEN]}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError) as e:
        if not silent_fail:
            raise
        print("LINE 推播失敗：%s" % e, file=sys.stderr)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python3 telegram_bot/notify.py '訊息內容'")
        sys.exit(1)
    ok = notify(" ".join(sys.argv[1:]), silent_fail=False)
    print("✅ 已送出" if ok else "⚠️ 未設定 LINE_NOTIFY_URL / LINE_NOTIFY_TOKEN，跳過")
