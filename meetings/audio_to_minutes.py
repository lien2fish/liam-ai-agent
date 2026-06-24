"""
會議錄音轉會議記錄 PDF（詳細版 + 簡化版）

用法：
    python3 meetings/audio_to_minutes.py "<音檔路徑>" "<會議名稱>"

例：
    python3 meetings/audio_to_minutes.py \
        "/Users/lien/Desktop/惜食第六屆會議1.m4a" \
        "惜食台灣行動協會 第六屆會議"

輸出：
    ~/Desktop/{會議名稱}_會議記錄.pdf       （詳細版）
    ~/Desktop/{會議名稱}_會議記錄_簡化版.pdf （簡化版）
"""

import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_PATH = os.path.join(REPO_ROOT, "config", ".gemini_key")
DESKTOP = os.path.expanduser("~/Desktop")
GEMINI_BASE = "https://generativelanguage.googleapis.com"
MODEL = "gemini-2.5-flash"

NAVY = colors.HexColor("#1F4E79")
LIGHT_BLUE = colors.HexColor("#DEEAF1")
GREY = colors.HexColor("#444444")

DETAILED_PROMPT = """你是一位專業的會議記錄整理人員。請聆聽附帶的會議錄音檔（繁體中文），完整轉錄並整理成正式會議記錄。

請用繁體中文輸出，依照以下 JSON 結構回覆：

{
  "meeting_title": "會議名稱（若錄音中有提及，否則用提供的會議名稱）",
  "meeting_date": "會議日期（若錄音中有提及具體日期則填寫，否則為空字串）",
  "agenda_items": [
    {
      "topic": "議題名稱",
      "discussion_summary": "該議題的討論內容摘要，需完整、具體，包含關鍵數字、提案內容、不同與會者的意見",
      "decisions": ["該議題達成的決議或共識，若無則為空陣列"]
    }
  ],
  "action_items": [
    {
      "task": "待辦事項內容",
      "owner": "負責人（若錄音中明確指派，否則寫「未指定」）",
      "due": "期限（若有提及，否則為空字串）"
    }
  ],
  "overall_summary": "整場會議的整體摘要，3-5句話"
}

注意：
- discussion_summary 務必詳細完整，不要只寫一句話草率帶過，要能讓沒參加會議的人讀懂全部討論脈絡
- 依照會議實際討論順序列出 agenda_items，議題數量不限，有多少討論主題就列多少
- 如果錄音中有金額、數字、人名、地點，務必精確記錄
- 若錄音中出現大量人名清單（例如：捐款人名單逐一唸出、簽到名冊、志工名單），不要逐字全部抄錄，只需註明「共XX人／包含XX等」並列出前幾位代表性人名即可，避免輸出過長或重複卡住
"""

SIMPLIFY_PROMPT_TEMPLATE = """以下是一份會議記錄的 JSON，內容偏冗長。
請幫我把每個 agenda_items 的 discussion_summary 濃縮整理成 3-5 條精簡要點（key_points），
每條限制在一句話內，但務必保留原文中的關鍵數字、金額、人名、地點、決議內容，不要遺漏重要資訊，只是把敘述文字精簡化、條列化。

overall_summary 也請精簡為 2-3 句話。
decisions 和 action_items 維持原內容不變，照抄即可。
meeting_title、meeting_date 也照抄不變。

原始內容：
{minutes_json}

請用以下 JSON 結構回覆：
{{
  "meeting_title": "...",
  "meeting_date": "...",
  "overall_summary": "...",
  "agenda_items": [
    {{"topic": "...", "key_points": ["...", "..."], "decisions": ["..."]}}
  ],
  "action_items": [
    {{"task": "...", "owner": "...", "due": "..."}}
  ]
}}
"""


def load_api_key():
    key = os.environ.get("GEMINI_KEY", "")
    if key:
        return key
    with open(KEY_PATH) as f:
        return f.read().strip()


