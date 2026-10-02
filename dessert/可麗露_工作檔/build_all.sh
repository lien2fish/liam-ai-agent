#!/bin/bash
cd "/Users/lien/Downloads/Liam AI agent"
for c in dessert/可麗露_短*_config.json; do
  echo "=== $c"; python3 tools/dessert_longform.py build "$c" 2>&1 | tail -3
done
echo ALLDONE
