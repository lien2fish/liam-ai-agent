"""布丁長片／短片共用：校正表、逐字稿切字幕、段落邊界對齊。"""
import json, re, os
import jieba
from opencc import OpenCC

ROOT = "/Users/lien/Downloads/Liam AI agent"
HERE = os.path.dirname(os.path.abspath(__file__))
cc = OpenCC("s2tw")
t2s = OpenCC("t2s")
jieba.setLogLevel(60)
for _w in ("沒有辦法", "那時候", "大同電鍋", "蒸汽烤箱", "保鮮膜", "焦糖", "翻砂", "房貸", "抽油煙機"):
    jieba.add_word(_w)
GLUE_AFTER = set("很太也都就才再還更最你我他它")  # 這些字後面不切（「很／喜歡」「跑來我／這邊」）
GLUE_BEFORE = set("的了嗎呢啊吧喔啦耶")  # 這些字前面不切（「洗出來／的」）

FIX = [
    ("【阿神】", ""),
    ("大容電鍋", "大同電鍋"),
    ("大同顛顧", "大同電鍋"),
    ("蛋黃鍋", "電鍋"),
    ("翻沙", "翻砂"),
    ("脫膜", "脫模"),
    ("Oak One", "Opus One"),
    ("剪指", "減脂"),
    ("小濃雞蛋", "雞蛋"),
    ("新鮮來潮", "心血來潮"),
    ("（", "，"),
    ("Baker店", "麵包店"),
    ("OakOne", "Opus One"),
    ("隻有", "只有"),
    ("臺", "台"),
    ("濃鬱", "濃郁"),
    ("結束這段錄", "結束這段錄影"),
]
DROP = re.compile(
    r"請不吝|訂閱|點贊|^嗯+$|^哦+~*$|^喔~*$|^對$|^好$|^呵+$|^哈+$|^啊!?$|^OK$|^哎$|^對啊$|^過分$|^可憐$|看他響|值得高的那種|喝很多蒸汽|^對阿$|^稍微$"
)
NUM = re.compile(
    r"\d[\d,]*(?:\.\d+)?\s*(?:°C|%|塊|元|克|分鐘|小時|天|度|顆|片|公分|根|杯)?"
)


def fix(t):
    t = cc.convert(t)
    for a, b in FIX:
        t = t.replace(a, b)
    return t.replace(",", "，").replace("?", "？").replace("﹔", "，").strip(" ，。")