def upload_file(path, api_key):
    mime_type = mimetypes.guess_type(path)[0] or "audio/mp4"
    size = os.path.getsize(path)
    start_req = urllib.request.Request(
        f"{GEMINI_BASE}/upload/v1beta/files?key={api_key}",
        method="POST",
        headers={
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(size),
            "X-Goog-Upload-Header-Content-Type": mime_type,
            "Content-Type": "application/json",
        },
        data=json.dumps({"file": {"display_name": os.path.basename(path)}}).encode(),
    )
    with urllib.request.urlopen(start_req) as resp:
        upload_url = resp.headers.get("X-Goog-Upload-URL")

    with open(path, "rb") as f:
        data = f.read()

    upload_req = urllib.request.Request(
        upload_url,
        method="POST",
        headers={
            "Content-Length": str(size),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        },
        data=data,
    )
    with urllib.request.urlopen(upload_req) as resp:
        return json.loads(resp.read().decode())["file"]


def wait_active(file_name, api_key):
    url = f"{GEMINI_BASE}/v1beta/{file_name}?key={api_key}"
    while True:
        with urllib.request.urlopen(url) as resp:
            info = json.loads(resp.read().decode())
        if info["state"] == "ACTIVE":
            return info
        if info["state"] == "FAILED":
            raise RuntimeError(f"檔案處理失敗: {info}")
        time.sleep(5)


