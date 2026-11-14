#!/usr/bin/env python3
"""金錢怪物獨立 Short 自動開工：本機排程啟動 Claude Code 照 RUNBOOK_SHORTS.md 做一支。

    python3 finance_shorts/auto_shorts.py install     # 裝排程（週一、週四 10:00）並立刻自我測試
    python3 finance_shorts/auto_shorts.py uninstall   # 停掉排程
    python3 finance_shorts/auto_shorts.py status      # 排程狀態、試跑進度、最近紀錄
    python3 finance_shorts/auto_shorts.py run         # 排程實際呼叫的入口（會真的做片並排程上片）

改時間改 SLOTS、改試跑支數改 TRIAL_LIMIT，改完重跑 install。
"""
import datetime, glob, os, plistlib, re, signal, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LABEL = "com.lien.moneymonster.shorts"
PLIST = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
STATE = Path.home() / "Library/Logs/moneymonster"
SLOTS = [(1, 10, 0), (4, 10, 0)]  # (星期幾 1=週一, 時, 分)
TRIAL_LIMIT = 4  # 試跑支數，做滿就停下來等 Lien 決定
TIMEOUT = 3 * 3600
MIN_BATTERY = 50

PROMPT = (
    "你現在是本機排程啟動的無人值守工作，沒有人在電腦前，不要提問。"
    "照 finance_shorts/RUNBOOK_SHORTS.md 做一支金錢怪物獨立 Short，做到排程上片與收尾為止；"
    "做不成就照該檔「收工回報」處理。最後一行一定要輸出 AUTO_SHORTS_RESULT。"
)
SELFTEST_PROMPT = (
    "這是排程的自我測試，不要做任何更動、不要上傳。"
    "讀 finance_shorts/RUNBOOK_SHORTS.md 與 finance_shorts/題目紀錄.md，"
    "跑 `python3 finance_shorts/verify.py ms-02` 與 `ffprobe -version`，"
    "然後只輸出一行：AUTO_SHORTS_SELFTEST: ok 下一題＝<題庫第一個沒做的題目>"
)
ALLOWED = [
    "Read",
    "Edit",
    "Write",
    "Glob",
    "Grep",
    "Skill",
    "WebSearch",
    "WebFetch",
    "Bash(python3 *)",
    "Bash(taskpolicy -b python3 *)",
    "Bash(ffprobe *)",
    "Bash(ffmpeg *)",
    "Bash(afconvert *)",
    "Bash(env -u NODE_OPTIONS codex exec -s read-only *)",
    "Bash(~/bin/gh workflow run line_notify.yml *)",
    f"Bash({Path.home()}/bin/gh workflow run line_notify.yml *)",
    "Bash(git status*)",
    "Bash(git diff*)",
    "Bash(git log*)",
    "Bash(git add *)",
    "Bash(git commit *)",
    "Bash(git push)",
    "Bash(git push origin main)",
    "Bash(ls *)",
    "Bash(mkdir *)",
    "Bash(cp *)",
]


def env():
    home = str(Path.home())
    node = sorted(glob.glob(f"{home}/.nvm/versions/node/*/bin"))[-1:]
    path = [
        f"{home}/.local/bin",
        f"{home}/bin",
        *node,
        "/opt/homebrew/bin",
        f"{home}/Library/Python/3.9/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
    ]
    return {
        "HOME": home,
        "USER": os.environ.get("USER", Path.home().name),
        "PATH": ":".join(path),
        "LANG": "en_US.UTF-8",
        "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
    }


def log(msg):
    STATE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(STATE / "auto_shorts.log", "a") as f:
        f.write(f"{stamp} {msg}\n")
    print(msg)


def line(text):
    subprocess.run(
        [
            str(Path.home() / "bin/gh"),
            "workflow",
            "run",
            "line_notify.yml",
            "-f",
            f"text={text}",
        ],
        cwd=REPO,
        env=env(),
        capture_output=True,
    )


def done_count():
    f = STATE / "done.txt"
    return len(f.read_text().splitlines()) if f.exists() else 0


def claude(prompt, timeout):
    """跑一次無人值守的 Claude Code，回傳 (輸出, 是否逾時)。逾時連子程序一起清。"""
    cmd = [
        "caffeinate",
        "-i",
        "claude",
        "-p",
        prompt,
        "--permission-mode",
        "acceptEdits",
        "--allowedTools",
        *ALLOWED,
    ]
    p = subprocess.Popen(
        cmd,
        cwd=REPO,
        env=env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        out, _ = p.communicate(timeout=timeout)
        return out, False
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGTERM)
        time.sleep(5)
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, _ = p.communicate()
        return out, True


def on_low_battery():
    b = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    pct = re.search(r"(\d+)%", b)
    return "Battery Power" in b and pct and int(pct.group(1)) < MIN_BATTERY


