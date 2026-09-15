# -*- coding: utf-8 -*-
"""記憶健檢：檢查 Claude Code 記憶庫有沒有壞掉、放錯、過期或長太大。

只讀不寫，報告印在終端機（記憶內容含客戶與財務資訊，不存檔、不進版控）。

    python3 scripts/memory_doctor.py           # 完整報告
    python3 scripts/memory_doctor.py --quiet   # 只印 ❌ 與 ⚠️
    python3 scripts/memory_doctor.py --paths   # 列出每個找不到的檔案

有 ❌ 時 exit code = 1。
"""
import difflib
import hashlib
import os
import re
import sys
from datetime import date

HOME = os.path.expanduser("~")
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM_DIR = os.path.join(
    HOME, ".claude/projects/-Users-lien-Downloads-Liam-AI-agent/memory"
)
WS_MEM_DIR = os.path.join(HOME, "liam-workspace/memory")
INDEX = os.path.join(MEM_DIR, "MEMORY.md")

# Claude Code 每次開 session 只把 MEMORY.md 的前 200 行讀進來
INDEX_LINE_CAP = 200
INDEX_WARN_LINES = 160
INDEX_LINE_LEN = 200
BIG_FILE = 12 * 1024
# 0.6 會把「鑫海產／鑫酒藏 Excel 系統（同一天更新）」這種同範本描述誤判成重複
DUP_RATIO = 0.7
ARCHIVE_WORDS = ("封存", "停止投入", "已結案", "取消", "不主動提", "不再提")
# 同一行出現這些字，代表檔案本來就該不存在，不算斷掉
GONE_WORDS = (
    "已刪",
    "刪除",
    "刪掉",
    "停用",
    "不存在",
    "移除",
    "已不",
    "舊",
    "改名",
    "搬",
)
# 只收「未來要發生」的字眼；「待」「排程」太泛，會把「09-05 停排程」這種已完成的事誤報
PENDING_WORDS = ("預計", "驗收", "到期", "截止", "已排程", "待發", "待上傳", "待送印")
# 範本路徑、別的專案的相對路徑、暫存區，找不到是正常的
PATH_SKIP = re.compile(r"YYYY|MM-DD|~\d|^\./|scratchpad/|^src/|^\.streamlit/")
# 這幾則記憶的用途就是記錄「已經不在的檔案」
PATH_SKIP_FILES = ("reference_missing_after_migration.md",)
PATH_ROOTS = [
    PROJECT,
    os.path.join(HOME, "liam-workspace"),
    HOME,
    os.path.join(HOME, "fishing-tycoon"),
    os.path.join(HOME, "lien-plugins"),
]
PATH_RE = re.compile(
    r"`((?:~/|/|[\w一-鿿.\-]+/)[^`\s*{}<>]*"
    r"\.(?:py|js|sh|json|md|yml|yaml|toml|html|txt|csv|xlsx|numbers|pdf|ai))`"
)
DATE_RE = re.compile(r"(?:(20\d\d)[-/])?(\d{1,2})[-/](\d{1,2})")

issues = {"❌": [], "⚠️": [], "ℹ️": []}


def add(level, msg):
    issues[level].append(msg)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def frontmatter(text):
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fm = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^(\s*)([\w-]+):\s*(.*)$", line)
        if m:
            fm.setdefault(m.group(2), m.group(3).strip().strip("\"'"))
    return fm


def parse_index():
    entries, section = [], ""
    for no, line in enumerate(read(INDEX).splitlines(), 1):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        m = re.match(r"^- \[(.+?)\]\(([^)]+\.md)\)\s*(.*)$", line)
        if m:
            entries.append(
                {
                    "no": no,
                    "title": m.group(1),
                    "file": m.group(2),
                    "hook": m.group(3),
                    "section": section,
                    "line": line,
                }
            )
    return entries