OVR = {  # 校對：整句改寫；None＝聽不清楚或不上字幕；(文字, [高光]) 可指定高光
    "對啊，咳咳，布丁喔算是，我人生當中一個很重要的東西啦": "對啊，布丁算是我人生當中一個很重要的東西啦",
    "喔嗎？你會讓你有劉為叔的進帳這樣？": "會讓你有六位數的進帳嗎？",
    "你那天一天，那時候一天最高賣到幾顆布丁": "那時候一天最高賣到幾顆布丁？",
    "一次做最多大概200杯吧": ("一次做最多大概200杯吧", ["200杯"]),
    "1杯60塊": ("一杯60塊", ["60塊"]), "1杯60": None, "還沒辦法": None,
    "再少的錢你都一定要想辦法賺": ("再少的錢你都一定要想辦法賺", []),
    "不然房貸利息就繳不出來": ("不然房貸利息就繳不出來", ["房貸利息"]),
    "我們稱作為翻砂啦": ("我們稱作翻砂", ["翻砂"]),
    "煮焦糖的一個重點就是你不要去攪拌它": ("煮焦糖的重點，就是不要去攪拌它", ["不要去攪拌"]),
    "我還沒看過他響 看他響是不是": None, "這個敏感不能亂講": "這個敏感，不能亂講", "開始站南北": None,
    "加水後會變黑": None, "哈哈哈": None, "哈哈哈哈": None,
    "在你覺得很完美的顏色": "在你覺得很完美的顏色", "前一秒就要關火": ("前一秒就要關火", ["前一秒"]),
    "加適量的水，稍微醃過": "加適量的水，稍微淹過",
    "那後面去加入的水大概就是1‧3‧1‧到1‧5‧1‧": ("後面加的水，大概是糖的三分之一到五分之一", ["三分之一到五分之一"]),
    "你如果今天糖是煮100克，你後面加大概就是2、30克就好了": ("糖煮100克，後面加20、30克就好", ["20、30克"]),
    "你如果今天是一大鍋你直接倒下去它會炸到天花板": ("如果是一大鍋，直接倒下去會炸到天花板", ["炸到天花板"]),
    "會很開心喔": None, "這麼一點": None,
    "那我們今天要做布丁的話，有它的成分嗎？": "今天做布丁，有什麼配方嗎？",
    "我們布丁你就大概1000": None, "值得高的那種 對對對": None,
    "一罐是多大罐？ 936": "一罐是多大罐？936", "其實你就算1000啦": ("就算1000啦", ["1000"]),
    "大概一罐的牛奶對6顆的雞蛋就好了": ("一罐牛奶對6顆雞蛋", ["6顆雞蛋"]),
    "糖的話大概加個100克": ("糖大概加100克", ["100克"]),
    "跟大家說": None, "這邊比較拍到好亂": "這邊拍到好亂",
    "我們市面上也有很多，比如說在一些麵包店或是飯店，都會看到有布丁的這個甜點": "麵包店、飯店都會看到布丁",
    "那你有辦法一看就知道這好不好吃嗎？": "你一看就知道好不好吃嗎？",
    "咦？新不新鮮？怎麼看？": "新不新鮮？怎麼看？",
    "淺點看起來": None, "新不新鮮嗎": None, "那剛剛你說的是": None,
    "有時候表面可能會有點皺皺凹進去": ("表面可能會有點皺皺、凹進去", ["皺皺、凹進去"]),
    "因為布丁放一段時間它是會脫水的": ("因為布丁放一段時間會脫水", ["脫水"]),
    "或是買Opus One來燉紅酒燉牛肉這樣": ("或是買 Opus One 來燉紅酒燉牛肉", ["Opus One"]),
    "布丁看到": None, "到底是怎么用的可以把炉子用成这个": "到底是怎麼用的，可以把爐子用成這樣",
    "到底是怎麼用的可以把爐子用成這個": "到底是怎麼用的，可以把爐子用成這樣",
    "我都不知道": None, "等一下你說減脂到泡芙裡面": "等一下，你說夾到泡芙裡面",
    "減脂有多痛苦，什麼東西都不能吃": "減脂有多痛苦，什麼都不能吃",
    "泡芙不是用罐還是要加進去的嗎": "泡芙不是用灌的嗎？", "剖開來，罐一堆餡": "剖開來，灌一堆餡",
    "敲一顆固定上去": "放一顆布丁上去", "這是放別人嗎？": None,
    "你剛才燙下去然後三度灼傷，那個就是過頭了": "你插下去三度灼傷，那個就是過頭了",
    "這樣不會不會生嗎？": "這樣不會不衛生嗎？",
    "有些蛋白甚至可以一坨加起來": "有些蛋白甚至可以一坨夾起來",
    "牛奶溫度大概六七十度": ("牛奶溫度大概六、七十度", ["六、七十度"]),
    "那我的習慣是過濾兩次啦": ("我的習慣是過濾兩次", ["兩次"]),
    "三色給你吃": None,
    "這樣就有點過份了，還是要稍微拿得出上等檯面的東西": "這樣就有點過分了，還是要拿得上檯面",
    "然後又有很多的耗手": "而且很耗損",
    "所以我們用保鮮膜": ("所以我們用保鮮膜", ["保鮮膜"]),
    "用保鮮膜把它完全貼面": ("用保鮮膜完全貼面", ["保鮮膜"]),
    "那等於是泡進去的意思": None, "你是不是常一首": None, "什麼時候": None,
    "真的硬要講，頂多大同電鍋": "真的硬要講，頂多大同電鍋",
    "那你就不用再談自己加水了": "那你就不用再自己加水了",
    "它不是喝很多蒸汽嗎？": None,
    "我們一般脫模很多人會講說倒過來搖搖搖搖不下來": "很多人脫模，倒過來搖半天都搖不下來",
    "所以我們做的事情拿緊鞋邊邊調一下": "所以我們把邊邊壓一下",
    "邊邊調一下讓空氣進去你就會很好脫了": ("邊邊壓一下讓空氣進去，就很好脫了", ["空氣進去"]),
    "不過現在就可以吃了，不准發": None, "該是真的嗎": None, "不會，這就是...": None,
    "該運動了啦。幹什麼東西。雞碎了": "該運動了啦", "對。沒水準": None,
    "我們上次做奶酪就是做布丁，這兩次做的都太簡單了": "上次做奶酪、這次做布丁，這兩次都太簡單了",
    "我覺得下次可以在我﹗下次可以在我桃園家做": "下次可以在我桃園家做",
    "有，讓大家留言，想要看下次做什麼好了": ("讓大家留言，想看下次做什麼", ["留言"]),
    "就像你在練習做那個紅酒燉牛肉，就用你買的那個日本A5和牛來用": ("就像你在練習做紅酒燉牛肉，就用你買的日本A5和牛", ["A5和牛"]),
    "或是買Opus One來燉紅酒燉牛肉這樣": ("或是買 Opus One 來燉紅酒燉牛肉", ["Opus One"]),
    "蛤？": None, "你說什麼？": None,
}
EXTRA = []  # 音量太小被濾掉、但非有不可的句子
MAXC = 26  # 16:9 一行約 27 個全形字；超過就在逗號切成多條