def run():
    STATE.mkdir(parents=True, exist_ok=True)
    if (STATE / "selftest").exists():
        (STATE / "selftest").unlink()
        out, timed_out = claude(SELFTEST_PROMPT, 600)
        ok = "AUTO_SHORTS_SELFTEST: ok" in out and not timed_out
        (STATE / "selftest_result.txt").write_text(
            ("OK\n" if ok else "FAIL\n") + out[-3000:]
        )
        log(f"自我測試 {'通過' if ok else '失敗'}")
        return

    if done_count() >= TRIAL_LIMIT:
        if not (STATE / "trial_notified").exists():
            (STATE / "trial_notified").touch()
            line(
                f"📋 金錢怪物 Short 自動開工試跑 {TRIAL_LIMIT} 支做完了，排程已自動暫停。"
                "要不要繼續、要不要擴到長片，等你開對話決定。"
            )
        log("試跑支數已滿，不開工")
        return

    lock = STATE / "lock"
    if lock.exists() and time.time() - lock.stat().st_mtime < TIMEOUT + 600:
        log("上一輪還在跑，這輪跳過")
        return
    if subprocess.run(
        ["pgrep", "-f", "hf_render|hyperframes"], capture_output=True
    ).stdout:
        log("電腦正在渲染別的影片，這輪跳過")
        line("⏭️ 金錢怪物 Short 這輪沒開工：電腦正在渲染別的影片。")
        return
    if on_low_battery():
        log("電池不足，這輪跳過")
        line(f"⏭️ 金錢怪物 Short 這輪沒開工：沒接電源而且電量低於 {MIN_BATTERY}%。")
        return

    lock.touch()
    try:
        log("開工")
        out, timed_out = claude(PROMPT, TIMEOUT)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        (STATE / f"run_{stamp}.txt").write_text(out)
        result = re.findall(r"AUTO_SHORTS_RESULT: (.+)", out)
        if result and result[-1].startswith("ok"):
            with open(STATE / "done.txt", "a") as f:
                f.write(f"{stamp} {result[-1]}\n")
            log(f"完成：{result[-1]}（試跑第 {done_count()}／{TRIAL_LIMIT} 支）")
        elif result:
            log(f"沒做成：{result[-1]}")
        else:
            why = "超過 3 小時被中止" if timed_out else "中途結束、沒有回報結果"
            log(f"異常：{why}")
            line(
                f"🔴 金錢怪物 Short 自動開工異常：{why}。紀錄在 ~/Library/Logs/moneymonster/"
            )
    finally:
        lock.unlink()


def install():
    STATE.mkdir(parents=True, exist_ok=True)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_bytes(
        plistlib.dumps(
            {
                "Label": LABEL,
                "ProgramArguments": [
                    "/usr/bin/python3",
                    str(Path(__file__).resolve()),
                    "run",
                ],
                "WorkingDirectory": str(REPO),
                "StartCalendarInterval": [
                    {"Weekday": w, "Hour": h, "Minute": m} for w, h, m in SLOTS
                ],
                "StandardOutPath": str(STATE / "launchd.out"),
                "StandardErrorPath": str(STATE / "launchd.err"),
                "ProcessType": "Background",
            }
        )
    )
    dom = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", f"{dom}/{LABEL}"], capture_output=True)
    r = subprocess.run(
        ["launchctl", "bootstrap", dom, str(PLIST)], capture_output=True, text=True
    )
    if r.returncode:
        sys.exit(f"❌ 排程沒裝上：{r.stderr.strip()}")
    print(
        "✅ 排程已裝好，現在由排程本身跑一次自我測試（不會做片、不會上傳），最多等 10 分鐘…"
    )
    print("   如果跳出「python3 想要取用下載項目檔案夾」之類的視窗，請按允許。")
    res = STATE / "selftest_result.txt"
    res.unlink(missing_ok=True)
    (STATE / "selftest").touch()
    subprocess.run(["launchctl", "kickstart", f"{dom}/{LABEL}"], capture_output=True)
    for _ in range(130):
        if res.exists():
            break
        time.sleep(5)
    if not res.exists():
        sys.exit(
            "❌ 自我測試 10 分鐘內沒有結果，看 ~/Library/Logs/moneymonster/launchd.err"
        )
    text = res.read_text()
    if text.startswith("OK"):
        print("✅ 自我測試通過：" + text.strip().splitlines()[-1])
        status()
    else:
        print("❌ 自我測試失敗，排程先停用。輸出：\n" + text)
        uninstall()
        sys.exit(1)


def uninstall():
    subprocess.run(
        ["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], capture_output=True
    )
    PLIST.unlink(missing_ok=True)
    print("已停掉排程")


def status():
    r = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"],
        capture_output=True,
        text=True,
    )
    days = "一二三四五六日"
    when = "、".join(f"週{days[w - 1]} {h:02d}:{m:02d}" for w, h, m in SLOTS)
    print(f"排程：{'已啟用' if r.returncode == 0 else '未啟用'}（{when}）")
    print(f"試跑進度：{done_count()}／{TRIAL_LIMIT} 支")
    f = STATE / "auto_shorts.log"
    if f.exists():
        print("最近紀錄：\n" + "\n".join(f.read_text().splitlines()[-8:]))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"install": install, "uninstall": uninstall, "status": status, "run": run}[cmd]()