def call_gemini(body, api_key, retries=3):
    req = urllib.request.Request(
        f"{GEMINI_BASE}/v1beta/models/{MODEL}:generateContent?key={api_key}",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps(body).encode(),
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                result = json.loads(resp.read().decode())
            return json.loads(result["candidates"][0]["content"]["parts"][0]["text"])
        except urllib.error.HTTPError as e:
            if e.code == 503 and attempt < retries - 1:
                time.sleep(8)
                continue
            print(e.read().decode(), file=sys.stderr)
            raise


def transcribe(file_info, meeting_name, api_key):
    body = {
        "contents": [
            {
                "parts": [
                    {
                        "file_data": {
                            "mime_type": file_info["mimeType"],
                            "file_uri": file_info["uri"],
                        }
                    },
                    {"text": DETAILED_PROMPT + f"\n\n會議名稱參考：{meeting_name}"},
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 65536,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    return call_gemini(body, api_key)


def simplify(minutes, api_key):
    prompt = SIMPLIFY_PROMPT_TEMPLATE.format(
        minutes_json=json.dumps(minutes, ensure_ascii=False)
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 65536,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    return call_gemini(body, api_key)


def register_fonts():
    pdfmetrics.registerFont(
        TTFont("PingFangTC", "/System/Library/Fonts/STHeiti Light.ttc", subfontIndex=0)
    )
    pdfmetrics.registerFont(
        TTFont(
            "PingFangTC-Medium",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            subfontIndex=0,
        )
    )
    pdfmetrics.registerFont(
        TTFont(
            "PingFangTC-Semibold",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            subfontIndex=0,
        )
    )


def build_styles():
    return {
        "title": ParagraphStyle(
            "title",
            fontName="PingFangTC-Semibold",
            fontSize=22,
            leading=28,
            textColor=NAVY,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName="PingFangTC",
            fontSize=11,
            leading=16,
            textColor=GREY,
            spaceAfter=14,
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName="PingFangTC-Semibold",
            fontSize=14,
            leading=20,
            textColor=NAVY,
            spaceBefore=16,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3",
            fontName="PingFangTC-Medium",
            fontSize=12,
            leading=17,
            textColor=NAVY,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="PingFangTC",
            fontSize=10.5,
            leading=17,
            textColor=colors.black,
            spaceAfter=6,
            alignment=4,
        ),
        "point": ParagraphStyle(
            "point",
            fontName="PingFangTC",
            fontSize=10.5,
            leading=16,
            textColor=colors.black,
            leftIndent=14,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontName="PingFangTC",
            fontSize=10.5,
            leading=16,
            textColor=NAVY,
            leftIndent=12,
            spaceAfter=3,
        ),
        "summary": ParagraphStyle(
            "summary",
            fontName="PingFangTC",
            fontSize=10.5,
            leading=17,
            textColor=colors.black,
            spaceAfter=6,
            alignment=4,
            backColor=LIGHT_BLUE,
            borderPadding=10,
        ),
    }


def action_items_table(action_items, styles):
    cell_style = ParagraphStyle("cell", fontName="PingFangTC", fontSize=9.5, leading=14)
    header_style = ParagraphStyle(
        "cellh",
        fontName="PingFangTC-Semibold",
        fontSize=10,
        leading=14,
        textColor=colors.white,
    )
    wrapped = [[Paragraph(c, header_style) for c in ["事項", "負責人", "期限"]]]
    for ai in action_items:
        wrapped.append(
            [
                Paragraph(ai.get("task", ""), cell_style),
                Paragraph(ai.get("owner", "") or "未指定", cell_style),
                Paragraph(ai.get("due", "") or "—", cell_style),
            ]
        )
    t = Table(wrapped, colWidths=[105 * mm, 35 * mm, 30 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#AAAAAA")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return t


def build_pdf(data, out_path, title_suffix, detail_key):
    styles = build_styles()
    story = [Paragraph(data["meeting_title"] + title_suffix, styles["title"])]

    meta_bits = []
    if data.get("meeting_date"):
        meta_bits.append(f"日期：{data['meeting_date']}")
    if data.get("attendees"):
        meta_bits.append("與會人員：" + "、".join(data["attendees"]))
    if meta_bits:
        story.append(Paragraph("　".join(meta_bits), styles["subtitle"]))

    story.append(HRFlowable(width="100%", thickness=1.2, color=NAVY, spaceAfter=12))
    story.append(Paragraph("會議摘要", styles["h2"]))
    story.append(Paragraph(data["overall_summary"], styles["summary"]))
    story.append(Paragraph("議程討論紀錄", styles["h2"]))

    for i, item in enumerate(data["agenda_items"], 1):
        story.append(Paragraph(f"{i}. {item['topic']}", styles["h3"]))
        if detail_key == "discussion_summary":
            story.append(Paragraph(item["discussion_summary"], styles["body"]))
        else:
            for p in item.get("key_points", []):
                story.append(Paragraph(f"• {p}", styles["point"]))
        for d in item.get("decisions", []):
            story.append(Paragraph(f"★ 決議：{d}", styles["bullet"]))

    if data.get("action_items"):
        story.append(Paragraph("待辦事項", styles["h2"]))
        story.append(action_items_table(data["action_items"], styles))

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=data["meeting_title"] + title_suffix,
    )
    doc.build(story)
    print("已輸出:", out_path)


def main():
    if len(sys.argv) < 3:
        print(
            "用法: python3 audio_to_minutes.py <音檔路徑> <會議名稱>", file=sys.stderr
        )
        sys.exit(1)

    audio_path, meeting_name = sys.argv[1], sys.argv[2]
    api_key = load_api_key()

    print("上傳音檔...", file=sys.stderr)
    file_info = upload_file(audio_path, api_key)
    print("等待處理完成...", file=sys.stderr)
    file_info = wait_active(file_info["name"], api_key)

    print("轉錄＋整理詳細版...", file=sys.stderr)
    detailed = transcribe(file_info, meeting_name, api_key)

    print("產出簡化版...", file=sys.stderr)
    simplified = simplify(detailed, api_key)

    register_fonts()
    build_pdf(
        detailed,
        os.path.join(DESKTOP, f"{meeting_name}_會議記錄.pdf"),
        "",
        "discussion_summary",
    )
    build_pdf(
        simplified,
        os.path.join(DESKTOP, f"{meeting_name}_會議記錄_簡化版.pdf"),
        "（簡化版）",
        "key_points",
    )


if __name__ == "__main__":
    main()
