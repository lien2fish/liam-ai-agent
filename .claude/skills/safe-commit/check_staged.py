#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""commit 前掃描暫存區，找出不該進公開版控的東西。

用法：
    python3 .claude/skills/safe-commit/check_staged.py          掃 git 暫存區
    python3 .claude/skills/safe-commit/check_staged.py <檔案…>  掃指定檔案

回傳碼 1＝有 ❌，別 commit。0＝過關。
⚠️ 這支是輔助，不是保證。它抓得到樣式，抓不到「這份資料的意義」——最後仍要人看過。
"""
import os
import re
import subprocess
import sys

# 檔名／路徑本身就該擋的
PATH_BLOCK = [
    (r"(^|/)客戶名單/", "客戶名單資料夾"),
    (r"(^|/)財務/", "財務資料夾"),
    (r"名單.*\.(csv|xlsx|numbers)$", "名單類資料檔"),
    (r"資產負債|balance_sheet", "財務報表"),
    (r"policy_data|保單", "保單資料"),
    (r"credential|token|secret|\.key$|\.pem$", "憑證或金鑰"),
    (r"身分證|identity", "身分證相關"),
]

# 執行日誌會逐條列出往來的銀行與平台名稱，比想像中洩漏更多
PATH_WARN = [
    (r"_log\.txt$|(^|/)log[s]?/", "執行日誌——常夾帶往來機構名稱"),
]

# 內容樣式
CONTENT_BLOCK = [
    (r"\b[A-Z][12]\d{8}\b", "疑似身分證號"),
    (r"\b09\d{2}[- ]?\d{3}[- ]?\d{3}\b", "疑似手機號碼"),
    (r"sk-[A-Za-z0-9_-]{20,}", "疑似 OpenAI／Anthropic 金鑰"),
    (r"gh[pousr]_[A-Za-z0-9]{20,}", "疑似 GitHub token"),
    (r"AIza[A-Za-z0-9_-]{30,}", "疑似 Google API 金鑰"),
    (r"EAA[A-Za-z0-9]{40,}", "疑似 Meta／FB token"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "疑似 Slack token"),
]

# 資料檔的欄位標題——比猜值的格式可靠得多。
# （2026-08-21 實測：客戶名單的電話被 Excel 吃掉開頭的 0 變 9 碼，值的正則抓不到，標題抓得到。）
HEADER_BLOCK = [
    ("姓名", "客戶姓名"),
    ("電話", "電話"),
    ("手機", "手機"),
    ("地址", "地址"),
    ("身分證", "身分證號"),
    ("Email", "Email"),
    ("e-mail", "Email"),
    ("累計消費", "消費金額"),
    ("訂購金額", "訂購金額"),
]

# 需要人看一眼，但不一定是問題
CONTENT_WARN = [
    (r"姓名\s*[,，]\s*電話", "含姓名＋電話的欄位標題"),
    (r"[\w.+-]+@[\w-]+\.[\w.]+", "含 Email 位址"),
    (r"統一?編號\s*[:：,]", "含統編欄位"),
]

DATA_EXT = (".csv", ".xlsx", ".xls", ".numbers", ".db", ".sqlite", ".json")
SKIP_EXT = (".png", ".jpg", ".jpeg", ".mp4", ".mov", ".wav", ".pdf", ".ttf", ".ttc")


def staged_files():
    # ⚠️ core.quotepath=false 不能省：預設會把中文檔名輸出成八進位跳脫，
    # 檔案開不起來又不會報錯，中文檔名的檔案會被靜默跳過（踩過三次）。
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false",
         "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
    ).stdout
    return [l for l in out.splitlines() if l.strip()]


def scan(path):
    """回傳 (errors, warnings)。"""
    errs, warns = [], []

    for pat, why in PATH_BLOCK:
        if re.search(pat, path):
            errs.append("路徑符合「%s」" % why)

    if path.lower().endswith(SKIP_EXT):
        return errs, warns

    for pat, why in PATH_WARN:
        if re.search(pat, path, re.I):
            warns.append(why)

    if path.lower().endswith(DATA_EXT):
        warns.append("資料檔——打開確認過內容再進版控")
        head = ""
        try:
            head = open(path, encoding="utf-8-sig", errors="ignore").readline()
        except OSError:
            pass
        hit = [why for key, why in HEADER_BLOCK if key.lower() in head.lower()]
        if hit:
            errs.append("欄位標題含" + "、".join(sorted(set(hit))))

    if not os.path.exists(path):
        return errs, warns
    try:
        text = open(path, encoding="utf-8", errors="ignore").read(400_000)
    except OSError:
        return errs, warns

    for pat, why in CONTENT_BLOCK:
        if re.search(pat, text):
            errs.append(why)

    # Markdown／文字報告裡的人名表格——48 份含客戶姓名的報告當初就是這樣漏掉的
    if re.search(r"\|\s*(客戶|姓名|名稱|社友|會員)\s*\|", text):
        rows = len(re.findall(r"(?m)^\|\s*[一-\u9fff]{2,6}[^|]{0,8}\s*\|", text))
        if rows:
            errs.append("含人名表格（%d 列）" % rows)
    for pat, why in CONTENT_WARN:
        if re.search(pat, text):
            warns.append(why)
    return errs, warns


def main():
    files = sys.argv[1:] or staged_files()
    if not files:
        print("暫存區沒有檔案，沒東西可檢查。")
        return 0

    bad, warned = [], []
    for f in files:
        errs, warns = scan(f)
        if errs:
            bad.append((f, sorted(set(errs))))
        elif warns:
            warned.append((f, sorted(set(warns))))

    print("檢查 %d 個檔案\n" % len(files))
    for f, reasons in bad:
        print("❌ %s" % f)
        for r in reasons:
            print("     %s" % r)
    for f, reasons in warned:
        print("⚠️  %s" % f)
        for r in reasons:
            print("     %s" % r)

    if bad:
        print("\n有 ❌，不要 commit。先確認這些檔案該去哪：")
        print("  絕不進 repo → 留本機　／　含個資或財務 → liam-workspace（私人）")
        print("  確定無害 → 公開 repo，但要逐檔看過")
        return 1
    if warned:
        print("\n沒有 ❌，但上面的 ⚠️ 要人看過才 commit。")
        return 0
    print("✅ 沒有發現敏感樣式。仍請確認資料的「意義」——樣式抓不到的東西只有你知道。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
