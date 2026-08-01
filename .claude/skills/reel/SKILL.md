---
name: reel
description: 剪輯短影音／長影音——把拍攝素材剪成 9:16 品牌影片（連老闆海鮮／崁仔頂）、樂器演奏 reels、甜點頻道長片。涵蓋 reel_maker / music_reel / dessert_longform 三套獨立工具的定案規格、config 寫法、渲染前檢查與所有已知地雷。要剪片、改字幕、調段落、產封面時載入。
---

# 剪輯短影音

## 先選對工具（三套完全獨立，勿混用）

| 素材 | 工具 | 特徵 |
|------|------|------|
| 漁港/魚市實拍、口播 | `tools/reel_maker.py` | 降噪＋speechnorm、橘黃高光字幕、1.3 倍速 |
| 樂器演奏 | `tools/music_reel.py` | **原音直出**：不降噪/不變速/不混BGM/無字幕 |
| 甜點頻道 | `tools/dessert_longform.py` | 同 reel 樣式字幕，但獨立流程 |

⚠️ **使用者明確要求不要動 `reel_maker.py`**。music_reel 與 dessert_longform 是為了不污染它才另開的，三者的音訊處理哲學相反，改錯一支會毀掉另外兩條產線。

## 標準流程

```
1. transcribe / batch 轉錄
2. 人工校對字幕稿          ← 不可跳過，Whisper 一定有錯
3. 寫 config.json
4. python3 tools/reel_check.py <config>   ← 渲染前檢查
5. 修完 ❌ 才 build
6. 試片
```

**第 4 步是新加的，不要跳過。** build 約 5 倍實時，2 分鐘的片重跑一次要 10 分鐘；`reel_check` 幾毫秒就把「渲染完才會發現」的問題抓出來，用的是跟 `build()` 完全同一套時間軸對映邏輯（直接 import reel_maker，不是複製一份）。

改字幕或段落**直接改 config 重跑 build，不必重新轉錄**。

## reel_check 會抓什麼

| 等級 | 項目 |
|------|------|
| ❌ | 素材是 iCloud 佔位檔／找不到／被回收 |
| ❌ | cue 對不到時間軸（**不會出現在成片**），並指出是不是誤用了借音段的畫面時間碼 |
| ❌ | 高光詞不在字幕字串裡（不會變橘黃）——最常見是空格差異，會提示 |
| ❌ | 換行後單行仍超過 SAFE_W 820px，會貼邊 |
| ❌ | segment/cover 的 video_index 或時間碼不合法 |
| ⚠️ | 整段沒有字幕（有講話就是漏給 cue；整支無 cue 則視為刻意，不提醒） |
| ⚠️ | 借的聲音長度不到畫面一半，後段會靜音 |
| ⚠️ | 字幕出現 Whisper 已知錯字（表在 `tools/whisper_corrections.json`，新踩到請往下加） |

## 逐字稿校對

Whisper 已知錯法都在 `tools/whisper_corrections.json`，`reel_check` 會自動掃 config 的 cues。**新踩到的錯字請加進那份 JSON**，下次就自動抓。

無人聲片段 Whisper 會吐 initial_prompt 或「請訂閱按讚」等**幻覺文字**，別當逐字稿用。

---

## 長片轉短影音 reel_maker（2026-07-06 建立）

連老闆-產地到餐桌 個人品牌 KOL，把漁港實拍長片剪成品牌短影音（IG/Shorts/TikTok）。全自建、不裝第三方。

