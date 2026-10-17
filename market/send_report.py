#!/usr/bin/env python3
"""把當天的財金日報（Markdown 轉 HTML 當內文）連同 PDF 寄給自己。"""

import html
import os
import re
import smtplib
import ssl
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

ADDR = "lien2fish@gmail.com"


def inline(text):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(text, quote=False))


def md_to_html(md):
    out, table = [], []

    def flush():
        if not table:
            return
        rows = [r for r in table if not re.match(r"^\|[\s\-:|]+\|$", r)]
        cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
        head = "".join(
            f'<th style="padding:6px 8px;text-align:left">{inline(c)}</th>' for c in cells[0]
        )
        body = "".join(
            "<tr%s>%s</tr>"
            % (
                ' style="background:#EEF4FA"' if i % 2 else "",
                "".join(
                    f'<td style="padding:6px 8px;border-top:1px solid #ddd;vertical-align:top">{inline(c)}</td>'
                    for c in r
                ),
            )
            for i, r in enumerate(cells[1:])
        )
        out.append(
            '<table style="border-collapse:collapse;width:100%;font-size:13px;margin:6px 0 14px">'
            f'<tr style="background:#1F4E79;color:#fff">{head}</tr>{body}</table>'
        )
        table.clear()

    for line in md.splitlines():
        if line.startswith("|"):
            table.append(line.strip())
            continue
        flush()
        if line.startswith("# "):
            out.append(f'<h1 style="font-size:20px;color:#1F4E79">{inline(line[2:])}</h1>')
        elif line.startswith("## "):
            out.append(
                f'<h2 style="font-size:16px;color:#1F4E79;border-bottom:2px solid #1F4E79;'
                f'padding-bottom:3px;margin-top:22px">{inline(line[3:])}</h2>'
            )
        elif line.startswith("### "):
            out.append(f'<h3 style="font-size:14px;margin:12px 0 4px">{inline(line[4:])}</h3>')
        elif line.startswith(">"):
            out.append(f'<p style="color:#888;font-size:12px">{inline(line.lstrip("> "))}</p>')
        elif line.startswith("- "):
            out.append(f'<p style="margin:3px 0 3px 12px">• {inline(line[2:])}</p>')
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
    flush()
    return (
        '<div style="font-family:-apple-system,\'PingFang TC\',sans-serif;max-width:760px;'
        'line-height:1.6;color:#222">' + "".join(out) + "</div>"
    )


def main(md_path, pdf_path):
    md = Path(md_path).read_text(encoding="utf-8")
    date = re.search(r"\d{4}-\d{2}-\d{2}", Path(md_path).name).group(0)
    m = re.search(r"\*\*今日重點：(.+?)\*\*", md)
    subject = f"財金日報 {date}" + (f"｜{m.group(1)}" if m else "")

    pw = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not pw:
        sys.exit("❌ 缺 GMAIL_APP_PASSWORD，無法寄信")

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = formataddr(("Liam AI Agent", ADDR))
    msg["To"] = ADDR
    msg.attach(MIMEText(md_to_html(md), "html", "utf-8"))
    part = MIMEApplication(Path(pdf_path).read_bytes(), _subtype="pdf")
    part.add_header("Content-Disposition", "attachment", filename=Path(pdf_path).name)
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
        s.login(ADDR, pw)
        s.send_message(msg)
    print(f"✅ 已寄出：{subject}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
