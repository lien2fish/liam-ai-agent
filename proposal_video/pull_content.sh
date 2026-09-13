#!/bin/bash
# 從私人 repo 取回文案。
#
# script.md（旁白）與 scenes.json（字卡）是對客戶提案的銷售話術，
# 不進公開 repo——2026-09-13 從公開庫撤下並改寫歷史，見 README。
# 換機或重新 clone 後跑這支，否則 build.py／gen_voice.py 會找不到檔案。
set -euo pipefail
cd "$(dirname "$0")"
W="${WORKSPACE_DIR:-$HOME/liam-workspace}/proposal"
[ -d "$W" ] || { echo "❌ 找不到 $W——先 clone 或 pull liam-workspace"; exit 1; }
mkdir -p content
cp "$W/script.md" "$W/scenes.json" content/
echo "文案已取回 content/（$(wc -l < content/script.md | tr -d ' ') 行腳本）"
