# line-assistant

部署一個只有自己能用的 LINE AI 助理（Cloudflare Worker）。

這個 plugin 提供**方法**，不含程式碼——範本在
[liam-ai-agent](https://github.com/lien2fish/liam-ai-agent) 的 `line_assistant/`。

## 安裝

```
/plugin marketplace add lien2fish/liam-ai-agent
/plugin install line-assistant@lien-plugins
```

## 內容

- 範本連結與設定方式（設定與程式分離，改 `profile.js` 不改 `worker.js`）
- **兩道非設不可的防護**：webhook 簽章驗證、使用者白名單，兩者皆須 fail closed
- LINE 的計費與時效規則（reply 免費／push 計額度／replyToken 60 秒）
- 部署九步驟與驗收方式
- 已知陷阱，包含 `wrangler secret put` 會靜默存成空字串

MIT
