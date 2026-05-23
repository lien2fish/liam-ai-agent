# Mac 本機 Crontab 排程

> 根目錄：/Users/lien/Downloads/Liam AI agent
> 查看：`crontab -l`
> 編輯：`crontab -e`

## 排程清單

| 時間 | 腳本 | Log |
|------|------|-----|
| `0 8 * * *` | `gmail_news_digest.py` | 今日新聞摘要.md（覆寫） |
| `5 8 * * *` | `gmail_monthly_cleanup.py` | 財務/gmail_cleanup_log.txt |
| `0 8 1 * *` | `notion_crm/monthly_report.py` | /tmp/notion_monthly_report.log |
| `0 8 * * *` | `instagram/generate_post.py`（本機備用） | /tmp/ig_post.log |
| `0 6 * * *` | `cache_cleanup.sh` | /tmp/liam_cache_cleanup.log |

> 注意：Mac 需開機且解鎖，排程才會觸發。主要發文已移至 GitHub Actions 雲端執行。
