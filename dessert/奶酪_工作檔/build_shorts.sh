#!/bin/bash
# 奶酪短片：渲染 → 備份無片尾母帶 → 接片尾 → 加配樂（light，GAP 18）
cd "/Users/lien/Downloads/Liam AI agent"
OUT=成品/奶酪
mkdir -p "$OUT/無片尾母帶"
for c in dessert/奶酪_短*_config.json; do
  subj=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['subject'])" "$c")
  echo "=== $subj"
  taskpolicy -b python3 tools/dessert_longform.py build "$c" 2>&1 | tail -1
  f="$OUT/$subj.mp4"
  [ -f "$f" ] || { echo "❌ 沒有產出 $f"; continue; }
  cp -p "$f" "$OUT/無片尾母帶/"
  python3 dessert/片尾.py append "$f" 2>&1 | tail -1
  taskpolicy -b python3 dessert/加配樂.py "$f" light 18 2>&1 | tail -1
done
echo ALLDONE
