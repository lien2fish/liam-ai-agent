"""事實查核閘門：腳本裡每個數字、法條都要對得到 facts.json，對不到就不准渲染。

規則
1. 每條被引用的 fact 至少兩個來源、其中至少一個 official。
2. 每句台詞與畫面字裡的阿拉伯數字、中文數字，都要出現在該句引用 fact 的
   tokens／來源名稱／引文裡。約略說法（「八千兩百多」）寫在該句的 approx。
3. 開場對話是角色劇情，劇情用的數字寫在 fiction，不必對事實表。
4. 不准出現 facts.json 的 rejected 說法的關鍵詞。

用法：python3 finance_shorts/verify.py [ins-01 ...]
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
FACTS = json.loads((ROOT / "facts.json").read_text())
SCRIPTS = json.loads((ROOT / "scripts.json").read_text())

REJECTED_PATTERNS = [r"受益人.{0,8}(早|先)(走|過世|身故).{0,12}遺產"]

CN_DIGIT = {
    "零": 0,
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
CN_UNIT = {"十": 10, "百": 100, "千": 1000}
CN_RE = re.compile(r"[零一二兩三四五六七八九十百千]+")


def cn_to_int(s):
    total, cur = 0, 0
    for ch in s:
        if ch in CN_DIGIT:
            cur = CN_DIGIT[ch]
        else:
            total += (cur or 1) * CN_UNIT[ch]
            cur = 0
    return total + cur


def screen_text(screen):
    if not screen:
        return ""
    parts = []
    for v in screen.values():
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            for item in v:
                parts.append(
                    json.dumps(item, ensure_ascii=False)
                    if isinstance(item, dict)
                    else str(item)
                )
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            parts.append(str(v))
    return " ".join(parts)


def fact_haystack(fid):
    f = FACTS["facts"][fid]
    parts = [f["claim"], " ".join(f["tokens"])]
    for s in f["sources"]:
        parts += [s["name"], s["quote"]]
    return " ".join(parts)


def norm_numbers(text):
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def check_episode(eid, ep):
    errors = []
    for i, line in enumerate(ep["lines"], 1):
        tag = f"{eid} 第{i}句"
        fids = line.get("facts", [])
        for fid in fids:
            if fid not in FACTS["facts"]:
                errors.append(f"{tag}：引用不存在的 {fid}")
                continue
            srcs = FACTS["facts"][fid]["sources"]
            if len(srcs) < 2:
                errors.append(f"{tag}：{fid} 只有 {len(srcs)} 個來源")
            if not any(s["official"] for s in srcs) and not FACTS["facts"][fid].get("exception"):
                errors.append(f"{tag}：{fid} 沒有官方來源")
            must = FACTS["facts"][fid].get("must_say")
            if must and must not in line["text"]:
                errors.append(f"{tag}：{fid} 是核准的例外，這句要講明「{must}」")

        hay = " ".join(fact_haystack(f) for f in fids if f in FACTS["facts"])
        hay_nums = norm_numbers(hay)
        allowed_text = set(line.get("fiction", [])) | set(line.get("approx", {}).keys())
        for target in line.get("approx", {}).values():
            if target.replace(",", "") not in hay_nums and target not in hay:
                errors.append(f"{tag}：approx 對應的「{target}」不在引用的事實裡")

        text = line["text"] + " " + line.get("sub", "")
        shown = screen_text(line.get("screen"))
        for n in norm_numbers(text + " " + shown):
            if n not in hay_nums:
                errors.append(f"{tag}：數字 {n} 對不到事實表（引用 {fids or '無'}）")

        spoken = text
        # 不是數量的常見詞：「零利率」「兩個規則」不該被當成 0、2 去對事實表
        for phrase in ("零利率", "停在零", "兩個", "兩年", "兩邊", "三級會議", "第二", "第三", "三條線", "三件事", "百分點", "百貨", "二手", "零容忍", "兩天", "第四"):
            spoken = spoken.replace(phrase, "")
        for phrase in sorted(allowed_text, key=len, reverse=True):
            spoken = spoken.replace(phrase, "")
        for m in CN_RE.finditer(spoken):
            word = m.group()
            if word == "一" or any(
                word in w for w in ("一樣", "一件", "一起", "一眼", "一致", "第一")
            ):
                continue
            n = str(cn_to_int(word))
            if n not in hay_nums:
                errors.append(f"{tag}：中文數字「{word}」({n}) 對不到事實表")

        for pat in REJECTED_PATTERNS:
            if re.search(pat, text + shown):
                errors.append(f"{tag}：出現已否決的說法（{pat}）")
    return errors


def main():
    wanted = sys.argv[1:] or list(SCRIPTS["episodes"])
    all_errors = []
    for eid in wanted:
        errs = check_episode(eid, SCRIPTS["episodes"][eid])
        print(f"{'✅' if not errs else '❌'} {eid} {SCRIPTS['episodes'][eid]['title']}")
        for e in errs:
            print("   ", e)
        all_errors += errs
    sys.exit(1 if all_errors else 0)


if __name__ == "__main__":
    main()
