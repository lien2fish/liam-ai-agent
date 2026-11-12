# -*- coding: utf-8 -*-
"""把盤後日報（Markdown）發成 Notion「📊 台股盤後日報」底下的一頁，一天一頁。

⚠️ 不放在舊的「每日市場日報」頁面底下——舊程式每天會刪光那頁的子區塊。
寫完會讀回來比對區塊數與表格列數，對不上就丟例外（run 變紅）。
"""
import json
import os
import re
import time
import urllib.request
from pathlib import Path

API = "https://api.notion.com/v1"
VER = "2022-06-28"
CONFIG = Path(__file__).resolve().parent / "market_config.json"


def _token():
    t = os.environ.get("NOTION_TOKEN", "")
    if not t:
        p = Path(__file__).resolve().parent.parent / "config" / ".notion_token"
        t = p.read_text().strip() if p.exists() else ""
    return t


def req(method, path, body=None):
    for i in range(4):
        try:
            r = urllib.request.Request(
                f"{API}/{path}",
                data=json.dumps(body).encode() if body else None,
                headers={
                    "Authorization": f"Bearer {_token()}",
                    "Notion-Version": VER,
                    "Content-Type": "application/json",
                },
                method=method,
            )
            with urllib.request.urlopen(r, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and i < 3:
                time.sleep(2 * (i + 1))
                continue
            raise RuntimeError(f"Notion {method} {path} → {e.code} {e.read()[:300]}")


def rt(text):
    out = []
    for i, part in enumerate(re.split(r"\*\*", text)):
        if part:
            out.append(
                {
                    "type": "text",
                    "text": {"content": part[:2000]},
                    "annotations": {"bold": i % 2 == 1},
                }
            )
    return out or [{"type": "text", "text": {"content": ""}}]


def md_to_blocks(md):
    blocks, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("# "):
            pass  # 標題已是頁名
        elif ln.startswith("## "):
            blocks.append({"type": "heading_2", "heading_2": {"rich_text": rt(ln[3:])}})
        elif ln.startswith("> "):
            blocks.append({"type": "quote", "quote": {"rich_text": rt(ln[2:])}})
        elif ln.startswith("- "):
            blocks.append(
                {
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": rt(ln[2:])},
                }
            )
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s\-:|]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            w = len(rows[0])
            blocks.append(
                {
                    "type": "table",
                    "table": {
                        "table_width": w,
                        "has_column_header": True,
                        "has_row_header": False,
                        "children": [
                            {
                                "type": "table_row",
                                "table_row": {
                                    "cells": [rt(c) for c in (r + [""] * w)[:w]]
                                },
                            }
                            for r in rows
                        ],
                    },
                }
            )
            continue
        elif ln.strip():
            blocks.append({"type": "paragraph", "paragraph": {"rich_text": rt(ln)}})
        i += 1
    return blocks


def container_id():
    cfg = json.loads(CONFIG.read_text())
    if cfg.get("evening_notion_parent"):
        return cfg["evening_notion_parent"]
    page = req(
        "POST",
        "pages",
        {
            "parent": {"page_id": cfg["notion_parent_page_id"]},
            "properties": {
                "title": {"title": [{"text": {"content": "📊 台股盤後日報"}}]}
            },
        },
    )
    cfg["evening_notion_parent"] = page["id"]
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    return page["id"]


def publish(title, md):
    blocks = md_to_blocks(md)
    page = req(
        "POST",
        "pages",
        {
            "parent": {"page_id": container_id()},
            "properties": {"title": {"title": [{"text": {"content": title}}]}},
        },
    )
    pid = page["id"]
    try:
        _fill_and_verify(pid, blocks)
    except Exception:
        req("PATCH", f"pages/{pid}", {"archived": True})  # 不留半成品頁，重跑時重新建
        raise
    print(f"✅ Notion 已發布並讀回比對：{len(blocks)} 個區塊 {page.get('url')}")
    return page.get("url")


def _fill_and_verify(pid, blocks):
    for k in range(0, len(blocks), 40):
        req("PATCH", f"blocks/{pid}/children", {"children": blocks[k : k + 40]})
        time.sleep(0.4)

    got, cursor = [], None
    while True:
        r = req(
            "GET",
            f"blocks/{pid}/children?page_size=100"
            + (f"&start_cursor={cursor}" if cursor else ""),
        )
        got += r["results"]
        if not r.get("has_more"):
            break
        cursor = r["next_cursor"]
    if len(got) != len(blocks):
        raise RuntimeError(
            f"Notion 區塊數不符：送出 {len(blocks)}、讀回 {len(got)}（{pid}）"
        )
    for sent, back in zip(blocks, got):
        if sent["type"] == "table":
            rows = req("GET", f"blocks/{back['id']}/children?page_size=100")["results"]
            if len(rows) != len(sent["table"]["children"]):
                raise RuntimeError(f"Notion 表格列數不符（{pid}）")
            first = "".join(t["plain_text"] for t in rows[-1]["table_row"]["cells"][0])
            want = "".join(
                t["text"]["content"]
                for t in sent["table"]["children"][-1]["table_row"]["cells"][0]
            )
            if first != want:
                raise RuntimeError(f"Notion 表格內容不符：{first!r} ≠ {want!r}")
