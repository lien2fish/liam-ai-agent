# Liam AI Agent 專案

## 身份與背景
- **使用者**：Lien（企業主 / 管理顧問）
- **公司**：鉅鑫管理顧問有限公司
- **品牌**：鑫酒坊（葡萄酒）、鑫茶坊（茶葉）、匠鑫私廚、龜吼現流活海產
- **核心價值**：鉅鑫只提供最高品質

## 工作目錄
所有開發與任務的根目錄：`/Users/lien/Downloads/Liam AI agent`

## 語言規則
- 一律使用**繁體中文**回覆
- 技術術語、程式碼保留英文原文
- 回覆簡潔有力，重點優先

## 技術環境
- **Shell**：bash（不是 zsh）
- **啟動指令**：`cc`（alias，自動進入此目錄並啟動 Claude Code with NO_FLICKER）
- **設定檔**：`~/.bashrc`（PATH + aliases）、`~/.bash_profile`（引入 .bashrc）
- **Node.js**：v24.15.0，透過 nvm 安裝（`~/.nvm`）

## MCP 工具（已安裝，scope: user）
| 工具 | 套件 | 說明 |
|------|------|------|
| firecrawl | `firecrawl-mcp` | 抓取任何網頁內容，API Key 已設定於環境變數 |
| filesystem | `@modelcontextprotocol/server-filesystem` | 存取 Desktop / Documents / Downloads |
| playwright | `@playwright/mcp` | 控制 Chromium 瀏覽器 |
| google-workspace | `@presto-ai/google-workspace-mcp` | Gmail、Calendar、Drive、Sheets 等，首次使用需 OAuth 登入 |
| notion-mcp | Notion MCP | 搜尋、新增頁面等 Notion 操作 |

- OAuth 憑證存放：`~/.config/google-workspace-mcp/credentials.json`
- 查看 MCP 狀態：`/mcp`

## 已授權工具權限（settings.json allow 清單）

### MCP 工具已允許功能
| 工具 | 已允許的操作 |
|------|-------------|
| filesystem | write_file |
| playwright | navigate、screenshot、snapshot、click、type、press_key、evaluate、resize、close |
| google-workspace | gmail_search、gmail_get、calendar_list、calendar_listEvents、sheets_getRange、people_getMe、time_getCurrentDate |
| firecrawl | map、scrape、crawl、agent、agent_status |
| notion-mcp | post-search、get-self、post-page |

### Bash 指令已允許
| 類別 | 允許的指令 |
|------|-----------|
| npm/Node | `npm list *`、`npx --version`、`node -e ...` |
| Python | `python3 *`、`pip3 install *`、`pip3 --version` |
| 系統工具 | `curl *`、`osascript *`、`open *`、`trash *`、`mv`、`cp`、`mkdir`、`sort`、`env`、`chmod +x` |
| 安全鑰匙圈 | `security find-generic-password *`、`security find-internet-password *` |
| Cron/Shell | `crontab *`、`/bin/bash *`、`bash` |
| 其他 | `log show *`、`convert --version`、`npm cache *`、`xargs du -ch`、`kill <PID>` |

### 內建工具已允許
- `Edit`（無限制，可編輯所有路徑）

### WebFetch 已允許網域
- `raw.githubusercontent.com`

### 技能（Skill）
- `schedule`

## 安全設定（已配置，請勿修改）
- `rm` 已 alias 為 `trash`，刪除會進垃圾桶而非永久刪除
- 永久刪除請用 `rm!`
- `~/.claude/settings.json` 已封鎖危險指令：`rm -rf`、`sudo`、`dd`、`mkfs`、`diskutil erase`、`chmod 777`、`git reset --hard`、`git push --force`、`git clean -f`、`git branch -D`、`shutdown`、`reboot`、`truncate`、`: >`
- 權限模式：**acceptEdits**（檔案編輯自動通過；遇到清單外新工具彈一次確認，允許後自動加入清單）
- **不可用 `dontAsk`**：此模式會靜默封鎖所有需確認的操作（包含 allow 清單內的 Edit），導致任務中斷卡死

