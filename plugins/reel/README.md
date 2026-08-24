# reel

用 ffmpeg 自建影片剪輯產線時的工程地雷。

## 安裝

```
/plugin marketplace add lien2fish/liam-ai-agent
/plugin install reel@lien-plugins
```

## 內容

- **YouTube「處理完才說無法上傳」的三個真因**（不是變速造成的 VFR）
- 串接外部片頭片尾要正規化的三件事（音量／色彩矩陣／timescale）
- Whisper 對無聲段的幻覺、專有名詞校對
- 渲染前檢查該抓什麼（渲染是 5 倍實時，錯了要重跑）
- 字幕安全寬度、遞迴換行、字型缺字
- **雲端同步會靜默回收素材**，以及暫存塞爆硬碟的連鎖反應
- 多來源重組與聲畫分離
- 不同素材的音訊哲學相反，不要共用工具

MIT
