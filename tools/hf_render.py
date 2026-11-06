#!/usr/bin/env python3
"""HyperFrames 本機渲染的唯一入口：抽格限流＋強制 SDR＋固定 workers＋電池溫度監測。

2026-10-27 金錢怪物 es-01 渲染兩度吃光記憶體、整台重開，規則與實測見 CLAUDE.md
「HyperFrames 本機渲染規則」。各產線不要再手打 `npx hyperframes render`。

  python3 tools/hf_render.py [專案目錄] [其他 render 參數...]
  from hf_render import render; render(pdir)
"""
import os
import pathlib
import re
import signal
import subprocess
import sys
import threading
import time

HF = "hyperframes@0.8.30"
GATE = pathlib.Path(__file__).resolve().parent / "ffmpeg_gate.py"
WORKERS = "2"  # auto 會開滿核心數的 Chrome，M5 Air 無風扇、長時間滿載過熱（2026-11-04 Lien 指示 3→2）

# 2026-11-06 Lien 擔心發熱傷電池：每 30 秒記一次電池溫度，超過上限就間歇暫停渲染降溫。
# 不整段停住：Chrome 與 hyperframes 有逾時檢查（10 秒），所以用「停 4 秒、跑 4 秒」降低平均負載。
TEMP_LIMIT = float(os.environ.get("HF_TEMP_LIMIT", "40"))  # °C，達到就開始間歇暫停
TEMP_RESUME = TEMP_LIMIT - 3  # 降到這裡恢復全速
SAMPLE_SEC = 30
PAUSE_SEC = RUN_SEC = 4


def battery_temp():
    """回傳 °C；讀不到回傳 None（不猜數字）。"""
    try:
        r = subprocess.run(
            ["ioreg", "-rn", "AppleSmartBattery"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r'"Temperature" = (\d+)', r.stdout) if r.returncode == 0 else None
    return int(m.group(1)) / 100 if m else None


def descendants(root):
    rows = subprocess.run(
        ["ps", "-axo", "pid=,ppid="], capture_output=True, text=True, timeout=5
    ).stdout.split()
    children = {}
    for pid, ppid in zip(rows[::2], rows[1::2]):
        children.setdefault(int(ppid), []).append(int(pid))
    found, todo = [], [root]
    while todo:
        for c in children.get(todo.pop(), []):
            found.append(c)
            todo.append(c)
    return [root, *found]


class Throttle:
    """記住實際被 SIGSTOP 的 PID，恢復時對同一批送 SIGCONT（不重新掃樹，避免漏掉被改掛父程序的子程序）。"""

    def __init__(self, root):
        self.root = root
        self.stopped = set()
        self.lock = threading.Lock()
        self.closed = False

    def pause(self):
        with self.lock:
            if self.closed:
                return
            for pid in descendants(self.root):
                try:
                    os.kill(pid, signal.SIGSTOP)
                    self.stopped.add(pid)
                except OSError:
                    pass

    def resume(self):
        with self.lock:
            for pid in self.stopped:
                try:
                    os.kill(pid, signal.SIGCONT)
                except OSError:
                    pass
            self.stopped.clear()

    def close(self):
        with self.lock:
            self.closed = True
        self.resume()


def watch(proc, throttle, done, log_path, stats):
    hot = False
    misses = 0
    next_sample = 0.0
    try:
        with open(log_path, "a") as log:
            log.write(f"# {time.strftime('%F %T')} 開始渲染，上限 {TEMP_LIMIT}°C\n")
            while proc.poll() is None and not done.is_set():
                now = time.monotonic()
                if now >= next_sample:
                    t = battery_temp()
                    next_sample = now + SAMPLE_SEC
                    if t is None:
                        misses += 1
                    else:
                        misses = 0
                        stats["max"] = max(stats["max"] or 0, t)
                        hot = t >= TEMP_LIMIT or (hot and t > TEMP_RESUME)
                    state = "讀不到溫度" if t is None else ("降溫中" if hot else "全速")
                    log.write(f"{time.strftime('%T')},{t},{state}\n")
                    log.flush()
                    if misses == 3:
                        print("  ⚠️ 連續 3 次讀不到電池溫度，溫度監測暫時失效，渲染照常進行")
                if not hot:
                    done.wait(1)
                    continue
                throttle.pause()
                try:
                    done.wait(PAUSE_SEC)
                finally:
                    throttle.resume()
                stats["paused"] += PAUSE_SEC
                done.wait(RUN_SEC)
    except Exception as e:  # 監測壞掉不能拖垮渲染，記下來最後回報
        stats["error"] = repr(e)
    finally:
        throttle.resume()


def render(pdir, *extra):
    # --sdr：素材混到一段 HDR 就整支切成 HDR 分層合成（es-01 1h39m→17m，HDR 版畫面發灰）
    pdir = pathlib.Path(pdir)
    proc = subprocess.Popen(
        ["npx", "--yes", HF, "render", "--workers", WORKERS, "--sdr", *extra],
        cwd=pdir,
        env={**os.environ, "HYPERFRAMES_FFMPEG_PATH": str(GATE)},
        start_new_session=True,  # 自成程序群組：中斷時整組結束，不靠事後掃樹
    )
    log_path = pdir / "render_temp.log"
    stats = {"max": None, "paused": 0, "error": None}
    throttle, done = Throttle(proc.pid), threading.Event()
    watcher = threading.Thread(
        target=watch, args=(proc, throttle, done, log_path, stats), daemon=True
    )
    watcher.start()
    interrupted = False
    try:
        code = proc.wait()
    except BaseException:
        interrupted = True
        raise
    finally:
        done.set()
        watcher.join()
        throttle.close()
        if interrupted:
            # 中途被中斷：整個程序群組加上記下的子孫一起結束。npx 先走的話，node 會被改掛到
            # launchd 繼續渲染（11-06 實測）；Chrome 另開 session，不在群組內，所以兩邊都要送
            try:
                tree = descendants(proc.pid)
            except (OSError, subprocess.SubprocessError):
                tree = [proc.pid]
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(proc.pid, sig)
                except OSError:
                    pass
                for pid in tree:
                    try:
                        os.kill(pid, sig)
                    except OSError:
                        pass
                if sig == signal.SIGTERM:
                    time.sleep(5)
                    try:
                        tree += [c for pid in tree for c in descendants(pid)[1:]]
                    except (OSError, subprocess.SubprocessError):
                        pass
            proc.wait()
        peak = "無有效讀值" if stats["max"] is None else f"{stats['max']:.1f}°C"
        print(f"  🌡️ 電池最高 {peak}，降溫暫停 {stats['paused']} 秒（紀錄：{log_path}）")
        if stats["error"]:
            print(f"  ⚠️ 溫度監測中途出錯，已恢復全部程序：{stats['error']}")
    if code:
        raise subprocess.CalledProcessError(code, proc.args)


if __name__ == "__main__":
    args = sys.argv[1:]
    pdir = args.pop(0) if args and not args[0].startswith("-") else "."
    render(pdir, *args)