## 指引牌產圖系統（2026 扶輪年會）

### 腳本與資料檔
| 項目 | 路徑 |
|------|------|
| 主要腳本 | `/Users/lien/Downloads/南港展覽館/generate_from_numbers.py` |
| Numbers 資料檔 | `/Users/lien/Desktop/HOC團隊/舉牌規格/指引牌資料.numbers` |
| 輸出：立牌 | `/Users/lien/Desktop/HOC團隊/舉牌規格/指引牌/放置立牌/` |
| 輸出：手舉牌 | `/Users/lien/Desktop/HOC團隊/舉牌規格/指引牌/手舉牌/` |

**執行方式：**
```bash
cd /Users/lien/Downloads/南港展覽館 && python3 generate_from_numbers.py
```
腳本會自動跳過已存在的 PNG，只產出新的。

### Numbers 欄位（A~M）
| 欄 | 名稱 | 說明 |
|----|------|------|
| A | 編號 | E1-1, B1-2... |
| B | 版型 | `標準` / `多活動` / `多館別` |
| C | 類型 | `手舉牌` / `立牌` |
| D | 活動區塊 | 依版型（多活動型每行一條，多館別留空） |
| E | 活動區塊英文 | 標準型才填，其他留空 |
| F | 出口①標籤 | Gate 5 / Exit 1 / 多館別館別標題 |
| G | 出口①說明 | 多活動才填 / 多館別子項目（換行分隔） |
| H | 出口②標籤 | 多活動才填 / 多館別第二館標題 |
| I | 出口②說明 | 多活動才填 / 多館別第二館子項目 |
| J | 場地（中） | 中英合行可直接填此欄，K 留空 |
| K | 場地（英） | 分開填寫時才用 |
| L | 底部說明（中） | 標準型才填 |
| M | 底部說明（英） | 標準型才填 |

### 三種版型
- **標準型**：單一活動 + 單一出口，D/E/F/J/K/L/M
- **多活動型**：多活動列表（D 換行分隔）+ 最多兩個 Gate（F-I）+ 場地（J-K）
- **多館別型**：D/E 留空，F/H 館別大標題（紅色），G/I 子項目，J/K 場地

### 字型規格（已確認，2026-05-08）
| 角色 | 字型檔 | Index |
|------|--------|-------|
| zh_font（中文/混合/箭頭） | `/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc` | 2 |
| en_font（純英文） | `/System/Library/Fonts/HelveticaNeue.ttc` | 1 |

### 排版關鍵常數
| 常數 | 值 | 說明 |
|------|-----|------|
| `W × H` | 3535 × 5000 px | 畫布尺寸 |
| `HEADER_BTM` | 1310 | "2026 RIC" 文字下緣，置中頂部基準 |
| `VENUE_Y` | 3750 | 場地文字起始 Y |
| `CONTENT_TOP` | 1380 | 標準型專用 |

**置中邏輯：**
- 多館別：整體內容垂直置中於 `HEADER_BTM` ～ (`VENUE_Y` 有場地 / `H` 無場地)
- 多活動：D/E 活動區塊置中於 `HEADER_BTM` ～ `fm_top`（Gate 區塊上方）；Gate 從 `fm_top` 往下；場地 = `max(y_after_gate + 80 + label_sz, VENUE_Y)`
- 標準型：D/E/F 整體置中於 `CONTENT_TOP` ～ `CONTENT_BTM`

## 開發原則
- 所有檔案操作預設在此資料夾進行
- 不寫不必要的註解，程式碼命名清楚就是最好的說明
- 不過度抽象化，解決當下問題為主
- 不加多餘的錯誤處理，除非是真實的邊界情況

## 回覆風格
- 直接給結論，不囉嗦
- 商業分析附具體數據與建議
- 文案符合高端品牌調性
- 表格優先於長段文字
