#!/bin/bash
# 用法：redo.sh <config key> <成品檔名(不含.mp4)>
cd "/Users/lien/Downloads/Liam AI agent"; O="成品/可麗露"; k="$1"; n="$2"
mkdir -p "$O/舊版備份"; mv "$O/無配樂母帶/$n.mp4" "$O/舊版備份/${n}_無配樂母帶_$(date +%H%M).mp4"; mv "$O/$n.mp4" "$O/舊版備份/${n}_$(date +%H%M).mp4"
python3 tools/dessert_longform.py build "dessert/可麗露_${k}_config.json" 2>&1 | grep cues
cp "$O/$n.mp4" "$O/build原檔/$n.mp4"
python3 dessert/可麗露_工作檔/make_overlays.py >/dev/null; python3 tools/overlay_fx.py "dessert/可麗露_工作檔/overlay_${k}.json" 2>&1 | tail -1 && mv "$O/${n}_疊圖.mp4" "$O/$n.mp4"
python3 dessert/片尾.py append "$O/$n.mp4" | tail -1; python3 dessert/加配樂.py "$O/$n.mp4" light | tail -1
