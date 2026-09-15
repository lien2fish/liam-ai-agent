# -*- coding: utf-8 -*-
"""統一搜尋：一個指令同時搜記憶、skill、規則、知識庫、決策、工作日誌。

結果分三層，照 OpenViking 的 L0／L1／L2 概念：
  L0  出處＋一句話摘要（記憶與 skill 的 description）
  L1  命中的段落與前後文
  L2  --full N 印出第 N 筆的整段原文

    python3 scripts/find_context.py 白帶魚
    python3 scripts/find_context.py IG 輪播 --in 記憶,skill
    python3 scripts/find_context.py 聚食釜 --full 1
    python3 scripts/find_context.py 限動 --since 7          # 日誌只看近 7 天

多個關鍵字用空白分開，命中越多個排越前面。只讀不寫，結果只印在終端機。
"""
import argparse
import glob
import math
import os
import re
from datetime import date, datetime

HOME = os.path.expanduser("~")
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS = os.path.join(HOME, "liam-workspace")
MEM_DIR = os.path.join(
    HOME, ".claude/projects/-Users-lien-Downloads-Liam-AI-agent/memory"
)

# (類別, glob 清單, 權重)
SOURCES = [
    ("記憶", [MEM_DIR + "/*.md"], 3.0),
    ("skill", [PROJECT + "/.claude/skills/**/*.md"], 2.5),
    (
        "規則",
        [
            PROJECT + "/CLAUDE.md",
            HOME + "/.claude/CLAUDE.md",
            HOME + "/.claude/USER.md",
        ],
        2.5,
    ),
    ("知識庫", [WS + "/knowledge/**/*.md"], 2.5),
    ("決策", [WS + "/DISCUSSIONS.md", WS + "/TODO.md", WS + "/plans/**/*.md"], 2.0),
    ("日誌", [WS + "/daily/20*.md"], 1.0),
]
CJK = re.compile(r"[一-鿿]")
SNIPPET_WIDTH = 90


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def split_frontmatter(text):
    if not text.startswith("---\n"):
        return {}, text, 0
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text, 0
    fm = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^\s*([\w-]+):\s*(.+)$", line)
        if m:
            fm.setdefault(m.group(1), m.group(2).strip())
    body_start = text.find("\n", end + 4) + 1
    return fm, text[body_start:], text[:body_start].count("\n")


def sections(body, offset):
    """依 markdown 標題切段；每段是一個檢索單位。"""
    out, head, start, buf = [], "", offset + 1, []
    for no, line in enumerate(body.splitlines(), offset + 1):
        if re.match(r"^#{1,4} ", line) and buf:
            out.append((head, start, buf))
            buf, start = [], no
        if re.match(r"^#{1,4} ", line):
            head = line.lstrip("#").strip()
        buf.append(line)
    if buf:
        out.append((head, start, buf))
    return out


def bigrams(term):
    return [term[i : i + 2] for i in range(len(term) - 1)]


def term_score(term, text_lower):
    t = term.lower()
    hits = text_lower.count(t)
    if hits:
        return 1.0, hits
    # 中文長詞允許部分命中（例：「白帶魚辨別」對到「白帶魚怎麼辨別」）
    if len(t) >= 3 and CJK.search(t):
        grams = bigrams(t)
        got = sum(1 for g in grams if g in text_lower)
        if got / len(grams) >= 0.6:
            return 0.5 * got / len(grams), 1
    return 0.0, 0


