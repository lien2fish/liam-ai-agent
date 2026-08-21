# 一人五品牌 — 對外簡報網站

給潛在顧問客戶看的能力展示品。內容與 `design/pitch_deck.py` 產出的 16:9 PDF 同一份。

| | |
|---|---|
| 線上網址 | https://gs-deck.pages.dev |
| 部署 | Cloudflare Pages，專案名 `gs-deck` |
| 更新 | 改完 `index.html` 後跑下面那行，網址不變 |

```bash
npx wrangler pages deploy design/deck --project-name=gs-deck --branch=main --commit-dirty=true
```

## 為什麼不放 GitHub Pages

`lien2fish.github.io/...` 這種網址會帶出 GitHub 帳號名，對方能順著找到
`github.com/lien2fish` 底下所有公開程式庫。Cloudflare Pages 的網址與 GitHub 無關，
客戶點進去只有簡報。

## 內容規則

**這是對外的，全部脫敏**——不含客戶姓名、報價、庫存成本、個人財務。
產出數字（18 條排程／94 天發文／96 份日報／60 支影片等）取自版本紀錄與平台後台，
時數與金額為估算且在頁面上明確標示假設。改內容前先跑：

```bash
python3 .claude/skills/safe-commit/check_staged.py
```
