# YouTube 留言自動回覆系統

## 核心資訊

| 項目 | 說明 |
|------|------|
| 腳本 | `youtube/auto_reply/yt_comment_reply.py` |
| Workflow | `.github/workflows/yt_comment_reply.yml` |
| 排程 | 每 10 分鐘（`*/10 * * * *`） |
| 狀態快取 | GitHub Actions Cache（`yt-reply-state-*`） |
| 頻道 | 連老闆-產地到餐桌（UCKScBZqHjasWfizXWna1Huw） |

## AI 回覆設定

同 IG 系統（Gemini 3.5-flash，15～25字，thinkingBudget:0）

## API 配額

| 項目 | 值 |
|------|-----|
| 每日配額 | 10,000 單位 |
| 回覆成本 | 50 單位/則 |
| 讀取成本 | 1 單位/次 |
| 每日可回覆 | ~190 則 |

## OAuth 設定

- Google Cloud 專案：claude-workspace-495009
- Refresh Token：永不過期
- 測試使用者 `lien2fish@gmail.com` 需在 [Cloud Console](https://console.cloud.google.com/auth/audience?project=claude-workspace-495009) 維持
