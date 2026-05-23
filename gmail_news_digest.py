#!/usr/bin/env python3
"""
Gmail 新聞電子報摘要
讀取中時新聞網、經濟日報的最新電子報，整理標題與重點，讀後移進垃圾桶。
輸出：Markdown 格式，可直接貼入早報或單獨使用。
"""
import json, os, re, base64, urllib.request, urllib.parse, time
from datetime import datetime

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "今日新聞摘要.md"
)

NEWS_SOURCES = [
    {
        "name": "中時新聞網",
        "query": "from:ctepaper@infotimes.com.tw is:unread",
        "parser": "chinatimes",
    },
    {
        "name": "經濟日報",
        "query": "from:mailman@mx.udnpaper.com is:unread",
        "parser": "udnmoney",
    },
]


def get_token():
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        token_path = os.path.expanduser("~/.config/gmail-cleanup-token.json")
        with open(token_path) as f:
            d = json.load(f)
        client_id = d["client_id"]
        client_secret = d["client_secret"]
        refresh_token = d["refresh_token"]

    payload = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode()
    with urllib.request.urlopen(
        urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
    ) as r:
        return json.loads(r.read())["access_token"]


def api(token, path, method="GET", body=None):
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/{path}"
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(
        urllib.request.Request(url, data=data, headers=headers, method=method)
    ) as r:
        return json.loads(r.read())


def get_msg_ids(token, query, max_results=5):
    result = api(
        token,
        f"messages?{urllib.parse.urlencode({'q': query, 'maxResults': max_results})}",
    )
    return [m["id"] for m in result.get("messages", [])]


def fetch_body(token, msg_id):
    msg = api(token, f"messages/{msg_id}?format=full")
    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}

    def extract(parts):
        for p in parts:
            mime = p.get("mimeType", "")
            data = p.get("body", {}).get("data", "")
            if data:
                raw = base64.urlsafe_b64decode(data + "==").decode(
                    "utf-8", errors="ignore"
                )
                if mime == "text/plain":
                    return raw, "text"
                if mime == "text/html":
                    return raw, "html"
            if "parts" in p:
                r = extract(p["parts"])
                if r:
                    return r
        return None, None

    payload_parts = msg["payload"].get("parts") or [msg["payload"]]
    # 優先找 text/plain，沒有就用 html
    plain_result = None
    html_result = None
    for p in payload_parts:
        content, ctype = extract([p])
        if content:
            if ctype == "text" and plain_result is None:
                plain_result = content
            elif ctype == "html" and html_result is None:
                html_result = content

    # 回傳 html（供 chinatimes parser 使用），is_plain 標記是否 plain-only
    if html_result:
        return headers, html_result, False
    return headers, plain_result or "", True


def strip_html(html):
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<p[^>]*>", "\n", text)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&[a-z]{2,6};", "", text)
    return text


def clean_lines(text):
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        # 跳過 URL、空行、CSS、只有符號的行
        if not line or line.startswith("http") or "{" in line or "}" in line:
            continue
        if re.match(r"^[=\-\s\.\,\(\)]+$", line):
            continue
        if len(line) < 4:
            continue
        lines.append(line)
    return lines


def parse_chinatimes(html, is_plain):
    """中時：<a> 標籤是標題，class=article-intro 是描述，直接配對"""
    if is_plain:
        # plain text fallback
        lines = clean_lines(html)
        articles = []
        for i, line in enumerate(lines):
            if "……" in line and len(line) > 6:
                # 找前面的標題
                for j in range(max(0, i - 3), i):
                    t = lines[j]
                    if 8 <= len(t) <= 80 and "……" not in t:
                        articles.append((t, line))
                        break
        return articles

    # 從 HTML 直接抽取
    titles = re.findall(r"<a[^>]*>\s*([^\s<][^<]{7,79}[^\s<])\s*</a>", html)
    descs = re.findall(r'class="[^"]*article-intro[^"]*"[^>]*>\s*([^<]{6,})\s*<', html)
    skip = {"閱讀更多", "取消訂閱", "大家都在看", "中時社論", "旺旺集團"}

    titles = [t.strip() for t in titles if t.strip() and not any(w in t for w in skip)]
    descs = [d.strip() for d in descs if d.strip()]

    articles = []
    for i, title in enumerate(titles):
        desc = descs[i] if i < len(descs) else ""
        articles.append((title, desc))
    return articles


def parse_udnmoney(text, is_plain):
    """經濟日報：text-based，標題行 + 下一段描述"""
    lines = clean_lines(text)
    articles = []
    skip = {
        "取消訂閱",
        "下載APP",
        "隱私權聲明",
        "服務條款",
        "會員中心",
        "經濟日報",
        "著作權",
        "此郵件",
    }
    i = 0
    while i < len(lines):
        line = lines[i]
        # 跳過日期行、Footer、短標籤
        if (
            len(line) < 8
            or any(w in line for w in skip)
            or re.match(r"^\d{4}年\d+月\d+日", line)
            or re.match(r"^[A-Z\s]+$", line)
        ):
            i += 1
            continue
        # 描述：下一行較長，含句點或逗號
        if i + 1 < len(lines):
            nxt = lines[i + 1]
            if (
                len(nxt) > len(line)
                and any(c in nxt for c in ["。", "，", "……"])
                and not any(w in nxt for w in skip)
            ):
                articles.append((line, nxt))
                i += 2
                continue
        i += 1
    return articles


def trash_msg(token, msg_id):
    api(token, f"messages/{msg_id}/trash", method="POST")


def format_digest(source_name, articles, date_str):
    if not articles:
        return f"### {source_name}\n> 今日無新文章\n"
    lines = [f"### {source_name}（{date_str}）"]
    for i, (title, desc) in enumerate(articles, 1):
        lines.append(f"\n**{i}. {title}**")
        lines.append(f"> {desc}")
    return "\n".join(lines)


def main():
    token = get_token()
    today = datetime.now().strftime("%Y-%m-%d")
    output_parts = [f"# 今日新聞電子報摘要 {today}\n"]

    for src in NEWS_SOURCES:
        ids = get_msg_ids(token, src["query"], max_results=3)
        if not ids:
            output_parts.append(f"### {src['name']}\n> 今日無新電子報\n")
            continue

        all_articles = []
        for msg_id in ids:
            headers, body, is_plain = fetch_body(token, msg_id)
            date_hdr = headers.get("Date", "")[:16]

            if src["parser"] == "chinatimes":
                articles = parse_chinatimes(body, is_plain)
            else:
                text = strip_html(body) if not is_plain else body
                articles = parse_udnmoney(text, is_plain)

            # 去重（同標題不重複）
            seen = {t for t, _ in all_articles}
            for a in articles:
                if a[0] not in seen:
                    all_articles.append(a)
                    seen.add(a[0])

            # 讀完移垃圾桶
            trash_msg(token, msg_id)
            time.sleep(0.2)

        output_parts.append(format_digest(src["name"], all_articles[:8], today))
        output_parts.append("")

    result = "\n".join(output_parts)
    print(result)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(result)
    return result


if __name__ == "__main__":
    main()
