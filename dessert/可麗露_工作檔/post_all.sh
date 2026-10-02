#!/bin/bash
# 每支：疊圖 → 接片尾 → 加配樂。build 原檔備份在 成品/可麗露/build原檔/
cd "/Users/lien/Downloads/Liam AI agent"
OUT="成品/可麗露"; mkdir -p "$OUT/build原檔"
for o in dessert/可麗露_工作檔/overlay_*.json; do
  v=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['video'])" "$o")
  ov="${v%.mp4}_疊圖.mp4"; base=$(basename "$v")
  echo "=== $base"
  [ -f "$OUT/build原檔/$base" ] || cp "$v" "$OUT/build原檔/$base"
  python3 tools/overlay_fx.py "$o" 2>&1 | tail -2 || exit 1
  mv "$ov" "$v"
  python3 dessert/片尾.py append "$v" 2>&1 | tail -1
  python3 dessert/加配樂.py "$v" light 2>&1 | tail -1
done
echo ALLDONE