| 項目 | 說明 |
|------|------|
| 工具 | `tools/reel_maker.py`（兩步：`transcribe 長片` 出可編輯字幕稿+config範本 → `build config.json` 產出 影片+封面+發文案）|
| 設定範本 | `tools/reel_config_example.json`（赤筆為例：segments段落/cues字幕含高光詞/cover封面/hooks文案）|
| 定案規格 | 原始畫面**滿版letterbox不放大**／關鍵字**橘黃高光**字幕(往上MarginV560)／領夾麥**前景過濾**濾背景人聲／降噪+**自合成輕快BGM**(無whoosh音效)／完整版**1.3倍速**／檔名用**主題名**(不加完整版/版本字樣) |
| 字幕自動換行(2026-07-21 大修) | `SAFE_W` 900→**820px**(版面可用寬920、扣描邊剩908，900等於零淨空會貼邊)；`wrap_lines` 改**遞迴**換行(原本最多切一刀，逗號後半段可達1196px直接衝出畫布)；斷點不切全形括號內、虛字不落行首；**裝了 jieba 就依詞邊界斷行**(否則會切出「可/以」「客/人」)，未裝自動退回啟發式故可攜版不受影響 |
| 音訊(2026-07-12) | 改 `highpass=f=100,afftdn=nf=-28,speechnorm=e=6.25:r=0.00015`：降噪放輕+**speechnorm 把小聲對話拉齊主講者**(原 dynaudnorm 不夠、較小聲對話會被前景偵測判背景而沒字幕，須另補cue) |
| 多來源跨檔重組(2026-07-20) | config 改用 `videos:[路徑...]`＋`segments:[[vi,s,e]]`＋`cues:[[vi,s,e,文字,[高光]]]`，可從多支素材抽段重組成一支。**取代舊的 concat -c copy 前置合檔**(各段本來就獨立重編碼再串接，順帶解決 23.98/24fps 混幀漂移)。單來源舊格式仍相容 |
| 封面卡壓開頭(2026-07-20) | `cover_intro`(預設1.0秒，0=關)：`_封面.jpg` 同一張以相同編碼參數產生後 concat copy 壓進開頭，不重編正片。`cover.video_index` 指定從哪支取幀 |
| 留白給旁白的素材(2026-07-21) | 無人聲B-roll要自行配音時：`bgm:false` 不混配樂、`af:"highpass=f=80"` 不做動態壓縮(預設的 speechnorm 會把環境雜訊拉爆)、`speed:1.0` 留足旁白時間、`cues:[]` 無字幕 |
| **聲畫分離**(2026-07-21) | 借用別段對白配這段畫面（配音蓋圖）。segments 元素寫成 `{"v":[vi,s,e], "a":[vi,s,e]}`，v=畫面、a=聲音。**以畫面長度為準**(聲音短 apad 補靜音、長則 -t 裁掉)，該段原始現場音完全丟棄。**cue 對時＝聲音區間優先**：字幕用對白來源的時間碼寫；借音段的畫面時間碼不參與比對(否則出現對不到聲音的幽靈字幕)。⚠️借音段畫面**不可有同一人正面說話的嘴部特寫**(對不上嘴型) |
| 只留BGM / BGM音量 | `mute_source:true` 去掉原始收音只留 BGM；`bgm_vol`(預設0.15，墊在人聲下)——**無人聲時 0.15 會太小聲**，純 BGM 建議 0.38。已成片要改音軌不必重跑 build：抽 `bgm_bed()` 產配樂後 `-map 0:v -map 1:a -c:v copy` 換軌，1分鐘完成且畫質零損失 |
| 批次轉錄 | `batch <工作資料夾> <影片...>`：多支素材一次轉錄，`transcripts/*.json`＋單一 `字幕稿_全部.txt` 供一次校對，不散落桌面 |
| 搞笑定格特效 | 非內建。客製 `gag_render.py`(letterbox+片尾定格 tpad+drawtext爆字+numpy合成boing/pop音效)＋`build_with_gags.py`(把 gag 段插進 segments、算好cue偏移)。若要常用可正式併進 reel_maker |
| 地雷 | 字幕**必須人工校對**(Whisper會錯,例:赤筆→刺筆、扁鱈→鞭血、圓鱈→鴛鱈/園巡、比目魚→底木魚)；**選段保留的畫面若有講話一定要給cue**否則該幾秒無字幕；**封面字 `・`(U+30FB)、`／`(U+FF0F) 在 STHeiti 是豆腐方框**(已在 `draw_cover_title` 自動替換成 `·` `/`)；opencv裝不起來→人臉追蹤不用；yt-dlp下載要`--extractor-args youtube:player_client=android` |

> 詳見 memory `project_viral_reel_maker.md`。播放器顯示的檔名≠影片內字，發佈後不會出現。首個成品：好市多實測「扁鱈vs圓鱈」(2片合1、3:03、含2搞笑定格段)。

### 崁仔頂魚市批次（2026-07-20～21）
17 支 4K 直式素材（`~/Desktop/IMG_40xx.MOV`，7/14 拍）重組成 4 支：**十年功夫才敢下這刀**(2:09 鮭魚+黑鮪分切)／**一斤1300到台北變2000**(1:41 價格內幕)／**連翻車魚都有**(1:13 親子認魚)／**崁仔頂魚市**(1:56 無字幕無BGM，待自行配音，附 `崁仔頂魚市_口說腳本.md`)。
- config 全在 repo `reels/`，改字幕或段落**直接改 config 重跑 build，不必重新轉錄**
- 逐字稿工作檔留在 `~/Desktop/連老闆_reels_20260720/`（transcripts JSON＋字幕校對稿），要從同批素材再剪別支可直接沿用
- **地雷**：17 支裡有 6 支無人聲，Whisper 對無聲段會吐出 initial_prompt 或「請訂閱按讚」等**幻覺文字**，別當成逐字稿用；魚種校對出現 龜魚→**鮭魚**、石木魚→**虱目魚**、土豬→土魠、紅鞋→紅喉、189斤→18.9斤
- ⚠️**原始 17 支素材已被刪到 iCloud 雲碟垃圾桶**（2026-07-21 發現，非 iCloud 空間回收、無 .icloud 佔位檔）。要再從這批剪片得先還原，垃圾桶約 30 天自動清空

