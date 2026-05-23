# IG 留言自動回覆系統

## 核心資訊

| 項目 | 說明 |
|------|------|
| 腳本 | `instagram/auto_reply/ig_comment_reply.py` |
| Workflow | `.github/workflows/ig_comment_reply.yml` |
| 排程 | 每 5 分鐘（`*/5 * * * *`） |
| 狀態快取 | GitHub Actions Cache（`ig-reply-state-*`） |

## AI 回覆設定

| 項目 | 值 |
|------|-----|
| 主模型 | gemini-3.5-flash |
| 降級 | → 2.5-flash → 2.0-flash |
| 字數 | 15～25 字，繁體中文 |
| maxOutputTokens | 256 |
| temperature | 0.75 |
| thinkingBudget | 0（思考型模型必須設定，否則截斷） |

## 重要注意事項

- **IG Token 到期：2026-07-16**，需重新取得（含 `instagram_manage_comments` 權限）
- Meta Webhook 限制多，改用輪詢（Polling）
- `gemini-3.5-flash` 不設 `thinkingBudget: 0` → 回覆只輸出幾個字（MAX_TOKENS 截斷）
