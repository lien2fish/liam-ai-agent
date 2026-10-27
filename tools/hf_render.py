#!/usr/bin/env python3
"""HyperFrames 本機渲染的唯一入口：抽格限流＋強制 SDR＋固定 workers。

2026-10-27 金錢怪物 es-01 渲染兩度吃光記憶體、整台重開，規則與實測見 CLAUDE.md
「HyperFrames 本機渲染規則」。各產線不要再手打 `npx hyperframes render`。

  python3 tools/hf_render.py [專案目錄] [其他 render 參數...]
  from hf_render import render; render(pdir)
"""
import os
import pathlib
import subprocess
import sys

HF = "hyperframes@0.8.30"
GATE = pathlib.Path(__file__).resolve().parent / "ffmpeg_gate.py"
WORKERS = "3"  # auto 會開滿核心數的 Chrome，M5 Air 無風扇、長時間滿載過熱


def render(pdir, *extra):
    # --sdr：素材混到一段 HDR 就整支切成 HDR 分層合成（es-01 1h39m→17m，HDR 版畫面發灰）
    subprocess.run(
        ["npx", "--yes", HF, "render", "--workers", WORKERS, "--sdr", *extra],
        cwd=pdir,
        check=True,
        env={**os.environ, "HYPERFRAMES_FFMPEG_PATH": str(GATE)},
    )


if __name__ == "__main__":
    args = sys.argv[1:]
    pdir = args.pop(0) if args and not args[0].startswith("-") else "."
    render(pdir, *args)
