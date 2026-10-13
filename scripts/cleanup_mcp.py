#!/usr/bin/env python3
"""清掉累積的 Playwright 程序。

每開一個 session，`npx @playwright/mcp` 就疊一份伺服器，舊的不會自己退出；
瀏覽器也常在工作結束後留著。兩者加起來一個月約累積 1GB。

用法：
  python3 scripts/cleanup_mcp.py              # 清瀏覽器 + 多餘的伺服器（保留最新一個）
  python3 scripts/cleanup_mcp.py --dry-run    # 只看要清什麼，不動手
  python3 scripts/cleanup_mcp.py --all        # 連最新的伺服器也清（MCP 會自己重連）

兩種程序都可以安全終止：
  瀏覽器走 --isolated 暫存 profile，沒有要保存的狀態，下次用到幾秒內重開。
  伺服器被關掉後 MCP 會自動重連。
"""

import argparse
import os
import signal
import subprocess
import sys
import time

BROWSER_PAT = "ms-playwright/chromium"
SERVER_PATS = ("@playwright/mcp", "playwright-mcp")
SELF_MARK = "cleanup_mcp"
SHELLS = {"zsh", "bash", "sh", "dash", "fish", "login", "ps", "grep", "python3"}


def snapshot():
    out = subprocess.run(
        ["ps", "-Ao", "pid=,ppid=,etime=,rss=,stat=,comm=,args="],
        capture_output=True,
        text=True,
    ).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split(None, 6)
        if len(parts) < 7:
            continue
        pid, ppid, etime, rss, stat, comm, args = parts
        # 殺掉但父程序還沒回收的程序是 zombie，ps 仍然列得出來。
        # 不排除的話驗證會誤判成「沒終止成功」（2026-10-12 測出來）。
        if stat.startswith("Z"):
            continue
        try:
            rows.append(
                {
                    "pid": int(pid),
                    "ppid": int(ppid),
                    "etime": etime,
                    "mb": int(rss) / 1024,
                    "comm": os.path.basename(comm),
                    "args": args,
                }
            )
        except ValueError:
            continue
    return rows


def protected():
    """自己、父程序、祖父程序都不能殺——2026-10-08 就是沒排除才殺掉自己的 shell。"""
    keep = {os.getpid(), os.getppid()}
    try:
        out = subprocess.run(
            ["ps", "-o", "ppid=", "-p", str(os.getppid())],
            capture_output=True,
            text=True,
        ).stdout.strip()
        if out:
            keep.add(int(out))
    except (ValueError, subprocess.SubprocessError):
        pass
    return keep


def classify(rows):
    keep = protected()
    browsers, servers = [], []
    for r in rows:
        if r["pid"] in keep or SELF_MARK in r["args"]:
            continue
        # 🔴 只認可執行檔名，不靠 args 比對。任何在命令字串裡提到這些路徑的
        # shell（例如 Claude Code 跑的 zsh -c）都會比對中 args，殺下去就是
        # 砍掉自己的工作殼——2026-10-08 實際發生過，exit code 144。
        if r["comm"] in SHELLS:
            continue
        if r["comm"].startswith("Google Chrome") and BROWSER_PAT in r["args"]:
            browsers.append(r)
        elif r["comm"] in ("node", "npm") and any(p in r["args"] for p in SERVER_PATS):
            servers.append(r)
    return browsers, servers


def etime_seconds(etime):
    """ps 的 etime 格式：[[dd-]hh:]mm:ss"""
    days = 0
    if "-" in etime:
        d, etime = etime.split("-", 1)
        days = int(d)
    bits = [int(x) for x in etime.split(":")]
    while len(bits) < 3:
        bits.insert(0, 0)
    h, m, s = bits
    return days * 86400 + h * 3600 + m * 60 + s


def group_by_tree(servers):
    """一組伺服器是 npm 父程序＋node 子程序，必須整組一起處理。

    只殺其中一個會留下壞掉的半組——2026-10-12 dry-run 時發現原本的
    「保留最新一個程序」會把活著那組的 node 子程序殺掉、留下 npm 空殼。
    """
    pids = {r["pid"] for r in servers}
    by_pid = {r["pid"]: r for r in servers}
    groups = {}
    for r in servers:
        root = r["pid"]
        seen = {root}
        while by_pid[root]["ppid"] in pids and by_pid[root]["ppid"] not in seen:
            root = by_pid[root]["ppid"]
            seen.add(root)
        groups.setdefault(root, []).append(r)
    return list(groups.values())


def show(label, rows):
    if not rows:
        print(f"  {label}：無")
        return
    total = sum(r["mb"] for r in rows)
    print(f"  {label}：{len(rows)} 個，共 {total:,.0f}MB")
    for r in sorted(rows, key=lambda x: -x["mb"]):
        name = "chromium" if BROWSER_PAT in r["args"] else "mcp-server"
        print(
            f"    PID {r['pid']:<7} {name:<11} {r['mb']:>6,.0f}MB  已執行 {r['etime']}"
        )


def terminate(rows, dry_run):
    if dry_run or not rows:
        return 0
    pids = [r["pid"] for r in rows]
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    time.sleep(2)

    alive = {r["pid"] for r in snapshot()} & set(pids)
    for pid in alive:
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"  強制終止 PID {pid}")
        except (ProcessLookupError, PermissionError):
            pass
    if alive:
        time.sleep(1)

    still = {r["pid"] for r in snapshot()} & set(pids)
    return len(pids) - len(still)


def main():
    ap = argparse.ArgumentParser(description="清掉累積的 Playwright 程序")
    ap.add_argument("--dry-run", action="store_true", help="只顯示，不終止")
    ap.add_argument(
        "--all", action="store_true", help="連最新的 MCP 伺服器也清（MCP 會自動重連）"
    )
    args = ap.parse_args()

    browsers, servers = classify(snapshot())

    print("目前狀況")
    show("Playwright 瀏覽器", browsers)
    show("playwright-mcp 伺服器", servers)

    groups = group_by_tree(servers)
    targets = list(browsers)
    if args.all:
        targets += servers
        kept = []
    else:
        # etime 最小＝最晚啟動，最可能是當前 session 在用的那組
        by_age = sorted(groups, key=lambda g: min(etime_seconds(r["etime"]) for r in g))
        kept = by_age[0] if by_age else []
        for g in by_age[1:]:
            targets += g

    if not targets:
        print("\n✅ 沒有需要清理的程序")
        return 0

    freed = sum(r["mb"] for r in targets)
    print(
        f"\n{'將清理' if args.dry_run else '清理中'}：{len(targets)} 個程序，約 {freed:,.0f}MB"
    )
    if kept:
        pids = "、".join(str(r["pid"]) for r in sorted(kept, key=lambda r: r["pid"]))
        print(f"保留最新那一組伺服器 PID {pids}（加 --all 可一併清掉）")

    if args.dry_run:
        print("\n（--dry-run，沒有實際終止任何程序）")
        return 0

    killed = terminate(targets, dry_run=False)

    b2, s2 = classify(snapshot())
    print(f"\n完成：終止 {killed} 個程序，釋放約 {freed:,.0f}MB")
    print(f"剩餘　瀏覽器 {len(b2)} 個／伺服器 {len(s2)} 個")
    if killed < len(targets):
        print("⚠️ 有程序沒終止成功，可能權限不足或已自行重啟")
    return 0


if __name__ == "__main__":
    sys.exit(main())