def snippet(lines, terms):
    shown = []
    for line in lines:
        low = line.lower()
        pos = min((low.find(t.lower()) for t in terms if t.lower() in low), default=-1)
        if pos < 0:
            continue
        s = max(0, pos - SNIPPET_WIDTH // 3)
        text = line[s : s + SNIPPET_WIDTH].strip()
        shown.append(
            ("…" if s else "") + text + ("…" if s + SNIPPET_WIDTH < len(line) else "")
        )
        if len(shown) == 2:
            break
    return shown


def daily_date(path):
    m = re.search(r"(20\d\d-\d\d-\d\d)\.md$", path)
    return datetime.strptime(m.group(1), "%Y-%m-%d").date() if m else None


def collect(terms, kinds, since):
    results = []
    for kind, patterns, weight in SOURCES:
        if kinds and kind not in kinds:
            continue
        paths = sorted({p for pat in patterns for p in glob.glob(pat, recursive=True)})
        for path in paths:
            if os.path.basename(path) == "MEMORY.md":
                continue
            d = daily_date(path) if kind == "日誌" else None
            if since is not None and d and (date.today() - d).days > since:
                continue
            text = read(path)
            fm, body, offset = split_frontmatter(text)
            summary = fm.get("description", "")
            meta = (fm.get("name", "") + " " + summary).lower()
            for head, start, lines in sections(body, offset):
                block = "\n".join(lines).lower()
                matched, score = 0, 0.0
                for t in terms:
                    s, hits = term_score(t, block)
                    ms, _ = term_score(t, meta)
                    hs, _ = term_score(t, head.lower())
                    if s or ms or hs:
                        matched += 1
                        score += s * (1 + math.log(1 + hits)) + ms * 2 + hs * 1.5
                if not matched:
                    continue
                if d:
                    age = (date.today() - d).days
                    score *= 1.3 if age <= 14 else 1.0
                results.append(
                    {
                        "kind": kind,
                        "path": path,
                        "line": start,
                        "head": head,
                        "summary": summary,
                        "date": d,
                        "lines": lines,
                        "matched": matched,
                        "score": score * weight,
                    }
                )
    results.sort(key=lambda r: (-r["matched"], -r["score"]))
    return results


def short(path):
    return path.replace(HOME, "~")


def main():
    ap = argparse.ArgumentParser(
        description="同時搜記憶、skill、規則、知識庫、決策、工作日誌"
    )
    ap.add_argument("terms", nargs="+", help="關鍵字，多個用空白分開")
    ap.add_argument(
        "--in",
        dest="kinds",
        help="只搜這些類別，逗號分隔：" + ",".join(s[0] for s in SOURCES),
    )
    ap.add_argument("--limit", type=int, default=8, help="顯示幾筆（預設 8）")
    ap.add_argument("--since", type=int, help="日誌只看最近 N 天")
    ap.add_argument("--full", type=int, metavar="N", help="印出第 N 筆的整段原文")
    ap.add_argument("--all-terms", action="store_true", help="每個關鍵字都要命中")
    args = ap.parse_args()

    kinds = set(args.kinds.split(",")) if args.kinds else None
    results = collect(args.terms, kinds, args.since)
    if args.all_terms:
        results = [r for r in results if r["matched"] == len(args.terms)]
    query = " ".join(args.terms)

    if not results:
        print("🔎 「%s」沒有找到" % query)
        return

    if args.full:
        if not 1 <= args.full <= len(results):
            print("只有 %d 筆結果" % len(results))
            return
        r = results[args.full - 1]
        print("📄 [%s] %s:%d\n" % (r["kind"], short(r["path"]), r["line"]))
        print("\n".join(r["lines"]))
        return

    by_kind = {}
    for r in results:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    print(
        "🔎 「%s」找到 %d 段（%s），顯示前 %d\n"
        % (
            query,
            len(results),
            "、".join("%s %d" % kv for kv in by_kind.items()),
            min(args.limit, len(results)),
        )
    )
    for i, r in enumerate(results[: args.limit], 1):
        name = os.path.basename(r["path"])
        if r["kind"] == "skill":
            name = os.path.relpath(r["path"], PROJECT + "/.claude/skills")
        head = " › " + r["head"][:40] if r["head"] else ""
        hit = (
            ""
            if len(args.terms) == 1
            else "　命中 %d/%d" % (r["matched"], len(args.terms))
        )
        print("%d. [%s] %s%s%s" % (i, r["kind"], name, head, hit))
        if r["summary"]:
            print("   摘要：" + r["summary"][:120])
        for s in snippet(r["lines"], args.terms):
            print("   " + s)
        print("   → %s:%d\n" % (short(r["path"]), r["line"]))
    if len(results) > args.limit:
        print(
            "還有 %d 段，加 --limit 看更多；--full N 看第 N 筆全文"
            % (len(results) - args.limit)
        )


if __name__ == "__main__":
    main()
