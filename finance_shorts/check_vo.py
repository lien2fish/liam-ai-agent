#!/usr/bin/env python3
"""整集配音驗收：每句丟回 Whisper large-v3，查發音和數字。

    python3 finance_shorts/check_vo.py uk-01            # 全部
    python3 finance_shorts/check_vo.py uk-01 3 17 40    # 只驗這幾句（1 起算）

為什麼不直接用 check_say.py：
  1. 一次一句、每次重載模型，整集 80 句太慢
  2. check_say 把「數字對不上」歸成可忽略（Whisper 常把中文數字轉成阿拉伯數字），
     等於數字從來沒被驗過。這裡把原文的每個數字換算後，逐一確認聽寫結果裡有出現

發音判斷沿用 check_say 的拼音比對（同音異字不算錯）。
有錯回傳 exit 1。
"""

import json, os, re, sys
from difflib import SequenceMatcher
from pathlib import Path

VENV = os.path.expanduser("~/聲音素材/tts/.venv/bin/python")
if os.path.exists(VENV) and sys.executable != VENV:
    os.execv(VENV, [VENV, os.path.abspath(__file__)] + sys.argv[1:])

ROOT = Path(__file__).resolve().parent
PUNCT = "，。、！？；：「」『』（）·　 ,.!?;:\n\t～—–-／/"
CN = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "兩": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
UNIT = {"十": 10, "百": 100, "千": 1000, "萬": 10000, "億": 100000000}


def cn_int(s):
    total, section, cur = 0, 0, 0
    for ch in s:
        if ch in CN:
            cur = CN[ch]
        elif ch in ("萬", "億"):
            total += (section + cur) * UNIT[ch]
            section = cur = 0
        else:
            section += (cur or 1) * UNIT[ch]
            cur = 0
    return total + section + cur


def numbers(text):
    """原文或聽寫裡的數字，統一成字串集合（去千分位、中文數字換算、年份逐字唸也認得）。"""
    out = set()
    # 「245 億」「37.5 萬」只核對前面的數字，萬／億當分隔，不乘進去
    t = text.replace(",", "").replace("萬", " ").replace("億", " ")
    for n in re.findall(r"\d+(?:\.\d+)?", t):
        out.add(n.rstrip("0").rstrip(".") if "." in n else n)
    for m in re.finditer(
        r"[零〇一二兩三四五六七八九十百千萬億]+(?:點[零〇一二三四五六七八九]+)?", t
    ):
        w = m.group()
        if w in ("一",):
            continue
        whole, _, frac = w.partition("點")
        if whole and all(c in CN for c in whole) and len(whole) >= 3:  # 二零二六 → 2026
            out.add("".join(str(CN[c]) for c in whole))
        try:
            v = str(cn_int(whole)) if whole else "0"
        except KeyError:
            continue
        out.add(v + ("." + "".join(str(CN[c]) for c in frac) if frac else ""))
    return out


D = "零一二三四五六七八九"


def cn_variants(n):
    """原文數字的國字唸法（含「兩百」「二零二六」這類寫法），用來在沒有標點的聽寫裡直接找。"""
    whole, _, frac = n.partition(".")
    out = set()

    def read(x):
        x = int(x)
        if x == 0:
            return ["零"]
        parts, zero = [], False
        for unit, name in ((1000, "千"), (100, "百"), (10, "十"), (1, "")):
            d, x = divmod(x, unit)
            if d:
                if zero:
                    parts.append("零")
                parts.append(D[d] + name)
                zero = False
            elif parts:
                zero = True
        s = "".join(parts)
        if s.startswith("一十"):
            s = s[1:]
        return [s, s.replace("二千", "兩千").replace("二百", "兩百")]

    if int(whole) < 10000:
        out.update(read(whole))
    if len(whole) == 4:
        out.add("".join(D[int(c)] for c in whole))
    if frac:
        out = {w + "點" + "".join(D[int(c)] for c in frac) for w in out}
    return out


def main():
    eid, *only = sys.argv[1:]
    ep = json.loads((ROOT / "scripts.json").read_text())["episodes"][eid]
    import mlx_whisper
    from pypinyin import lazy_pinyin, Style

    py = lambda s: "".join(
        c
        for c in "".join(lazy_pinyin(s, style=Style.TONE3, errors=lambda x: list(x)))
        if not c.isdigit()
    )
    clean = lambda s: "".join(c for c in s if c not in PUNCT)
    bad = 0
    for i, line in enumerate(ep["lines"], 1):
        if only and str(i) not in only:
            continue
        wav = ROOT / eid / "audio" / f"l{i}.mp3"
        def listen():
            r = mlx_whisper.transcribe(
                str(wav),
                path_or_hf_repo="mlx-community/whisper-large-v3-mlx",
                language="zh",
                condition_on_previous_text=False,
                # 用阿拉伯數字寫時 Whisper 常把小數點吞掉（3.1%→31%），用國字提示才看得出有沒有唸「點」
                initial_prompt="以下是繁體中文旁白，數字用國字寫，例如百分之三點一、一百六十九點五、三十七點五萬。",
            )
            return "".join(s["text"] for s in r["segments"])

        # 數字要用保留標點的原文抓：拿掉標點後「百分之四，一年」會黏成「四一」被當成一個數
        raw = listen()
        heard = clean(raw)
        ref = clean(line["text"])
        # Whisper 習慣把日期寫成「日」，唸的是「號」不算錯
        heard_cmp, ref = heard.replace("日", "號"), ref.replace("日", "號")
        problems, warns = [], []

        want = numbers(line["text"]) - {"1"}
        miss = sorted(n for n in want if n not in numbers(raw) and not any(v in raw for v in cn_variants(n)))
        # 只差小數點的，多半是 Whisper 寫法不穩定（同一段音檔時有時無），重聽兩次再判
        for _ in range(2):
            if not any("." in n and n.replace(".", "") in numbers(raw) for n in miss):
                break
            again = listen()
            miss = [n for n in miss if n not in numbers(again)]
        dotted = [n for n in miss if "." in n and n.replace(".", "") in numbers(raw)]
        if dotted:
            warns.append(f"小數點待確認 {dotted}（三次聽寫都沒寫出小數點）")
        if [n for n in miss if n not in dotted]:
            problems.append(f"數字沒聽到 {[n for n in miss if n not in dotted]}")

        sm = SequenceMatcher(None, ref, heard_cmp, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            s_, g_ = ref[i1:i2], heard_cmp[j1:j2]
            if tag == "equal" or not any("一" <= c <= "鿿" for c in s_):
                continue
            if not g_ or not any("一" <= c <= "鿿" for c in g_):
                continue
            if len(s_) >= 4 and len(g_) <= len(s_) // 2:
                continue
            ps, pg = py(s_), py(g_)
            if ps == pg or SequenceMatcher(None, ps, pg).ratio() >= 0.78:
                continue
            problems.append(f"「{s_}」聽成「{g_}」")

        mark = "🔴" if problems else ("⚠️" if warns else "✅")
        bad += bool(problems)
        print(f"{mark} 第{i:>2}句 {line['text'][:28]}")
        for p in problems + warns:
            print(f"      {p}　｜聽到：{heard[:60]}")
    print(f"\n{'全部通過' if not bad else f'{bad} 句有問題'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
