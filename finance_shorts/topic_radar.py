"""金錢怪物選題雷達：查某個題目最近 30 天在 Reddit／YouTube／Hacker News／Polymarket 的討論。

引擎是 mvanhorn/last30days-skill（MIT），固定版本放在 ~/tools/last30days/。
只用免費來源、不讀瀏覽器 cookie、不帶任何金鑰。結果是「網友在講什麼」，不是事實，
只當選題線索，內容仍要走 verify.py 的雙來源查證。

用法：
    python3 finance_shorts/topic_radar.py "buy now pay later" \
        --also "Klarna Affirm delinquencies" --subs personalfinance,economy
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ENGINE = Path.home() / "tools/last30days/scripts/last30days.py"
OUT_DIR = Path.home() / "tools/last30days/out"
SOURCES = ["reddit", "youtube", "hackernews", "polymarket"]
STRIP_ENV = ("GH_TOKEN", "GITHUB_TOKEN", "OPENAI_API_KEY", "GEMINI_API_KEY")


def build_plan(topic, also):
    subqueries = [
        {
            "label": "primary",
            "search_query": topic,
            "ranking_query": f"What are people saying about {topic}?",
            "sources": SOURCES,
            "weight": 1.0,
        }
    ]
    for i, query in enumerate(also, 1):
        subqueries.append(
            {
                "label": f"angle{i}",
                "search_query": query,
                "ranking_query": f"What are people saying about {query}?",
                "sources": ["reddit", "youtube", "hackernews"],
                "weight": 0.7,
            }
        )
    return {
        "intent": "breaking_news",
        "freshness_mode": "strict_recent",
        "cluster_mode": "story",
        "subqueries": subqueries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("topic", help="英文關鍵字，不要放年份、月份或 news 這類字")
    parser.add_argument(
        "--also", action="append", default=[], help="額外角度，可重複，最多 3 個"
    )
    parser.add_argument("--subs", help="指定 subreddit，逗號分隔、不加 r/")
    args = parser.parse_args()

    if not ENGINE.exists():
        sys.exit(f"找不到引擎：{ENGINE}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", args.topic.lower()).strip("-")[:50]
    out = OUT_DIR / f"{date.today():%Y%m%d}_{slug}.md"

    cmd = [
        "uv",
        "run",
        "--python",
        "3.12",
        "--no-project",
        str(ENGINE),
        args.topic,
        "--no-browser-cookies",
        "--search",
        ",".join(SOURCES),
        "--emit",
        "md",
        "--output",
        str(out),
        "--plan",
        "-",
    ]
    if args.subs:
        cmd += ["--subreddits", args.subs]

    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    plan = json.dumps(build_plan(args.topic, args.also[:3]))
    result = subprocess.run(
        cmd, input=plan, text=True, env=env, stdout=subprocess.DEVNULL
    )
    if result.returncode != 0 or not out.exists():
        sys.exit("雷達沒有產出結果，看上面的錯誤訊息")
    print(f"結果：{out}")


if __name__ == "__main__":
    main()
