---
name: vector-ai
description: 點陣圖轉 Illustrator 可編輯向量 .ai（tools/image_to_vector_ai.py），以及六邊形理監事牌換姓名（design/hex_badge_rename.py）。含字型限制、CMYK 就地重繪、排版反解。要轉向量檔、改名牌時載入。
---

## 點陣圖轉向量 .ai 工具（2026-07-03 建立）

把「文字＋簡單圖形」的點陣輸出圖（TIFF/PNG）轉成 Illustrator 可編輯的**真向量 .ai**。

| 項目 | 說明 |
|------|------|
| 腳本 | `tools/image_to_vector_ai.py`（改 `JOBS` 清單：來源檔名／第1行／第2行／輸出名，再跑）|
| 原理 | reportlab 產向量 PDF → 存 `.ai` 副檔名（PDF 相容，AI 可開）。原生二進位 .ai 無法直接寫 |
| 字型 | `/System/Library/Fonts/STHeiti Medium.ttc`（PingFang 是 CFF，reportlab 會報錯）；`setTextRenderMode(2)` 填色+描邊 fake-bold |
| 自動偵測 | sips 轉 RGB→判斷有無六邊形（bbox 填充率>0.55）→ 求平頂六邊形頂點＋文字行帶；**逐張取樣原檔 CMYK** 保留職級色碼 |
| 校準 | `em_px=原字高×1.104`、baseline=`cy+0.38×em_px`、畫板=原像素尺寸 |
| 地雷 | **檔名不一定=內容**（惜食「雙板1~5」實為 6 位理事），轉檔前 Read 視覺確認文字；輸出背景透明適合模切 |

### 六邊形牌換姓名（2026-07-22）
`design/hex_badge_rename.py`：`python3 design/hex_badge_rename.py <來源tiff> <新姓名> [輸出tiff]`。首次應用＝以某位現任理事的牌為模板產出新任理事牌（TIFF＋.ai 各一份）。**原持牌人仍在任、兩人並存，理事牌 8 位**；只有當初複製出來當來源的 `..._CMYK拷貝.tiff` 工作檔移至 `已撤除_20260722/`。
- **直接在 CMYK 空間就地重繪、零色彩轉換**：白字＝CMYK(0,0,0,0)，故不是「畫白色」而是依覆蓋率衰減背景 `arr*(1-mask)`，抗鋸齒自然保留、油墨值零偏移。驗證含「職稱行逐像素未變」
- **原稿字型＝`Hiragino Sans GB.ttc` index 3**（非專案慣用的 STHeiti）。反推法：拿同批已有該字的牌當標準答案比對 IoU（拿同字在另一面牌上比對）→ Hiragino 0.88~0.98、PingFang 0.55、STHeiti 0.41
- **排版反解**：每字置中於等距格子，advance **416.5**、中心 x=**1334**、字級 **460**、anchor=`mm`、姓名行基準 y=**1420**（重建原三字姓名 IoU 0.94）。2~4 字自動居中。**非統一 baseline 排版**，用 pen 反推會得到不一致的 y，別走那條路
- ⚠️**.ai 與 TIFF 字型必然不同**：Hiragino 是 PostScript/CFF，**reportlab 載不進去**（同 PingFang 地雷），故 43 張 .ai 一律 STHeiti Medium＋`setTextRenderMode(2)` 描邊 fake-bold 模擬。新牌沿用以**與另外 42 張整齊**（理監事樹整面牆一起看）。**同一批只交同一種格式**給印刷廠
- `tools/image_to_vector_ai.py` 加**第4參數 filter**只跑指定 job：`... . 向量ai檔案 /tmp/hexqa [已移除]`，不必為一張重產 43 張
- 驗證 .ai 用 PyMuPDF 比對同批既有檔：頁面尺寸/嵌入影像數(應0=真向量)/字型/CMYK填色須逐項相符

> 首次應用：惜食第七屆理監事六邊形牌 43 張全數轉檔（`…/惜食廚房輸出/第七屆理監事樹調整/向量ai檔案/`）。詳見 memory `feedback_raster_to_vector_ai.md`
