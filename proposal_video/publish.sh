#!/bin/bash
# 把四支最新的渲染成果複製到「成品/AI導入包提案影片/」，檔名改成提案現場找得到的樣子。
set -euo pipefail
cd "$(dirname "$0")"
OUT="../成品/AI導入包提案影片"
mkdir -p "$OUT"

declare -a MAP=(
  "full-wide:完整版_橫式_投影用_2分45秒.mp4"
  "full-tall:完整版_直式_手機用_2分45秒.mp4"
  "short-wide:精華版_橫式_投影用_90秒.mp4"
  "short-tall:精華版_直式_手機用_90秒.mp4"
)

for m in "${MAP[@]}"; do
  p="${m%%:*}"; name="${m#*:}"
  src=$(ls -t "$p"/renders/*.mp4 2>/dev/null | head -1) || { echo "  ⚠️  $p 還沒渲染"; continue; }
  cp "$src" "$OUT/$name"
  printf "  → %-38s %s\n" "$name" "$(du -h "$OUT/$name" | cut -f1)"
done
echo "全部在：$(cd "$OUT" && pwd)"
