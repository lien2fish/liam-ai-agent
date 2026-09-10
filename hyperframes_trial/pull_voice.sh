#!/bin/bash
# 從私人 repo 取回旁白音檔。
#
# 旁白＝Lien 的克隆聲音，屬個資敏感資料，不進公開 repo（見 .gitignore 註解）。
# 各專案的 audio/ 已從版控移除，換機或清空後用這支取回，否則渲染會沒有聲音。
set -euo pipefail
cd "$(dirname "$0")"
W="${WORKSPACE_DIR:-$HOME/liam-workspace}/assets/voice/hyperframes"
[ -d "$W" ] || { echo "❌ 找不到 $W——先 clone 或 pull liam-workspace"; exit 1; }

for p in */; do
  p="${p%/}"
  [ -f "$p/hyperframes.json" ] || continue
  [ -d "$W/$p" ] || { echo "  ⚠️  $p 私人 repo 裡沒有音檔，跳過"; continue; }
  mkdir -p "$p/audio"
  cp "$W/$p"/s*.mp3 "$p/audio/"
  echo "  → ${p}（$(ls -1 "$p/audio"/s*.mp3 | wc -l | tr -d ' ') 段）"
done
echo "旁白已取回"
