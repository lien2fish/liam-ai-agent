# safe-commit

commit／push 前的敏感資料檢查與外洩止血流程。

## 安裝

```
/plugin marketplace add lien2fish/liam-ai-agent
/plugin install safe-commit@lien-plugins
```

## 內容

- 三步驟：判敏感等級 → **實查目的地公開程度**（repo 名稱不代表可見性）→ 掃暫存區
- 附 `scripts/check_staged.py` 掃描腳本
- **中文檔名讓 git 輸出八進位跳脫，grep 永遠 0 命中且不報錯**——
  任何用 git 列檔名的指令都要加 `-c core.quotepath=false`
- `.gitignore` 不會取消追蹤、`git rm` 不會清歷史、
  force push 後 GitHub 仍以 SHA 提供舊 commit
- 完整止血流程（含最常被漏掉的：寫信請 GitHub 清快取）

MIT
