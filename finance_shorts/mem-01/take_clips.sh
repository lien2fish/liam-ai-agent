#!/bin/bash
# mem-01 畫面素材（YouTube 創用 CC，8 秒一段）；抽格看過才留
t(){ python3 broll.py take "$1" "$2" "$3" 8 2>&1 | tail -1 | cut -c1-90; }
i=0; for s in 0 8 16 24 32 40 48 56; do t mm_chip_$(printf %02d $i) MwMyIDs9DQU $s; i=$((i+1)); done
for s in 22 150 214 222; do t mm_chip_$(printf %02d $i) LmFt8a_oYqs $s; i=$((i+1)); done
i=0; for s in 0 8 16 24 707 715; do t mm_ram_$(printf %02d $i) oXZWF6gDNLI $s; i=$((i+1)); done
i=0; for s in 640 700 826 834 842 850 964 972; do t mm_server_$(printf %02d $i) gsN_CJJDy_o $s; i=$((i+1)); done
i=0; for s in 0 8 15; do t mm_phone_$(printf %02d $i) TagIkml2Cgw $s; i=$((i+1)); done
t mm_phone_03 EpxCSxSHFGY 0; i=4
for s in 152 190 198 228 236; do t mm_phone_$(printf %02d $i) 3GQuAlU-ZYI $s; i=$((i+1)); done
i=0; for s in 77 232 240 258 266 283 291; do t mm_laptop_$(printf %02d $i) ip4lMh_aXkg $s; i=$((i+1)); done
i=0; for s in 490 498 740 748 1480 1488 1730 1738 2240 2470 2478; do t mm_store_$(printf %02d $i) qmtMhecPAgU $s; i=$((i+1)); done
t mm_korea_00 L7L3Pwq0xnk 3; i=1
for s in 0 10 18; do t mm_korea_$(printf %02d $i) jd5cxSFaMis $s; i=$((i+1)); done
