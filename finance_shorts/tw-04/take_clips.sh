#!/bin/bash
# tw-04 畫面素材（YouTube 創用 CC，8 秒一段）：手機、銀行、資安、機房、文件、歐盟
t() { python3 broll.py take "$1" "$2" "$3" 8 2>&1 | tail -1 | cut -c1-70; }
t bk_bank_00 X8FkegKcfjo 0
t bk_bank_01 X8FkegKcfjo 7
t bk_cyber_00 0WmT4hkACno 0
t bk_cyber_01 0WmT4hkACno 10
t bk_cyber_02 0WmT4hkACno 20
t bk_cyber_03 WhtRhjbcrjg 0
t bk_cyber_04 WhtRhjbcrjg 8
t bk_cyber_05 WhtRhjbcrjg 16
t bk_server_00 XrwewCWMq6k 2
t bk_server_01 r68DbzAKxKE 2
t bk_server_02 ZVc7UQuEPOo 2
t bk_server_03 ZVc7UQuEPOo 14
t bk_server_04 ZVc7UQuEPOo 28
t bk_phone_00 SW6-tncAC-Q 0
t bk_phone_01 ZW2S3RVsNlI 1
t bk_phone_02 Gj4aHCMz5TM 1
t bk_phone_03 Gj4aHCMz5TM 9
t bk_phone_04 R75aMAwxtik 1
t bk_phone_05 6OEbomOX9E4 1
t bk_phone_06 6OEbomOX9E4 7
t bk_law_00 s3F3Ba3xckg 1
t bk_law_01 bD1idP5K5y4 1
t bk_law_02 bD1idP5K5y4 10
t bk_law_03 OQq6cAMM7uA 1
t bk_law_04 OQq6cAMM7uA 7
t bk_eu_00 Bg77Md-T0qo 3
t bk_eu_01 Bg77Md-T0qo 25
t bk_eu_02 Bg77Md-T0qo 50
