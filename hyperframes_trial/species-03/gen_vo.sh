#!/bin/bash
# 逐句產生克隆旁白並用 large-v3 回聽；音檔不進公開 repo
cd "$(dirname "$0")"
python3 -c "import json;[print(k+'\t'+s) for k,s,_ in json.load(open('lines.json'))]" | while IFS=$'\t' read k s; do
  [ -n "$ONLY" ] && [[ " $ONLY " != *" $k "* ]] && continue
  ~/聲音素材/tts/say.py "$s" -o "$PWD/audio/$k" >/dev/null 2>&1 </dev/null && mv "audio/${k}_000.wav" "audio/$k.wav"
  printf "%s " "$k"; python3 ~/聲音素材/tts/check_say.py "audio/$k.wav" "$s" --model large-v3 2>&1 </dev/null | tail -2 | tr '\n' ' '; echo
done