def split(c, maxc=MAXC):
    n, s, e, t, hl = c
    if len(t) <= maxc or "，" not in t:
        return [c]
    parts, cur = [], ""
    for p in t.split("，"):
        if cur and len(cur) + 1 + len(p) > maxc:
            parts.append(cur)
            cur = p
        else:
            cur = f"{cur}，{p}" if cur else p
    parts.append(cur)
    if any(not any(h in p for p in parts) for h in hl) or (e - s) * min(len(p) for p in parts) / len(t) < 0.6:
        return [c]  # 會遺失高光或切出太短的字幕就不切
    out, t0, tot = [], s, sum(len(p) for p in parts)
    for p in parts:
        t1 = t0 + (e - s) * len(p) / tot
        out.append([n, round(t0, 2), round(t1, 2), p, [h for h in hl if h in p]])
        t0 = t1
    return out


def word_split(n, ws, t, a, b, maxc, hl=()):
    """短片用：超過 maxc 的字幕切成依序出現的幾條，切在詞邊界，避免 wrap_lines 把詞從中間折斷（「沒／有」「甜／點」）。
    在最終字幕文字上逐字找切點（Whisper 常把幾個字黏成一個 token，只在 token 之間切會切出「紅／酒櫃」）：
    逗號後 0 分、jieba 詞邊界 1 分、詞中間 6 分、切開高光詞 100 分；條數最少優先，再來代價最低、最長那條最短。
    時間按字的位置從逐字稿內插。"""
    if len(t) <= maxc:
        return None
    s0, s1 = max(ws[0]["s"], a + 0.02), min(ws[-1]["e"], b - 0.02)
    # 逐字時間：每個 token 的時間平均分給它的字，再按比例對到最終文字（校正表可能改變字數）
    ct = []
    for w in ws:
        k = max(len(w["w"]), 1)
        ct += [w["s"] + (w["e"] - w["s"]) * i / k for i in range(k)]
    at = lambda i: max(s0, min(s1, ct[min(int(i * len(ct) / len(t)), len(ct) - 1)] if i < len(t) else s1))
    bounds, p = set(), 0
    for tok in jieba.lcut(t2s.convert(t)):
        p += len(tok)
        bounds.add(p)
    inside_hl = set()
    for h in hl:
        q = t.find(h)
        while q >= 0:
            inside_hl.update(range(q + 1, q + len(h)))
            q = t.find(h, q + 1)
    PUN = "，、。！？"
    def cost(k):
        if k in inside_hl:
            return 100
        if t[k - 1] in PUN:
            return 0
        glue = 4 if (t[k - 1] in GLUE_AFTER or t[k] in GLUE_BEFORE) else 0
        return (1 if k in bounds else 6) + glue
    L = lambda i, j: len(t[i:j].strip(PUN + " "))
    N = len(t)
    dp = [(0, 0, 0, [])] + [None] * N
    for j in range(1, N + 1):
        if j < N and t[j - 1] not in PUN and j not in bounds and j not in range(N):
            continue
        for i in range(j):
            if dp[i] is None or L(i, j) > maxc:
                continue
            c = dp[i][1] + (cost(i) if i else 0)
            cand = (dp[i][0] + 1, c, max(dp[i][2], L(i, j)), dp[i][3] + [i])
            if dp[j] is None or cand[:3] < dp[j][:3]:
                dp[j] = cand
    if dp[N] is None or dp[N][0] < 2:
        return None
    cuts = dp[N][3] + [N]
    out = []
    for x, y in zip(cuts, cuts[1:]):
        tt = t[x:y].strip(PUN + " ")
        cs, ce = at(x), at(y) if y < N else s1
        if ce - cs < 0.5:
            return None
        h = [k for k in hl if k in tt] or [m.group().strip() for m in NUM.finditer(tt) if re.search(r"\d", m.group())][:2]
        out.append([n, round(cs, 2), round(ce, 2), tt, h])
    return out


