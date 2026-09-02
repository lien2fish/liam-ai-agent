# 中秋烤肉組 EDM（鑫海產）

1080×1920 直式長圖，給 LINE 群發與 IG 用。2026-09 中秋檔期。

- 可視覺編輯的畫布：https://claude.ai/code/artifact/88de9e09-e017-468b-921f-6bf69a5fbd83
- 成品圖：`中秋烤肉組_鑫海產_1080x1920.png`

## ⏳ 尚未填的欄位

版面上有三處方括號佔位，Lien 給資料後才算完稿：

| 佔位 | 位置 |
|---|---|
| `[LINE ID／訂購電話]` | 左下 footer |
| `[截止日]` | 左下 footer |
| `[取貨日]` | 左下 footer |

## 內容

| 組合 | 售價 | 品項 |
|---|---|---|
| 四牛炭燒 | NT$3,299 | 牛小排／肋眼牛排／翼板／松阪豬／雞松阪／雞腿排 各 300g、日本和牛 400g、秘製鹹豬肉 ×1、黑豬肉香腸 ×8 |
| 現流海味 | NT$1,399 | 活蝦 1 斤、砲管透抽 1 支、秋刀魚 ×4、鯖魚片 ×2、蛤蜊 1 斤 |
| 兩組合購 | NT$4,399 | 單買合計 4,698，省 299 |

兩組各 4-6 人份。標題刻意用具體事實（真的有四種牛、真的是龜吼現流）而不是形容詞堆疊。

## 檔案

| 檔案 | 說明 |
|---|---|
| `Main.dc.html` | **版面原始檔**，改這個 |
| `canvas.json` | 畫布佈局與待辦便利貼 |
| `*.jpg` | 素材圖，見下方授權 |
| `中秋烤肉組_..._1080x1920.png` | 出好的成品 |

`mid-autumn-bbq-set.html` 是組裝後的畫布產物（約 3MB），**不進版控**，需要時重新組裝即可。

## 改版面與重新出圖

```bash
# 1. 改 Main.dc.html

# 2. 本機預覽：把 <x-dc> 內容抽成單檔，起一個 http server
#    （file:// 會被瀏覽器擋掉，一定要走 http）
python3 -m http.server 8765

# 3. 出圖：用系統 Chrome headless，一次到位 1080×1920
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --window-size=1080,1920 --virtual-time-budget=8000 \
  --screenshot="$PWD/out.png" "http://localhost:8765/_preview_Main.html"

# 4. 重新組裝畫布並發布
SD="<design skill 的 base directory>"
node "$SD/seed-canvas.mjs" --template "$SD/payload.template.html" \
  --out mid-autumn-bbq-set.html --title "中秋烤肉組 EDM" \
  --artboard Main.dc.html --canvas canvas.json \
  --image hero.jpg --image steak_new.jpg --image wagyu.jpg --image steak2.jpg \
  --image shrimp.jpg --image squid.jpg --image fish.jpg --image clam.jpg
# 再用 Artifact 工具發布，contract 固定 0.1.31，URL 不變
```

## 圖片來源與授權

全部取自 **Unsplash**（Unsplash License：可商用、免署名）。
只取 `images.unsplash.com`，**不取 `plus.unsplash.com`**（那是 Unsplash+ 付費授權）。

| 檔案 | 對應品項 | 版面位置 |
|---|---|---|
| `hero.jpg` | 炭火主視覺 | 頂部滿版 |
| `steak_new.jpg` | 牛小排・肋眼・翼板 | 左側出血大圖 |
| `wagyu.jpg` | 日本和牛 | 右上 |
| `steak2.jpg` | 肋眼牛排 | 右中大圖 |
| `shrimp.jpg` | 活蝦 | 海鮮 2×2 右上 |
| `squid.jpg` | 砲管透抽 | 海鮮 2×2 右下 |
| `fish.jpg` | 秋刀魚・鯖魚片 | 海鮮 2×2 左上 |
| `clam.jpg` | 蛤蜊 | 海鮮 2×2 左下 |

⚠️ **這些不是實際出貨的商品照。** 產地真實性是這個品牌的說服力來源，
換成龜吼實拍會比圖庫圖有用得多。

## 版面上的地雷（改之前先看）

- **羽化用 `mask-image` 的橢圓漸層**，`-webkit-` 前綴要一起寫，少了在部分瀏覽器不生效。
- **圖疊在文字下當背景時，DOM 順序要在文字之前**，否則圖會蓋住字。
- **羽化圖之間圓心距離要 > 可見直徑**（約為寬度的 0.68 倍），否則會糊成一團——
  海鮮四張就是因為擠在同一側才改成 2×2。
- **小圖縮到 200px 以下就看不出是什麼了**，寧可少而大。
- **量測抓不到溢出**：卡片 `height` 是固定值，內容超出時 `getBoundingClientRect` 仍回報固定高，
  只有截圖看得出來。**每次改完都要真的截一張圖看過。**
- 中文字型走系統堆疊（`Songti TC`／`PingFang TC`），**不要用 Google Fonts**——
  匯出 PNG／PDF 時嵌不進去，畫面與匯出會不一致。
- **出圖不要用 Playwright MCP 截圖**：那邊有 5 秒硬上限，這張圖 8 張素材＋
  `filter` 濾鏡在 2015 Air 上渲染就超過，會一直 `Timeout ... waiting for element to be stable`
  （記憶體與磁碟都沒問題，純粹是渲染時間）。**改用系統 Chrome headless**，
  `--window-size` 直接給 1080×1920 就不必事後裁切。

## 品牌規範

依 `seafood-brand` skill：

- **不寫死合作漁船數量**，一律「與在地共捕漁船長期合作」。
- **「生食級」「可生食」在確認台灣法規依據前不得出現在文案**
  （原本的北海道生食級干貝加購已由 Lien 取消，此規範仍適用於日後加品項）。
- 高端克制，不用促銷語氣、不喊便宜。
