import sys, re, os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansTC.ttf")
pdfmetrics.registerFont(TTFont("NotoTC", FONT_PATH))
pdfmetrics.registerFont(TTFont("NotoTC-Bold", FONT_PATH))

base = ParagraphStyle("base", fontName="NotoTC", fontSize=10, leading=15)
h1 = ParagraphStyle(
    "h1", fontName="NotoTC-Bold", fontSize=18, leading=24, spaceAfter=10
)
h2 = ParagraphStyle(
    "h2", fontName="NotoTC-Bold", fontSize=14, leading=20, spaceAfter=8, spaceBefore=10
)
quote = ParagraphStyle(
    "quote",
    fontName="NotoTC",
    fontSize=9,
    leading=14,
    textColor=colors.grey,
    leftIndent=10,
)
bullet = ParagraphStyle(
    "bullet", fontName="NotoTC", fontSize=10, leading=15, leftIndent=14, bulletIndent=4
)


def inline(text):
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return text


def md_to_story(md_path):
    with open(md_path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    story = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue

        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), h1))
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), h2))
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), h2))
        elif line.startswith(">"):
            story.append(Paragraph(inline(line.lstrip("> ").strip()), quote))
        elif line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            i -= 1
            rows = []
            for tl in table_lines:
                if re.match(r"^\|[\s\-:|]+\|$", tl):
                    continue
                cells = [c.strip() for c in tl.strip("|").split("|")]
                rows.append([Paragraph(inline(c), base) for c in cells])
            if rows:
                tbl = Table(rows, hAlign="LEFT")
                tbl.setStyle(
                    TableStyle(
                        [
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.white, colors.HexColor("#DEEAF1")],
                            ),
                        ]
                    )
                )
                story.append(tbl)
                story.append(Spacer(1, 6))
        elif line.startswith("- "):
            story.append(Paragraph("• " + inline(line[2:]), bullet))
        else:
            story.append(Paragraph(inline(line), base))
        i += 1

    return story


def build_pdf(pdf_path, md_paths):
    story = []
    for idx, md_path in enumerate(md_paths):
        if idx > 0:
            story.append(PageBreak())
        story.extend(md_to_story(md_path))

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )
    doc.build(story)
    print(f"OK: {pdf_path}")


if __name__ == "__main__":
    build_pdf(sys.argv[1], sys.argv[2:])