### 第二批：口播＋聲畫分離（2026-07-21）
`IMG_4060`(2:20 抱小孩對鏡頭口播，畫面單一)＋`IMG_4042`(3:50 市場實景無人聲)＋`IMG_4047`(0:39 皇帝條特寫含對話) → **《凌晨12點40這裡才剛開始》**(1:39)，config `reels/凌晨12點40_config.json`（**聲畫分離的完整範本**，8 段中 4 段借音）。
- 手法：口播當聲音主軸、市場實景蓋上去，真人畫面只留**開頭／中段轉折／結尾**三處當錨點——單一構圖的長口播因此不再悶
- 校對：潭崽嶺→崁仔頂、中澳→**南方澳（口誤）**、中港→**東港**、黃地條→**皇帝條**（口誤標註沿用「正確詞（口誤）」寫法）

## 甜點頻道「甜點輕鬆做．師傅真心話」（2026-07-18 建立）

YouTube 全新頻道，**團隊視角**（主講＝合作的專業甜點師朋友、2007年入行開線上課；使用者＝經營/訪談）。標語「配方可以簡單，但話要說真的。」品牌文案＝`~/Desktop/甜點頻道_品牌文案.md`。

| 項目 | 說明 |
|------|------|
| 工具 | `tools/dessert_longform.py`（與 reel_maker/music_reel **完全獨立勿混用**）：`build config.json`／`bgm 影片 [warm\|lively]` |
| config | `videos`多來源檔＋`segments`=[[vi,s,e]]＋`cues`=[[vi,s,e,字幕,[高光]]]＋`speed`＋`bgm`＋`cover`＋`cover_intro`（秒數，預設1.0，0=關）|
| 定案規格 | 直式1080×1920滿版、橘黃高光字幕（同reel樣式MarginV560）、降噪+speechnorm、**9:16封面卡自動壓進影片開頭1秒**（與`_封面.jpg`同一張，concat copy不重編正片）、自合成BGM兩款（warm 76bpm柔和／lively 112bpm輕快，勿用ffmpeg tremolo會exit 222）|
| 首批產出 | 桌面`肉桂捲研發日記/`：長片《六種口味肉桂捲全記錄》13:30(1.2x)＋系列EP1~7(1.3x, 1:47~2:19)。config＝repo `dessert/`（EP1~7＋長片＋產生器`make_ep_configs.py`）|
| 發佈策略 | 開站日長片+EP1同天，之後每週二/五一集，Shorts（抹茶色素/180元極限/杜拜巧克力）穿插；播放清單《肉桂捲研發日記》|
| 地雷 | **iCloud 在磁碟吃緊時會無聲回收桌面大檔**（2026-07-18 批次剪輯中 IMG_4106/4107 被回收→EP5只出16秒）。跑剪輯前確認來源非`.icloud`佔位檔、必要時`brctl download`；工具已加seg產出檢查（<10KB即raise）。concat清單內路徑一律用**絕對路徑**（相對路徑以清單所在目錄解析）|

## 樂器演奏短影音 music_reel（2026-07-14 建立）

直笛/樂器演奏長片轉 9:16 reels，**與 reel_maker 海鮮流程完全獨立、勿混用**（使用者明確指示不動 reel_maker）。

| 項目 | 說明 |
|------|------|
| 工具 | `tools/music_reel.py`（兩步：`analyze 長片` 出每秒能量曲線+config範本 → `build config.json` 產出 影片 到桌面）|
| 定案規格 | **原音直出**：不降噪/不speechnorm/不變速/不混BGM/無字幕（音樂就是內容）；段落交界 0.15s afade 防爆音；音訊192k、1080×1920、crf20、24fps；檔名＝曲名 |
| 版型（蓋臉版） | 頂部白底大樂譜面板 `score_h=450`（`shift_y=0`+`score_y=0`）**從頂端蓋到鼻子，只露吹奏嘴型+手部**（保護孩子肖像，使用者指定）；樂譜圖去白邊放大置中，隨演奏換頁（每頁2小節含注音唱名）；0~2s 曲名橫幅（白格紋紙底+棕色 MarkerFelt 手寫字）疊面板下方，全程不露臉 |
| config 要點 | `segments`=[[演奏起-0.4s, 迄+0.5s]]（原片時間軸）；`score` 換頁時間=**輸出後時間軸**，估法：演奏總長÷頁數均分再依聽感微調；頭位置不同只調 `score_h` |
| 可攜版 | 桌面 `樂器演奏reels工具/`（music_reel.py+README+範例config），供另一台電腦執行；新機需 `pip3 install numpy pillow`+ffmpeg（不需ffprobe）；MarkerFelt 為 mac 內建字型，非 mac 要改 `MARKER_FONT` |
| 首支成品 | NO BATIDÃO（素材 `VID_20260710081733888.MP4`、樂譜 IMG_6458/6459/6461/6462.JPG、config `NO_BATIDAO_config.json`，皆在桌面）；發布平台未定 |

> 詳見 memory `project_music_reel.md`。

