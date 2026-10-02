#!/bin/bash
cd "/Users/lien/Downloads/Liam AI agent/dessert/可麗露_工作檔"
for c in ../可麗露_短*_config.json; do
  k=$(basename "$c" | sed 's/^可麗露_//; s/_config.json$//')
  n=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['subject'])" "$c")
  echo "=== $k"
  ./redo.sh "$k" "$n" 2>&1 | grep -v "^mv:"
done
echo ALLDONE