def cues_for(n, a, b, maxc=MAXC):
    out = []
    OV = {fix(k): v for k, v in OVR.items()}
    for s in json.load(open(f"{HERE}/transcripts/IMG_{n}.json")):
        if s["end"] <= a or s["start"] >= b or s["db"] < -50:
            continue
        ws = [w for w in s["words"] if a - 0.05 <= w["s"] < b]
        if not ws:
            continue
        t = fix("".join(w["w"] for w in ws))
        hl = None
        if t in OV:
            t = OV[t]
            if not t:
                continue
            if isinstance(t, tuple):
                t, hl = t
        if DROP.search(t):
            continue
        cs, ce = max(ws[0]["s"], a + 0.02), min(ws[-1]["e"], b - 0.02)
        if ce - cs < 0.3:
            continue
        if hl is None:
            hl = [m.group().strip() for m in NUM.finditer(t) if re.search(r"\d", m.group())][:2]
        ws_cut = word_split(n, ws, t, a, b, maxc, hl) if maxc < MAXC else None
        if ws_cut:
            out += ws_cut
            continue
        out += split([n, round(cs, 2), round(ce, 2), t, hl], maxc)
    out += [list(x) for x in EXTRA if x[0] == n and a <= x[1] and x[2] <= b]
    return sorted(out, key=lambda c: c[1])


NOSNAP = {5577, 5592}  # 逐字稿有幻覺亂碼，字的時間碼不可信


def snap(n, a, b):
    """段落邊界切到字中間時：字大半在段內就整個收進來，大半在段外就整個切掉。
    切在字的邊界上、不留緩衝——相鄰字首尾相接，多留 0.03 秒會切進隔壁那個字。"""
    if n in NOSNAP:
        return a, b
    ws = [w for s in json.load(open(f"{HERE}/transcripts/IMG_{n}.json")) for w in s["words"]]
    for w in ws:
        if w["s"] < a < w["e"]:
            a = w["s"] if w["e"] - a >= a - w["s"] else w["e"]
        if w["s"] < b < w["e"]:
            b = w["e"] if b - w["s"] >= w["e"] - b else w["s"]
    return round(a, 2), round(b, 2)


