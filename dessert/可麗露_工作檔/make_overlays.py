"""疊圖設定：時間用「素材秒數」寫，自動換算成成品秒數。產出 overlay_<短X>.json。"""
import json, glob, os
ROOT = "/Users/lien/Downloads/Liam AI agent"
TOP = 1470  # 字幕底緣約 y=1360，字卡放在字幕下方，不擋臉

def mapper(cfg):
    sp = cfg.get("speed", 1.0)
    real = f"{cfg['out_dir']}/{cfg['subject']}_段落時間.json"
    if os.path.exists(real):  # build 寫出的實際段落起點，與字幕同一套時間
        offs = json.load(open(real))
        def m(n, t):
            for cs, name, s, e in offs:
                if name == f"IMG_{n}.MOV" and s <= t <= e:
                    return round(cs + (t - s) / sp, 2)
            raise ValueError(f"{n} {t} 不在任何段落")
        last = offs[-1]
        return m, round(last[0] + (last[3] - last[2]) / sp, 2)
    def m(n, t):
        cum = 0.0
        for seg in cfg["segments"]:
            vi, s, e = seg[:3]
            if os.path.basename(cfg["videos"][vi]) == f"IMG_{n}.MOV" and s <= t <= e:
                return round((cum + t - s) / sp, 2)
            cum += e - s
        raise ValueError(f"{n} {t} 不在任何段落")
    total = sum(s[2] - s[1] for s in cfg["segments"]) / sp
    return m, total

def card(t, title, lines): return {"type": "card", "t": t, "title": title, "lines": lines, "top": TOP}
def label(t, text, y=1560): return {"type": "label", "t": t, "xy": [540, y], "text": text}

