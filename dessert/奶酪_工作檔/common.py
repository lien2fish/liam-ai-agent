"""奶酪長片／短片共用：校正表、逐字稿切字幕、段落邊界對齊。"""
import json, re, os
import jieba
from opencc import OpenCC

ROOT = "/Users/lien/Downloads/Liam AI agent"
HERE = os.path.dirname(os.path.abspath(__file__))
cc = OpenCC("s2tw")
t2s = OpenCC("t2s")
jieba.setLogLevel(60)
for _w in ("红酒柜", "没有办法", "那时候", "巧克力房", "巧克力工厂", "五星级饭店", "拿去"):  # jieba 會切成「有红／酒柜」「没有／办法」
    jieba.add_word(_w)
GLUE_AFTER = set("很太也都就才再還更最你我他它")  # 這些字後面不切（「很／喜歡」「跑來我／這邊」）
GLUE_BEFORE = set("的了嗎呢啊吧喔啦耶")  # 這些字前面不切（「洗出來／的」）

FIX = [
    ("雞粒丁", "吉利丁"),
    ("基利丁", "吉利丁"),
    ("雞米丁", "吉利丁"),
    ("激勵的", "吉利丁"),
    ("吉利丁片一般來說分晶跟銀", "吉利丁片一般分金級跟銀級"),
    ("晶級", "金級"),
    ("大西地", "大溪地"),
    ("大CD", "大溪地"),
    ("香草劑", "香草籽"),
    ("香草只", "香草籽"),
    ("蔥頭籽", "香草籽"),
    ("香草夾", "香草莢"),
    ("沒酒", "沒救"),
    ("涼杯", "量杯"),
    ("空置", "控制"),
    ("吃乾拿進", "吃乾抹淨"),
    ("醬味", "降溫"),
    ("融質液晶", "融吉利丁"),
    ("脫膜", "脫模"),
]
DROP = re.compile(
    r"panna cotta|請不吝|訂閱|點贊|^嗯+$|^哦+~*$|^喔$|^對$|^好$|^呵+$|^哈+$|^啊!?$|超回答|^哎呦"
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
    "他是剛剛上述這麼多香草的始祖": "它是剛剛講的這些香草的始祖", "吼吼": None, "我跟廠商賣的": "我跟廠商買的",
    "這個是Pompona大花香草": ("這個是 Pompona 大花香草", ["Pompona"]),
    "這我等一下就讓": None, "那個panna大花這支": "那個 Pompona 大花這支", "這支": None, "好薇薇有什麼": None,
    "那個做給真的很重要很重要要求婚啊還是怎麼樣": "做給很重要很重要的人，要求婚啊",
    "斯괬順": None, "這個紙我們就先把它進鍋子裡": "這個籽我們就先把它放進鍋子裡",
    "這個配方結送給大家了": "這個配方就送給大家了", "所以這個牛奶跟鮮奶油250250": "所以牛奶跟鮮奶油250、250",
    "鮮奶油多會是": None, "所以一體500吉利丁3片": "所以液體500，吉利丁3片", "三片，那我已經把它對減了啦": "三片，我已經幫你對半減了",
    "然後500的8%是多少？40%": "500的8%是多少？40克",
    "全部攪拌均勻加熱對不對熱了以後把吉利丁融進去然後就關杯子": "全部攪拌均勻加熱，再把吉利丁融進去，然後就灌杯子",
    "可是它的奶酪其實對我來講它會有一個很失敗的地方是": "可是對我來講，這樣會有一個很失敗的地方",
    "我以為是那個不知名的堅持這樣": "我以為是什麼不知名的堅持", "我們買到煮好一定要降溫": "我們煮好一定要降溫",
    "我以前連做那個": None, "我以為你要說煮到手下去摸一套": "我以為你要說用手下去摸一下",
    "其實超過50度幾率一定都融化": "其實超過50度，吉利丁一定都融化", "那這邊的話呢": None, "還是它": None,
    "那手又不小心摸的時候": None, "那時候教我的時候怎麼沒有鎖定式？": None, "大家看清楚就是": None, "我": None,
    "老師不只是甜甜老師": "老師不只是甜點老師", "把整個滴幹": "把水整個滴乾", "那其實你摸的過程": None,
    "如果有記得就要再多泡一泡": None, "你這裡開火": None,
    "你超過幾度它的凝固力就已幾倍遞減": "超過以後，它的凝固力會倍數遞減",
    "它如果不然降過頭，是不是它還在量杯裡就硬掉": "如果降過頭，它還在量杯裡就硬掉",
    "但是溫度不要超過那種孵化，就沒救了": "但是溫度不要超過86度，超過就沒救了",
    "剩下的液體裡面直接沖下去，迅速的趕快先把它噴開": "倒進剩下的液體裡，趕快把它拌開",
    "像那個這麼大的一個是冰的，它不會直接立馬結塊": "這一大鍋是冰的，它不會立馬結塊嗎？",
    "所以我這邊其實沖完它的溫度，加上我們剛剛在那邊慢慢來滴曬，其實這鍋液體溫度一定也有稍微上升": "沖完再加上剛剛慢慢滴乾，這鍋液體溫度也有稍微上升",
    "我現在比較懶喔，我就直接灌一灌就靜靜一下": "我現在比較懶，就直接灌",
    "不然它會...": None, "圍一波就會回來吧": "微波一下就會回來吧？", "一點點": None,
    "那但是我如果說我們像我自己以前是做巧克力的": "像我自己以前是做巧克力的", "哈哈對啊": None,
    "他就每天都在那邊跑來我這邊亂跑來我這邊偷吃巧克力": "他每天都跑來我這邊偷吃巧克力",
    "那個現在一公斤到一千多塊": "現在一公斤要一千多塊", "冷藏三天": None,
    "這個冷藏會要冷藏多久的時間？": "這個要冷藏多久？",
    "你等於是有點微微微阻的破壞它的表面": "等於是微微破壞它的表面",
    "第一個它有鮮奶油，鮮奶油是油脂嗎": "第一個它有鮮奶油，鮮奶油是油脂",
    "因為自助性的就看起來會吃起來比較像果凍": "因為植物性的吃起來比較像果凍",
    "那我們做就是，它兩個會有差別嗎？": "這兩個會有差別嗎？", "我們": None, "你在灌": None,
    "這個頻道之後轉直播": "這個頻道之後轉吃播",
    "但是我們側邊你還是可以看得到有一些香草籽是漂浮在半空中有沒有": "側邊還是看得到，有些香草籽漂浮在半空中", "吃很多的吃膩了": "吃很多，吃膩了",
    "所以我剛，我沒有跟大家講說什麼幾克幾克多少": "所以我沒有跟大家講幾克幾克",
    "糖八趴這樣子": ("糖8%這樣子", ["8%"]), "一千對六片": ("一千對六片", ["一千對六片"]),
    "還有跟大家講香草絕對不要放冰箱": ("還有，香草絕對不要放冰箱", ["不要放冰箱"]),
    "其實你香草放冰箱是錯誤的，這樣會導致它加速老化，然後你香草很容易就硬掉": "香草放冰箱是錯誤的，會加速老化，很容易就硬掉",
}
EXTRA = [  # 音量太小被濾掉、但非有不可的句子
    (5303, 207.05, 207.55, "不行", []),
    (5319, 65.5, 67.5, "我們的配方做法", []),
    # 5307 原逐字稿是亂碼（「斯괬順」），單獨重轉後補上；時間是 Whisper 句級時間碼
    (5307, 8.1, 12.9, "如果你是乾淨的香草，絕對不要碰到水", []),
    (5307, 13.0, 15.0, "我們把它翻開來", []),
    (5307, 16.0, 18.0, "翻開來之後", []),
    (5307, 18.0, 20.0, "用我們的刀背", []),
    (5307, 20.0, 22.0, "用力刮", ["用力刮"]),
    (5307, 24.0, 26.0, "哇賽，這刮太乾淨了吧", []),
    (5307, 26.0, 27.9, "這個就是我們的香草籽", ["香草籽"]),
]
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


NOSNAP = {5307}  # 逐字稿是亂碼，字的時間碼不可信


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


