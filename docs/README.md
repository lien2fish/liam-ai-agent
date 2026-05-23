# Liam AI Agent — 系統文件索引

> 鉅鑫管理顧問 × 龜吼現流活海產｜自動化系統總覽

## 📁 目錄結構

```
docs/
├── systems/          # 各自動化系統說明
│   ├── ig-fb-daily-post.md       IG+FB 每日自動發文
│   ├── ig-comment-reply.md       IG 留言自動回覆
│   ├── youtube-comment-reply.md  YouTube 留言自動回覆
│   └── gmail-automation.md       Gmail 自動化
├── setup/            # 環境設定與憑證
│   ├── github-secrets.md         GitHub Secrets 清單
│   ├── google-oauth.md           Google OAuth 設定
│   └── mac-crontab.md            Mac 本機排程
└── tasks/            # 任務管理
    └── PENDING.md                待執行任務
```

## 🤖 GitHub Issues 任務系統

### 新增任務（手機操作）
1. 開 GitHub App → Issues → New Issue
2. 選擇模板：**Claude 任務** 或 **內容創作需求**
3. 填寫內容 → Submit
4. 系統自動加上 `claude-task` + `pending` 標籤

### 執行任務（Mac）
回到 Mac，告訴 Claude Code：
```
去 GitHub 讀取有 claude-task + pending 標籤的 Issue 並執行
```

### Labels 說明
| Label | 說明 |
|-------|------|
| `claude-task` | 交由 Claude Code 在 Mac 執行 |
| `auto-execute` | GitHub Actions 自動執行，不需 Mac |
| `pending` | 待執行 |
| `in-progress` | 執行中 |
| `completed` | 已完成 |
| `automation` | 自動化系統相關 |
| `content` | 內容創作相關 |
| `config` | 設定變更 |

## 🔄 自動化系統狀態

| 系統 | 排程 | 狀態 |
|------|------|------|
| IG+FB 每日發文 | 每天 08:00 | ✅ |
| IG 留言自動回覆 | 每 5 分鐘 | ✅ |
| YouTube 留言自動回覆 | 每 10 分鐘 | ✅ |
| Gmail 清理 | 每天 08:05 | ✅ |
| Gmail 新聞摘要 | 每天 08:00 | ✅ |
| TikTok | 手動 | — |