PLAN = {
 "短1_沒靜置": lambda m, T: [
   card([m(4971, 246.0), m(4971, 250.2)], "正常做法", ["第一天做麵糊、冷藏靜置", "第二天才烤"]),
   card([m(4988, 43.86), m(4988, 49.6)], "這次", ["早上才做麵糊", "只靜置 1 小時就進烤箱"]),
   label([T - 1.6, T], "你等得了兩天嗎？留言告訴我們")],
 "短2_銅模兩千": lambda m, T: [
   card([m(4971, 375.3), m(4971, 382.2)], "法國銅模", ["一顆約 2,000 元", "十幾顆 ≈ 2 萬"]),
   card([m(4971, 401.6), m(4971, 403.4)], "不沾模", ["一顆 80 元"]),
   label([T - 1.6, T], "你會買 2,000 還是 80？")],
 "短3_食材兩成": lambda m, T: [
   card([m(4972, 174.0), m(4972, 184.0)], "可麗露市價", ["一顆 80～120 元", "原味約 70～80 元"]),
   card([m(4972, 261.2), m(4972, 278.2)], "食材成本 < 20%", ["貴在：人工、模具", "時間、高溫烤焙的電費"]),
   label([T - 1.6, T], "你覺得一顆多少才合理？")],
 "短4_辭職": lambda m, T: [
   card([m(4972, 314.6), m(4972, 322.5)], "業外收入", ["很好、很適合"]),
   card([m(4972, 328.0), m(4972, 336.6)], "直接辭職？", ["初期投資額高", "一開始沒有客群"]),
   label([T - 1.6, T], "你會辭職做甜點嗎？")],
 "短5_布丁": lambda m, T: [
   card([m(4972, 446.8), m(4972, 462.6)], "布丁 vs 可麗露", ["一樣好賣", "布丁投資不到 1/10", "布丁接單才做・可麗露可冷凍"]),
   label([T - 1.6, T], "你比較想吃哪一個？")],
 "短6_不能碰水": lambda m, T: [
   card([m(4971, 525.7), m(4971, 542.5)], "銅模保養", ["完全不要碰水", "用完擦乾淨就好"]),
   card([m(4971, 642.7), m(4971, 648.4)], "簡單記", ["便宜的模具：隨便刷", "精密的模具：不碰水"]),
   label([T - 1.2, T], "你的模具碰過水嗎？")],
 "短7_上課模具": lambda m, T: [
   card([m(4971, 474.4), m(4971, 480.6)], "上課 vs 回家", ["一堂課 2,000 多", "銅模一套 ≈ 2 萬"]),
   card([m(4971, 412.5), m(4971, 419.1)], "兩種模具", ["不沾模：刷奶油", "銅模：蜂蠟"]),
   label([T - 1.6, T], "你吃得出差別嗎？")],
 "短8_白頭": lambda m, T: [
   card([m(4990, 106.6), m(4990, 119.1)], "白頭不是失敗", ["麵糊沒貼到模具", "敲回去・用下火烤上色"]),
   card([m(4990, 3.5), m(4990, 25.0)], "表面深、裡面淺", ["蓋鋁箔紙擋掉上面的溫度"]),
   label([T - 1.6, T], "你烤過白頭嗎？")],
 "短9_敲回去": lambda m, T: [
   card([m(4985, 57.5), m(4985, 62.0)], "衝出模具", ["8～10 分鐘敲回去一次"]),
   card([m(4985, 176.7), m(4985, 187.5)], "頂多敲 3～4 次", ["定型後把顏色烤到位"]),
   label([T - 1.4, T], "第一次看到可麗露長這樣？")],
 "短10_切開": lambda m, T: [
   card([m(4997, 53.1), m(4997, 56.3)], "失敗的切面", ["實心", "或中間一個大洞"]),
   card([m(5005, 71.4), m(5005, 75.2)], "成功的切面", ["蜂巢組織・有氣孔是正常的"]),
   label([T - 1.4, T], "你喜歡脆的還是軟的？")],
 "短11_外面買的": lambda m, T: [
   card([m(5006, 20.2), m(5006, 26.1)], "剛出爐", ["外脆內軟・最好吃"]),
   card([m(5006, 35.7), m(5006, 41.0)], "放了一整天", ["皮一定會軟"]),
   card([m(5006, 42.7), m(5006, 48.2)], "保存", ["不能冷藏", "室溫或冷凍"]),
   label([T - 1.6, T], "你買過軟皮的可麗露嗎？")],
}
for f in sorted(glob.glob(f"{ROOT}/dessert/可麗露_短*_config.json")):
    key = os.path.basename(f)[4:-12]
    if key not in PLAN: continue
    cfg = json.load(open(f)); m, T = mapper(cfg)
    video = f"{cfg['out_dir']}/{cfg['subject']}.mp4"
    out = {"video": video, "out": video.replace(".mp4", "_疊圖.mp4"), "items": PLAN[key](m, T)}
    json.dump(out, open(f"{ROOT}/dessert/可麗露_工作檔/overlay_{key}.json", "w"), ensure_ascii=False, indent=1)
    print(key, round(T, 1), "秒", len(out["items"]), "層")

steps = json.load(open(f"{ROOT}/dessert/可麗露_工作檔/steps_index.json"))
cfg = json.load(open(f"{ROOT}/dessert/可麗露_短12_步驟_config.json")); m, T = mapper(cfg)
items = [{"type": "label", "t": [m(n0, s0), m(n1, e1)], "xy": [540, 230], "text": lab, "fs": 68}
         for lab, n0, s0, n1, e1 in steps]
items[-1]["t"][1] = T - 1.8
items.append(label([T - 1.6, T], "存起來，下次照著做"))
video = f"{cfg['out_dir']}/{cfg['subject']}.mp4"
json.dump({"video": video, "out": video.replace(".mp4", "_疊圖.mp4"), "items": items},
          open(f"{ROOT}/dessert/可麗露_工作檔/overlay_短12_步驟.json", "w"), ensure_ascii=False, indent=1)
print("短12_步驟", round(T, 1), "秒", len(items), "層")
