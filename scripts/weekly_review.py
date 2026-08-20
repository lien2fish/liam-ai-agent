#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每週總經理週報：把上週的工作日誌、程式改動、自動化執行狀況整理成一份正式報告。

資料來源全部是既有產物，不額外埋點：
  workspace/daily/*.md    每次 session 做了什麼（SessionEnd hook 產）
  公開 repo 的 git log     人為改動（自動化 chore commit 會濾掉）
  GitHub Actions runs API  17 個排程任務的成功／失敗
  workspace/TODO.md 的 diff 待辦進度

⚠️ 報告含客戶姓名與報價，只寫進私人 repo liam-workspace 與 Email，不進公開 repo。
"""
import argparse
import json
import os
import re
import smtplib
import ssl
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

CLAUDE_MODEL = (
    "claude-sonnet-5"  # 省錢可改 "claude-haiku-4-5"，但「可精進的地方」品質會變差
)
MAX_TOKENS = 8000

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
sys.path.insert(0, BASE)
from md_to_pdf import md_to_story

ADDR = "lien2fish@gmail.com"
GH_REPO = "lien2fish/liam-ai-agent"

# 自動化排程自己 commit 的訊息，不算人為工作
AUTO_COMMIT = re.compile(
    r"(市場日報|更新漁獲行情|Add IG post|YouTube 留言通知|YouTube 頻道日報"
    r"|回購提醒報告|產險到期提醒|Gmail 報告|Update seafood history"
    r"|yt: recent topic|更新限動預告選片紀錄|限動預告影片|清掉過期限動影片|Notion 月報)"
)


def week_range(week_arg):
    """回傳 (週一, 週日, 'YYYY-Www')。預設＝上一個完整的週一~週日。"""
    if week_arg:
        y, w = week_arg.upper().split("-W")
        monday = date.fromisocalendar(int(y), int(w), 1)
    else:
        today = date.today()
        monday = today - timedelta(days=today.weekday() + 7)
    sunday = monday + timedelta(days=6)
    iso = monday.isocalendar()
    return monday, sunday, "%d-W%02d" % (iso[0], iso[1])


def read_daily(ws, monday, sunday):
    out = []
    d = monday
    while d <= sunday:
        p = os.path.join(ws, "daily", d.isoformat() + ".md")
        if os.path.exists(p):
            out.append(open(p, encoding="utf-8").read())
        d += timedelta(days=1)
    return "\n\n".join(out) or "（本週沒有工作日誌）"


def read_commits(monday, sunday):
    raw = subprocess.run(
        [
            "git",
            "log",
            "--no-merges",
            "--date=short",
            "--pretty=format:%cd %s",
            "--since",
            monday.isoformat() + " 00:00:00",
            "--until",
            sunday.isoformat() + " 23:59:59",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    ).stdout

    lines = [
        "- " + l for l in raw.splitlines() if l.strip() and not AUTO_COMMIT.search(l)
    ]
    return "\n".join(lines) or "（本週沒有人為程式改動）"


def read_actions(monday, sunday):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return "（無 GITHUB_TOKEN，略過自動化執行統計）"
    stats, page = {}, 1
    while page <= 10:
        url = (
            "https://api.github.com/repos/%s/actions/runs"
            "?created=%s..%s&per_page=100&page=%d"
            % (GH_REPO, monday.isoformat(), sunday.isoformat(), page)
        )
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "User-Agent": "liam-weekly-review",
            },
        )
        try:
            data = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:
            return "（讀取 Actions 紀錄失敗：%s）" % e
        runs = data.get("workflow_runs", [])
        if not runs:
            break
        for r in runs:
            s = stats.setdefault(r["name"], {"ok": 0, "fail": 0, "other": 0})
            c = r.get("conclusion")
            s["ok" if c == "success" else "fail" if c == "failure" else "other"] += 1
        if len(runs) < 100:
            break
        page += 1

    rows = ["| 任務 | 成功 | 失敗 | 其他 |", "|---|---|---|---|"]
    for name in sorted(stats, key=lambda n: (-stats[n]["fail"], n)):
        s = stats[name]
        rows.append("| %s | %d | %d | %d |" % (name, s["ok"], s["fail"], s["other"]))
    return "\n".join(rows) if stats else "（本週沒有任何 Actions 執行紀錄）"


def read_todo_diff(ws, monday, sunday):
    raw = subprocess.run(
        [
            "git",
            "log",
            "-p",
            "--no-merges",
            "--since",
            monday.isoformat() + " 00:00:00",
            "--until",
            sunday.isoformat() + " 23:59:59",
            "--",
            "TODO.md",
        ],
        cwd=ws,
        capture_output=True,
        text=True,
    ).stdout
    changes = [
        l
        for l in raw.splitlines()
        if (l.startswith("+") or l.startswith("-"))
        and not l.startswith(("+++", "---"))
        and l[1:].strip()
    ]
    return "\n".join(changes[:200]) or "（本週 TODO.md 沒有變動）"


PROMPT = """你是鉅鑫管理顧問有限公司的 AI 技術幕僚，要向老闆 Lien 提交本期工作週報。
語氣像一位總經理向董事長報告：務實、有數字、直說問題，不寫空泛鼓勵、不用行銷語彙。
一律使用繁體中文。表格優先於長段文字。

Lien 的事業版圖：鉅鑫管理顧問、鑫酒坊（葡萄酒）、鑫茶坊（茶葉）、匠鑫私廚、
龜吼現流活海產（2026 建置中）；另有磊山保經業務、惜食台灣行動協會志工、
中城網路扶輪社，以及自建的內容產線（IG/FB、YouTube 三個頻道、短影音）。

報告期間：{monday} ~ {sunday}（{iso}）

=== 素材一：每日工作日誌（Lien 每次交辦的原話） ===
{daily}

=== 素材二：本期人為程式改動（自動化排程的 commit 已濾除） ===
{commits}

=== 素材三：自動化排程執行統計 ===
{actions}

=== 素材四：待辦清單變動 ===
{todo}

請輸出一份 Markdown 報告，**嚴格照下列五個章節、不要加其他章節、不要寫開場白**：

## 一、本期成果
一段兩三句的總述，接一個表格：| 專案 | 進度 | 具體產出 |。
進度只寫「已結案／進行中／暫停」。具體產出要寫得出檔名、支數、面數這種可查核的東西，
沒有就寫「無可查核產出」，不要膨風。

## 二、自動化營運狀況
根據素材三的表格說明。有失敗的任務要單獨點名並推測原因（例如金鑰到期、額度用完、
GitHub 高頻排程 delay）。全部正常就直說全部正常，不要湊字。

## 三、可精進的地方
三到五點。每點格式固定為「**現象**：…（引素材中的事實）→ **建議**：…」。
特別注意反覆返工的環節（同一個版面改超過五次、同一個錯誤修兩次以上），
指出下次怎麼一次到位。沒有值得檢討的就寫少一點，不要硬湊。

## 四、尚未解決／卡住的
表格：| 項目 | 卡在什麼 | 卡在誰身上 |。「卡在誰身上」只填「Lien」「AI」或「外部（廠商／協會／平台）」。

## 五、下期建議推進
表格：| 優先序 | 建議事項 | 為什麼值得做 | 預估工時 |，依投報率排序，最多五項。
表格後補一段「值得多想的方向」，一到三點，寫那種還沒被提過、但從本期素材看得出機會的延伸，
例如某條產線的產出可以餵給另一條、某個重複人工可以自動化。"""


def call_claude(prompt):
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("缺 ANTHROPIC_API_KEY")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(
            {
                "model": CLAUDE_MODEL,
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode(),
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    data = json.load(urllib.request.urlopen(req, timeout=300))
    if "content" not in data:
        raise RuntimeError("Claude 回傳異常：%s" % data)
    # Sonnet 5 預設開 adaptive thinking，content[0] 可能是 thinking block
    text = next((b["text"] for b in data["content"] if b.get("type") == "text"), "")
    if not text.strip():
        raise RuntimeError("Claude 回應沒有文字內容")
    return text.strip()


def build_report_pdf(pdf_path, md_path, monday, sunday, iso):
    """封面＋內文＋頁碼。內文排版沿用 md_to_pdf 的 md_to_story，不重複實作。"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    NAVY = colors.HexColor("#1F4E79")
    center = ParagraphStyle(
        "c",
        fontName="NotoTC",
        fontSize=13,
        leading=20,
        alignment=1,
        textColor=colors.HexColor("#555"),
    )
    big = ParagraphStyle(
        "big", fontName="NotoTC", fontSize=26, leading=38, alignment=1, textColor=NAVY
    )
    period = ParagraphStyle(
        "p",
        fontName="NotoTC",
        fontSize=15,
        leading=24,
        alignment=1,
        textColor=colors.HexColor("#333"),
    )
    note = ParagraphStyle(
        "n",
        fontName="NotoTC",
        fontSize=8.5,
        leading=13,
        alignment=1,
        textColor=colors.HexColor("#999"),
    )

    meta = Table(
        [
            ["報告期別", iso],
            ["涵蓋期間", "%s ~ %s" % (monday, sunday)],
            ["製表日期", date.today().isoformat()],
            ["呈報對象", "連傳正 董事長"],
            ["製表單位", "Liam AI Agent"],
        ],
        colWidths=[35 * mm, 75 * mm],
        hAlign="CENTER",
    )
    meta.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "NotoTC"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#666")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F6FA")),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#D6E2EC")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D6E2EC")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    rule = Table([[""]], colWidths=[60 * mm], rowHeights=[2], hAlign="CENTER")
    rule.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY)]))

    story = [
        Spacer(1, 55 * mm),
        Paragraph("鉅鑫管理顧問有限公司", center),
        Spacer(1, 6 * mm),
        rule,
        Spacer(1, 10 * mm),
        Paragraph("AI 技術幕僚<br/>工作週報", big),
        Spacer(1, 8 * mm),
        Paragraph("%s ~ %s" % (monday, sunday), period),
        Spacer(1, 22 * mm),
        meta,
        Spacer(1, 26 * mm),
        Paragraph("資料來源：每日工作日誌、程式版本紀錄、自動化排程執行紀錄", note),
        Paragraph(
            "本報告含客戶資訊，僅存於私人資料庫與電子郵件，未進入公開程式庫", note
        ),
        PageBreak(),
    ]
    story += md_to_story(md_path)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("NotoTC", 8)
        canvas.setFillColor(colors.HexColor("#999"))
        if doc.page > 1:
            canvas.drawString(15 * mm, 12 * mm, "鉅鑫管理顧問 · AI 工作週報 %s" % iso)
            canvas.drawRightString(
                A4[0] - 15 * mm, 12 * mm, "第 %d 頁" % (doc.page - 1)
            )
        canvas.restoreState()

    SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        title="AI 工作週報 %s" % iso,
        author="Liam AI Agent",
        topMargin=20 * mm,
        bottomMargin=22 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    print("OK: %s" % pdf_path)


def build_email_html(iso, monday, sunday, body_md):
    html = []
    for line in body_md.splitlines():
        s = line.rstrip()
        if s.startswith("## "):
            html.append(
                '<h3 style="color:#1F4E79;border-bottom:2px solid #DEEAF1;'
                'padding-bottom:4px;margin-top:22px">%s</h3>' % s[3:]
            )
        elif s.startswith("|"):
            html.append(s)
        elif s.startswith("- "):
            html.append("<p style='margin:4px 0 4px 14px'>• %s</p>" % s[2:])
        elif s.strip():
            html.append("<p>%s</p>" % s)
    text = "\n".join(html)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(
        r"`([^`]+)`",
        r"<code style='background:#F2F6FA;padding:1px 4px;border-radius:3px'>\1</code>",
        text,
    )
    text = md_tables_to_html(text)
    return f"""<div style="font-family:-apple-system,'PingFang TC',sans-serif;max-width:720px;color:#222;line-height:1.65">
<h2 style="color:#1F4E79;margin-bottom:4px">📋 AI 技術幕僚 · 工作週報 {iso}</h2>
<p style="color:#888;margin-top:0">涵蓋期間 {monday} ~ {sunday}｜完整版 PDF 見附件</p>
{text}
<p style="color:#888;font-size:13px;margin-top:24px">報告全文已存入私人資料庫 liam-workspace/reviews/{iso}.md<br>— Liam AI Agent</p>
</div>"""


def md_tables_to_html(text):
    out, buf = [], []
    for line in text.splitlines():
        if line.startswith("|"):
            buf.append(line)
            continue
        if buf:
            out.append(_table(buf))
            buf = []
        out.append(line)
    if buf:
        out.append(_table(buf))
    return "\n".join(out)


def _table(rows):
    cells = [
        [c.strip() for c in r.strip("|").split("|")]
        for r in rows
        if not re.match(r"^\|[\s\-:|]+\|$", r)
    ]
    if not cells:
        return ""
    head = "".join('<th style="padding:6px">%s</th>' % c for c in cells[0])
    body = ""
    for i, row in enumerate(cells[1:]):
        bg = "#DEEAF1" if i % 2 else "#fff"
        body += '<tr style="background:%s">%s</tr>' % (
            bg,
            "".join(
                '<td style="padding:5px 7px;border:1px solid #ccc">%s</td>' % c
                for c in row
            ),
        )
    return (
        '<table style="border-collapse:collapse;width:100%%;font-size:13px;margin:8px 0">'
        '<tr style="background:#1F4E79;color:#fff">%s</tr>%s</table>' % (head, body)
    )


def send_mail(subject, html, pdf_path):
    pw = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not pw:
        print("⚠️ 缺 GMAIL_APP_PASSWORD，略過寄信")
        return
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = formataddr(("Liam AI Agent", ADDR))
    msg["To"] = ADDR
    msg.attach(MIMEText(html, "html", "utf-8"))
    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
    part.add_header(
        "Content-Disposition", "attachment", filename=os.path.basename(pdf_path)
    )
    msg.attach(part)
    with smtplib.SMTP_SSL(
        "smtp.gmail.com", 465, context=ssl.create_default_context()
    ) as s:
        s.login(ADDR, pw)
        s.send_message(msg)
    print("✅ 已寄出：%s" % subject)


def commit_workspace(ws, iso):
    subprocess.run(["git", "add", "reviews/"], cwd=ws)
    r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ws)
    if r.returncode == 0:
        print("workspace 無變動，略過 commit")
        return
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Liam AI Agent",
            "-c",
            "user.email=lien2fish@gmail.com",
            "commit",
            "-q",
            "-m",
            "review: 工作週報 %s" % iso,
        ],
        cwd=ws,
    )
    subprocess.run(["git", "push", "-q"], cwd=ws)
    print("✅ 已推送週報到 liam-workspace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", help="指定週次，例如 2026-W33；預設為上一個完整週")
    ap.add_argument("--workspace", default=None, help="liam-workspace 路徑")
    ap.add_argument("--dry-run", action="store_true", help="只產檔，不寄信不 commit")
    args = ap.parse_args()

    ws = args.workspace or (
        os.path.join(REPO, "workspace")
        if os.path.isdir(os.path.join(REPO, "workspace"))
        else os.path.expanduser("~/liam-workspace")
    )
    monday, sunday, iso = week_range(args.week)
    print("報告期間 %s ~ %s（%s）\nworkspace: %s" % (monday, sunday, iso, ws))

    prompt = PROMPT.format(
        monday=monday,
        sunday=sunday,
        iso=iso,
        daily=read_daily(ws, monday, sunday),
        commits=read_commits(monday, sunday),
        actions=read_actions(monday, sunday),
        todo=read_todo_diff(ws, monday, sunday),
    )
    print("素材長度 %d 字元" % len(prompt))

    body = call_claude(prompt)

    outdir = os.path.join(ws, "reviews")
    os.makedirs(outdir, exist_ok=True)
    md_path = os.path.join(outdir, iso + ".md")
    header = "# 工作週報 %s\n\n> 涵蓋期間 %s ~ %s ｜ 製表 %s\n\n" % (
        iso,
        monday,
        sunday,
        date.today().isoformat(),
    )
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(header + body + "\n")
    print("✅ Markdown：%s" % md_path)

    pdf_path = os.path.join(outdir, "工作週報_%s.pdf" % iso)
    build_report_pdf(pdf_path, md_path, monday, sunday, iso)

    if args.dry_run:
        print("dry-run：不寄信、不 commit")
        return

    send_mail(
        "📋 AI 工作週報 %s（%s ~ %s）" % (iso, monday, sunday),
        build_email_html(iso, monday, sunday, body),
        pdf_path,
    )
    commit_workspace(ws, iso)


if __name__ == "__main__":
    main()
