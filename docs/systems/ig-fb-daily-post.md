# IG + FB 每日自動發文系統

## 核心資訊

| 項目 | 說明 |
|------|------|
| 腳本 | `instagram/generate_post.py` |
| Workflow | `.github/workflows/daily_post.yml` |
| 排程 | GitHub Actions，每天 UTC 00:00（台灣 08:00） |
| 底圖 | `instagram/template.png`（2700×3375px → 輸出 1080×1920） |
| 圖片存放 | `instagram/posts/YYYY-MM-DD.jpg` |

## 發文流程

1. **Gemini 3.5-flash** 生成海鮮知識 JSON（5~6句，三大類：海鮮/捕魚/漁船）
2. **HF FLUX.1-schnell** 生成對應水彩插圖
3. **PIL** 動態排版合成（字型大小依內容量自動調整）
4. **GitHub API** 上傳圖片 → raw.githubusercontent.com 公開 URL
5. **Meta Graph API v19.0** 同時發送：
   - IG 限時動態（media_type=STORIES）
   - FB 限時動態（透過 cross_post_ids 跨發）

## Facebook 粉絲專頁

| 項目 | 值 |
|------|-----|
| 名稱 | From Source To TABLE |
| Page ID | 1081333268402454 |
| Meta App | Liam AI（ID: 1310018353798687）|
| Business ID | 2163986274210892 |

## 注意事項

- `photo_stories` API 不可用，FB 限時動態改用 IG `cross_post_ids`
- Repo 必須維持 **public**（GitHub raw URL 才可公開存取）
- 每次 workflow commit 圖片，本地 push 前需 `git pull --rebase`
- prompt 為 f-string 時，JSON 範本的 `{}` 必須寫成 `{{}}`