def check_index(entries, files):
    lines = read(INDEX).splitlines()
    size = os.path.getsize(INDEX)
    level = "⚠️" if len(lines) >= INDEX_WARN_LINES else "ℹ️"
    add(
        level,
        "索引 %d 行／%.1fKB（Claude Code 只讀前 %d 行）"
        % (len(lines), size / 1024, INDEX_LINE_CAP),
    )
    if len(lines) > INDEX_LINE_CAP:
        add(
            "❌",
            "索引超過 %d 行，第 %d 行之後的記憶每次開 session 都讀不到"
            % (INDEX_LINE_CAP, INDEX_LINE_CAP + 1),
        )

    listed = {e["file"] for e in entries}
    for e in entries:
        if e["file"] not in files:
            add("❌", "索引第 %d 行指向不存在的檔案：%s" % (e["no"], e["file"]))
    for f in sorted(files - listed):
        add("⚠️", "檔案沒有列進索引（讀不到）：%s" % f)

    seen = {}
    for e in entries:
        if e["file"] in seen:
            add(
                "⚠️",
                "同一個檔案在索引出現兩次：%s（第 %d、%d 行）"
                % (e["file"], seen[e["file"]], e["no"]),
            )
        seen[e["file"]] = e["no"]

    for e in entries:
        if len(e["line"]) > INDEX_LINE_LEN:
            add(
                "⚠️",
                "索引第 %d 行 %d 字，太長會吃掉每次開 session 的額度：%s"
                % (e["no"], len(e["line"]), e["title"]),
            )


def check_archive_section(entries):
    for e in entries:
        if "封存" not in e["section"]:
            continue
        path = os.path.join(MEM_DIR, e["file"])
        body = read(path) if os.path.exists(path) else ""
        if not any(w in e["line"] or w in body[:600] for w in ARCHIVE_WORDS):
            add(
                "❌",
                "放在「%s」底下但內容看不出已封存，可能分類放錯：%s（第 %d 行）"
                % (e["section"], e["title"], e["no"]),
            )


def check_files(files):
    names = {}
    for f in sorted(files):
        path = os.path.join(MEM_DIR, f)
        text = read(path)
        fm = frontmatter(text)
        if fm is None:
            add("❌", "沒有 frontmatter：%s" % f)
            continue
        for key in ("name", "description", "type"):
            if not fm.get(key):
                add("❌", "frontmatter 缺 %s：%s" % (key, f))
        if fm.get("type") not in (None, "", "user", "feedback", "project", "reference"):
            add(
                "⚠️",
                "type 不是 user/feedback/project/reference：%s（%s）"
                % (f, fm.get("type")),
            )
        if re.search(r"^type:", text[: text.find("\n---", 4)], re.M):
            add("ℹ️", "舊版格式（type 不在 metadata 底下）：%s" % f)
        if fm.get("name"):
            names.setdefault(fm["name"], []).append(f)
        size = os.path.getsize(path)
        if size > BIG_FILE:
            add(
                "⚠️",
                "檔案 %.1fKB，讀一次很吃 context，考慮拆分或精簡：%s"
                % (size / 1024, f),
            )
    for name, fs in names.items():
        if len(fs) > 1:
            add("❌", "name 重複「%s」：%s" % (name, "、".join(fs)))
    return names


def slug(s):
    return s.lower().replace(".md", "").replace("_", "-")


def check_links(files, names):
    known = {slug(n) for n in names} | {slug(f) for f in files}
    unwritten = {}
    for f in files:
        for link in re.findall(r"\[\[([^\]]+)\]\]", read(os.path.join(MEM_DIR, f))):
            if slug(link) not in known:
                unwritten.setdefault(link, []).append(f)
    if unwritten:
        top = sorted(unwritten.items(), key=lambda kv: -len(kv[1]))[:8]
        add(
            "ℹ️",
            "有 %d 個 [[連結]] 指向還沒寫的主題（不是錯誤）。被引用最多：%s"
            % (len(unwritten), "、".join("%s×%d" % (k, len(v)) for k, v in top)),
        )


def resolve(ref):
    if ref.startswith("~/"):
        return [os.path.expanduser(ref)]
    if ref.startswith("/"):
        return [ref]
    return [os.path.join(root, ref) for root in PATH_ROOTS]


