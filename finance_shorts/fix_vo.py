#!/usr/bin/env python3
"""配音自動重抽：tts → check_vo → 沒過的句子刪掉重抽，最多 N 輪。

    python3 finance_shorts/fix_vo.py uk-01            # 先整集驗，再只重抽沒過的
    python3 finance_shorts/fix_vo.py uk-01 --rounds 5

克隆聲音每次產生的結果會浮動（同一個詞這次對、下次錯），
所以「唸錯」先重抽；重抽幾輪都不過的，才是要改 say 的詞。
"""

import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def check(eid, lines):
    r = subprocess.run(
        [sys.executable, str(ROOT / "check_vo.py"), eid, *map(str, lines)],
        capture_output=True,
        text=True,
    )
    out = r.stdout
    print(out, flush=True)
    return sorted(int(n) for n in re.findall(r"🔴 第\s*(\d+)句", out))


def main():
    eid = sys.argv[1]
    rounds = (
        int(sys.argv[sys.argv.index("--rounds") + 1]) if "--rounds" in sys.argv else 5
    )
    subprocess.run([sys.executable, str(ROOT / "tts.py"), eid], check=True)
    bad = check(eid, [])
    for n in range(1, rounds + 1):
        if not bad:
            break
        print(f"=== 第 {n} 輪重抽：{bad}", flush=True)
        for i in bad:
            (ROOT / eid / "audio" / f"l{i}.mp3").unlink(missing_ok=True)
        subprocess.run([sys.executable, str(ROOT / "tts.py"), eid], check=True)
        bad = check(eid, bad)
    print(f"\n最後仍未通過：{bad}" if bad else "\n全部通過", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
