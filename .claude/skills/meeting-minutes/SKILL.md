---
name: meeting-minutes
description: 會議錄音轉會議記錄（meetings/audio_to_minutes.py）：Gemini File API 上傳轉錄、輸出詳細版＋簡化版雙 PDF、字型限制、Gemini 額度地雷、人名校對規則。有錄音檔要轉會議記錄時載入。
---

## 會議錄音轉會議記錄系統（2026-06-23 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 腳本 | `meetings/audio_to_minutes.py` |
| 用法 | `python3 meetings/audio_to_minutes.py "<音檔路徑>" "<會議名稱>"` |
| 輸出 | `~/Desktop/{會議名稱}_會議記錄.pdf` ＋ `~/Desktop/{會議名稱}_會議記錄_簡化版.pdf` |
| 排程 | 手動執行，非自動化（依需求隨時對單一錄音檔跑） |

### 流程
1. **上傳音檔**：用 Gemini File API resumable upload（音檔通常 >20MB，無法用 inline base64），上傳後 poll `state` 直到 `ACTIVE`
2. **轉錄＋結構化**：呼叫 `gemini-2.5-flash` 的 `generateContent`，傳入 `file_data`（mime_type + file_uri），`thinkingConfig.thinkingBudget: 0`，`responseMimeType: application/json`，輸出結構化 JSON：
   `meeting_title / meeting_date / agenda_items[{topic, discussion_summary, decisions}] / action_items[{task, owner, due}] / overall_summary`（不含 attendees，使用者要求拿掉與會人員欄位）
3. **簡化版**：第二次呼叫 Gemini（純文字，不需重傳音檔），把 `discussion_summary` 濃縮成 `key_points`（3-5條精簡要點，保留所有數字/人名/決議，只精簡敘述文字）
4. **排版 PDF**：用 reportlab 輸出**兩份 PDF**到桌面：
   - `{會議名稱}_會議記錄.pdf`（詳細版，完整討論段落，正式記錄保存用）
   - `{會議名稱}_會議記錄_簡化版.pdf`（簡化版，條列要點，快速瀏覽用）
5. **人名校對**：語音辨識常把人名聽成同音字，產出後務必請使用者校對一次人名再定案。**每份錄音的校對結果只適用該份**，不要把上一份的人名/職稱修正規則直接套用到下一份新錄音（職稱縮寫如扶輪社PG/PP/DG/DK各有不同意義，需使用者逐份確認）

### 重要技術細節
- **字型地雷**：`PingFang.ttc` 在 reportlab 會直接報錯（`postscript outlines are not supported`，因為是 CFF outline 格式）。改用 `/System/Library/Fonts/STHeiti Light.ttc`（index 0，正文）+ `STHeiti Medium.ttc`（index 0，標題），這兩個是 TrueType outline 格式，reportlab 可正常載入
- **GEMINI_KEY 本機快取**：已存放於 `config/.gemini_key`（已 gitignore），本機腳本可直接讀取，不需每次都去 Google Cloud Console 複製
- **GEMINI_KEY 額度地雷**（2026-06-23實測）：這組 Key **沒有開通 Cloud Billing，仍受免費額度限制**——`gemini-2.5-flash` 限20次/天（超過會429 RESOURCE_EXHAUSTED，重試無效需等隔天重置，重置時間約UTC 00:00＝台北15:00）；`gemini-2.5-pro` 免費額度直接0token，完全不可用；`gemini-2.5-flash-lite`額度較寬鬆但對長音檔（60分鐘以上）容易卡進repetition loop或內容變空泛模糊，**避免用於正式會議記錄**。503 UNAVAILABLE（伺服器過載）是暫時性的，重試幾次（間隔10-15秒）通常會恢復，跟429額度問題要分開判斷
- **本機 Whisper 備案**：已安裝 `openai-whisper`（`pip3 install openai-whisper`，含torch CPU版）。這台Mac是Intel x86_64無GPU，65分鐘音檔預估跑1-2小時以上，平時優先用 Gemini API，只有額度/過載卡住才考慮本機Whisper

---