def check_paths(files, detail):
    missing = []
    for f in sorted(files):
        if f in PATH_SKIP_FILES:
            continue
        for no, line in enumerate(read(os.path.join(MEM_DIR, f)).splitlines(), 1):
            if any(w in line for w in GONE_WORDS):
                continue
            for ref in PATH_RE.findall(line):
                if PATH_SKIP.search(ref):
                    continue
                if not any(os.path.exists(p) for p in resolve(ref)):
                    missing.append("%s:%d → %s" % (f, no, ref))
    if not missing:
        return
    # 多半是已完成或已取消專案留下的舊路徑，逐條列會淹沒真正要修的問題
    add(
        "⚠️",
        "%d 則記憶提到 %d 個找不到的檔案%s"
        % (
            len({m.split(":")[0] for m in missing}),
            len(missing),
            "" if detail else "（加 --paths 看明細）",
        ),
    )
    if detail:
        for m in missing:
            add("ℹ️", "　找不到：" + m)


def check_duplicates(files):
    desc = {}
    for f in files:
        fm = frontmatter(read(os.path.join(MEM_DIR, f))) or {}
        if fm.get("description"):
            desc[f] = fm["description"]
    keys = sorted(desc)
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            ratio = difflib.SequenceMatcher(None, desc[a], desc[b]).ratio()
            if ratio >= DUP_RATIO:
                add(
                    "⚠️",
                    "兩則記憶描述很像（%.0f%%），可能重複：%s ↔ %s"
                    % (ratio * 100, a, b),
                )


def check_stale(entries):
    today = date.today()
    for e in entries:
        text = e["title"] + " " + e["hook"]
        if not any(w in text for w in PENDING_WORDS):
            continue
        dates = []
        for y, m, d in DATE_RE.findall(text):
            try:
                dates.append(date(int(y) if y else today.year, int(m), int(d)))
            except ValueError:
                continue
        # 看最晚的那個日期——「09-13 起測試、10/13 驗收」要到 10/13 過了才算過期
        if dates and max(dates) < today:
            add(
                "⚠️",
                "索引寫著待辦性質的日期 %s 已經過了，內容可能過期：%s（第 %d 行）"
                % (max(dates).isoformat(), e["title"], e["no"]),
            )


def check_sync(files):
    if not os.path.isdir(WS_MEM_DIR):
        add("ℹ️", "找不到私人 repo 的 memory/，略過同步檢查")
        return
    ws = {f for f in os.listdir(WS_MEM_DIR) if f.endswith(".md")}
    local = files | {"MEMORY.md"}

    def digest(d, f):
        return hashlib.sha256(open(os.path.join(d, f), "rb").read()).hexdigest()

    only_local = sorted(local - ws)
    only_ws = sorted(ws - local)
    changed = sorted(
        f for f in local & ws if digest(MEM_DIR, f) != digest(WS_MEM_DIR, f)
    )
    if only_local or only_ws or changed:
        add(
            "⚠️",
            "本機與私人 repo 不同步（手機看到的是舊版）：本機獨有 %d、repo 獨有 %d、內容不同 %d → 跑 sync_workspace.sh push"
            % (len(only_local), len(only_ws), len(changed)),
        )
        for f in (only_local + only_ws + changed)[:10]:
            add("ℹ️", "　不同步：%s" % f)
    else:
        add("ℹ️", "本機與私人 repo 同步 ✓")


def main():
    quiet = "--quiet" in sys.argv
    files = {f for f in os.listdir(MEM_DIR) if f.endswith(".md") and f != "MEMORY.md"}
    entries = parse_index()

    check_index(entries, files)
    check_archive_section(entries)
    names = check_files(files)
    check_links(files, names)
    check_paths(files, "--paths" in sys.argv)
    check_duplicates(files)
    check_stale(entries)
    check_sync(files)

    print("🩺 記憶健檢　%s　共 %d 則記憶\n" % (date.today().isoformat(), len(files)))
    for level, title in (("❌", "要修"), ("⚠️", "建議看一下"), ("ℹ️", "資訊")):
        if quiet and level == "ℹ️":
            continue
        if not issues[level]:
            continue
        print("%s %s（%d）" % (level, title, len(issues[level])))
        for msg in issues[level]:
            print("  - " + msg)
        print()
    if not issues["❌"] and not issues["⚠️"]:
        print("✅ 沒有需要處理的問題")
    sys.exit(1 if issues["❌"] else 0)


if __name__ == "__main__":
    main()
