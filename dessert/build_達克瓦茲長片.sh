#!/bin/bash
# 達克瓦茲長片：一條龍。四步都要跑完才算完成。
#
#   1  產 config（段落與字幕都在 make_達克瓦茲長片.py 裡）
#   2  build 正片（含 9:16 封面卡壓進開頭 1 秒）
#   3  接上成品照片尾
#   4  另出 16:9 縮圖——直式長片在 YouTube 會掉進 16:9 版位
#
# ⚠️ 4703 走 素材/IMG_4703_遮擋.MOV（配方紙追蹤遮擋版）。
#    遮擋區間在 dessert/遮擋/，要重出母帶看 tools/paper_mask.py。
set -eu
cd "$(dirname "$0")/.."
OUT="成品/達克瓦茲"
NAME="裂掉是火力不夠不是下火太高"

python3 dessert/make_達克瓦茲長片.py
python3 tools/dessert_longform.py build dessert/達克瓦茲_長片_config.json
python3 dessert/成品照.py

# 片尾 concat：兩段編碼參數一致，畫面 copy、只重編音訊
cat > /tmp/dq_concat.txt <<EOF
file '$PWD/$OUT/$NAME.mp4'
file '$PWD/$OUT/成品照片尾.mp4'
EOF
ffmpeg -v error -f concat -safe 0 -i /tmp/dq_concat.txt \
  -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 1 \
  -movflags +faststart "$OUT/${NAME}_完整.mp4" -y
mv "$OUT/${NAME}_完整.mp4" "$OUT/$NAME.mp4"

python3 - <<'PY'
import importlib.util, json, os
spec = importlib.util.spec_from_file_location("dl", "tools/dessert_longform.py")
dl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dl)
cfg = json.load(open("dessert/達克瓦茲_長片_config.json", encoding="utf-8"))
cov = cfg["cover"]
out = os.path.join(cfg["out_dir"], cfg["subject"] + "_封面_16x9.jpg")
dl.make_cover_169(cfg["videos"][cov["video_index"]], cov["time"],
                  cov["main"], cov["sub"], out)
print("✅", out)
PY

ls -la "$OUT/$NAME".* "$OUT"/成品照*
