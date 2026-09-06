#!/bin/bash
# 把共用檔複製進各專案。
#
# 為什麼要複製而不是共用路徑：hyperframes 的 lint / check 只吃「專案目錄」
# 且只驗該目錄的 index.html，靜態伺服器也不會跟著 ../ 出專案根目錄。
# 所以每支必須是獨立專案、共用檔必須實體存在於各專案內。
#
# shared/ 與 vendor/ 是唯一來源，各專案內的副本已 gitignore，
# 不可能漂移。改設計系統改這裡，然後跑這支。
set -euo pipefail
cd "$(dirname "$0")"

for p in */; do
  p="${p%/}"
  [ -f "$p/hyperframes.json" ] || continue
  rm -rf "$p/shared" "$p/vendor"
  cp -R shared "$p/shared"
  cp -R vendor "$p/vendor"
  echo "  → $p"
done
echo "共用檔已同步"
