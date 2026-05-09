每天早晨執行時，依序完成以下步驟，彙整成「早晨日報」：

## 步驟一：取得今天與昨天的日期
使用 `mcp__google-workspace__time_getCurrentDate` 取得今日日期（台北時區）。

## 步驟二：Gmail 昨日重要郵件
使用 `mcp__google-workspace__gmail_search` 搜尋昨天收到的郵件（`after:YYYY/MM/DD before:YYYY/MM/DD`），取前 20 封，篩選出：
- 需要回覆或處理的郵件
- 客戶來信（鑫酒藏、鑫茶坊、鑫海產、匠鑫私廚相關）
- 帳單或付款通知
- 重要通知

## 步驟三：今日行程（Google + Mac 本機）

**Google Calendar：**
使用 `mcp__google-workspace__calendar_listEvents` 列出今天所有行程（calendarId: primary）。

**Mac 本機行事曆：**
使用 Bash 執行以下 AppleScript 取得今日本機行事曆事件：
```bash
osascript << 'EOF'
tell application "Calendar"
    set today to current date
    set startOfDay to today - (time of today)
    set endOfDay to startOfDay + 86399
    set output to ""
    repeat with cal in calendars
        set evts to (every event of cal whose start date >= startOfDay and start date <= endOfDay)
        repeat with e in evts
            set output to output & (summary of e) & " | " & ((start date of e) as string) & "\n"
        end repeat
    end repeat
    return output
end tell
EOF
```
合併 Google 與本機行事曆結果，依時間排序。

## 步驟四：彙整早晨日報

輸出格式如下：

---

# ☀️ 早晨日報｜{今日日期}

## 📬 昨日 Gmail 摘要
（列出需要處理的郵件，每封一行：寄件人 / 主旨 / 摘要一句話）
若無重要郵件，顯示「無待處理郵件」

## 📅 今日行程（Google + Mac）
（合併列出今天所有行程，含時間與地點，標註來源）
若無行程，顯示「今日無排程行程」

## ✅ 今日建議待辦
（根據郵件與行程，自動推導 3–5 項今日重點任務）

---

語言：繁體中文，語氣簡潔有力。
