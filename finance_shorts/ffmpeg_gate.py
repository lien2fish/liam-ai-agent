#!/usr/bin/env python3
"""HyperFrames 的 ffmpeg 包裝：抽影格的呼叫限制同時數量與核心數。

HyperFrames 0.8.30 對每段 <video> 同時開一個 ffmpeg、沒有上限，
es-01（186 段）一次開到 130 個、吃掉 36GB，2026-10-27 兩度讓整台當機重開。
實測同時 2 個、每個 2 核，186 段抽格 42.6 秒（同時 6 個 36.8 秒），記憶體峰值 0.5GB。

只攔抽影格（輸出為 %05d 圖檔序列），其餘呼叫（編碼、混音）原樣放行。
用 flock 佔位：ffmpeg 結束或被殺時鎖自動釋放，不會留下卡死的位子。
"""
import fcntl
import os
import re
import sys
import time

REAL = os.environ.get("FFMPEG_GATE_REAL", "/opt/homebrew/bin/ffmpeg")
SLOTS = int(os.environ.get("FFMPEG_GATE_SLOTS", "2"))
THREADS = os.environ.get("FFMPEG_GATE_THREADS", "2")
LOCK_DIR = "/tmp/ffmpeg_gate"

args = sys.argv[1:]
if args and re.search(r"%0\d+d\.(jpg|png)$", args[-1]):
    os.makedirs(LOCK_DIR, exist_ok=True)
    held = None
    while held is None:
        for i in range(SLOTS):
            fd = os.open(f"{LOCK_DIR}/slot{i}", os.O_CREAT | os.O_RDWR)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held = fd
                break
            except BlockingIOError:
                os.close(fd)
        else:
            time.sleep(0.1)
    os.set_inheritable(held, True)
    args = ["-threads", THREADS] + args

os.execv(REAL, [REAL] + args)
