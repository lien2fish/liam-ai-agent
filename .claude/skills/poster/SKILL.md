---
name: poster
description: 海報與徽章排版：鑫海產「鮮味聚」商務版海報（design/seafood_poster_rotary.py）、惜食台灣 A1 表揚海報、公益活動圓形徽章。含品項欄位格式與版面上限。要做海報、改品項報價版面時載入。
---

> ⚠️ 捐款名單（姓名與金額）已移到 `config/savefood_donors.py`（repo 為 public，config/ 已 gitignore）。

## 鑫海產「鮮味聚」海報（2026-09-07 改版）

⛔ **舊的水彩四季版型已刪除**（`seafood_poster.py` ＋ spring/summer/autumn/winter config，
2026-09-07 Lien 指示清掉）。**現行只有一套**：商務沉穩版，用於扶輪社社團推薦。
不要再引用 `seafood_poster.py`、`draw_list` 自動縮字級、`bottom_strip` 那些規格，都不存在了。

| 項目 | 說明 |
|------|------|
| 腳本 | `design/seafood_poster_rotary.py` |
| Config | `design/seafood_poster/rotary.json` |
| 品項來源 | **不在 config 裡**——`items_from` 指向 `current.json`（Lien 給的實際店內售價）。**價格只維護一處** |
| 底圖 | `bg_blue_deep.png`，壓到 20% 混色＋由上而下漸層暗罩，只留海洋質感不搶字 |
| 輸出 | 1080×1920 RGB PNG，LINE 群組／IG 用，**不做印刷**。成品另存 `~/Desktop/鑫海產_鮮味聚海報/` |
| 重產 | `python3 design/seafood_poster_rotary.py design/seafood_poster/rotary.json` |

版面＝品牌區（鑫海產／XIN SEAFOOD／龜吼現流．產地直送）／主標「本季當令」／系列小標
／金線／8 項編號式清單／金線／信任區塊／洽詢膠囊條／深藍頁尾條。

- **信任區塊的主軸＝「新鮮海產」**（2026-09-07 Lien 指定，原本是「為什麼是龜吼」）。
  三行＝來源／處理／速度，全部出自 `seafood-brand` 已核可的事實
- ⛔ **漁船不寫數量、不寫「老闆出海」、不寫「生食級」**。
  ⚠️ 這份 skill 舊版寫過「生食級屬狀態與等級可留」——**那是錯的**，與 `seafood-brand`
  「法規依據未確認前一律不准出現」直接衝突，2026-09-07 已更正
- 品項中文行格式＝**「前綴 名稱　形容詞」**（半形空格分前綴、**全形空格**分形容詞），
  `split_zh` 靠這個格式拆欄；改 `current.json` 的寫法會讓排版錯位
- 價格格式＝「NT$500 / 片」（`split_price` 拆金額與單位），或整串倒裝如「2 尾 NT$400」（無單位）
- **金額右緣統一切齊 `X_UNIT - 10`**，不是靠單位寬度反推——否則沒單位的那項會突出（踩過）
- ⚠️ **PIL 的 `rounded_rectangle` 半透明填充在這版沒吃到 alpha**：洽詢條用過
  `fill=(255,255,255,20)`，結果整條變不透明白、把白字吃掉。一律用實心深底 `(16,38,62)` ＋金框
- 字距靠 `draw_tracked` 逐字繪製（PIL 沒有 letter-spacing）
- **8 項是版面上限**：`LIST_TOP=556`、`ROW_H=106`，第 8 項落在 y=1404，再多會撞信任區塊
- 地雷：中點一律用全形「．」，不要用 STHeiti 的「·」（全形寬且字面靠左，前後會有明顯空隙）
- `photos/`（官網去背海鮮照）與 `bg_blue_light.png`／`bg_autumn.png` 留著，
  但**目前沒有任何腳本在用**——舊水彩版型的遺留素材
- 成品 PNG 與 `photos/` 已 gitignore（前者可重產，後者是實拍素材而 repo 為 public）

---
## 海報圖片生成系統（2026-05-26 建立）

### 公益活動圓形徽章（4張）
| 項目 | 說明 |
|------|------|
| 腳本 | `/Users/lien/Downloads/gen_circles_hq.py`（或類似名稱） |
| 輸出 | `/Users/lien/Downloads/circle_1_愛心捐款_HQ.png` ～ `circle_4_物資捐贈_HQ.png` |
| 規格 | 2400×2400px，300dpi，透明背景圓形 |
| 設計 | 相片底圖 + 暗色覆蓋 + 愛心底紋 + 白色文字 + 白色邊框 |
| 四張內容 | 愛心捐款（含匯款帳號）、半日志工、惜食送餐、物資捐贈 |

### A1 表揚海報（惜食台灣行動協會）
| 項目 | 說明 |
|------|------|
| 腳本 | `/Users/lien/Downloads/gen_a1_list.py` |
| 輸出 | `/Users/lien/Downloads/海報/累積100萬以上捐款_名單.png` |
|      | `/Users/lien/Downloads/海報/累積50萬以上捐款_名單.png` |
| 規格 | 7016×9933px（A1），300dpi |
| 底圖 | 100萬：`/Users/lien/Desktop/未命名設計-1.jpg`（手持愛心）|
|      | 50萬：`/Users/lien/Desktop/191214-growth-1170x780.jpg`（嫩芽）|
| 版面結構 | 主標題「惜食台灣行動協會」→ 子標題（累積XXX萬以上捐款）→ 捐款名單 → 底部標語 |
| 名單邊界 | 對齊角落愛心圓心 x=700，名字左齊、金額右齊，col_gap=700px |
| 換行邏輯 | 名字超過 name_col_w（≈3499px）時自動找最平衡斷點（兩行都需 ≤ name_col_w）|
| 底部標語 | 裝飾線上方：「等一個便當，等一個疼惜」/ 下方：「疼惜食物。疼惜台灣」|
| 裝飾線 | x=1000 ～ x=6016（避開角落愛心），accent色粗線 + 白色細線 |

#### 100萬捐款名單
| 捐款人 | 金額 |
|--------|------|

#### 50萬捐款名單
| 捐款人 | 金額 |
|--------|------|
| 白俊宇 | 全區磁磚捐贈 |

### 重新產出指令
```bash
python3 /Users/lien/Downloads/gen_a1_list.py
```

---
