"""把 gt-01（GTA6 首日 37.9 億美元：一套 2,320 元，你的錢流去哪？）的事實寫進 facts.json；重跑會覆蓋同 id。查詢日期 2026-11-22。"""

import json
import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "facts.json"

K8 = "Take-Two 8-K Exhibit 99.1（2026-11-20）〈Grand Theft Auto VI Shatters Entertainment Box Office Records with $3.79 Billion in Day One Retail Sales〉"
K8_U = "https://www.sec.gov/Archives/edgar/data/0000946581/000162828026075217/exhibit9918k.htm"
FOXB = "Fox Business 2026-11-21〈GTA VI smashes records with $3.79 billion in first 24 hours, Rockstar says〉"
FOXB_U = "https://www.foxbusiness.com/entertainment/grand-theft-auto-vi-shatters-entertainment-records-staggering-3-79b-debut"
ER = "Take-Two 8-K 第二季（FY27 Q2）財報新聞稿（2026-11-09）"
ER_U = "https://www.sec.gov/Archives/edgar/data/946581/000162828026072175/ttwo2q27earningsrelease.htm"
Q10 = "Take-Two 10-Q（截至 2026-09-30，2026-11-09 申報）"
Q10_U = "https://www.sec.gov/Archives/edgar/data/946581/000162828026072254/ttwo-20260930.htm"
YF = "Yahoo Finance 2026-11〈Take-Two Shares Rise Over 3% After Quarterly Results as GTA VI November 19 Release Confirmed〉"
YF_U = "https://finance.yahoo.com/markets/stocks/articles/two-shares-rise-over-3-113921042.html"
PR = "Take-Two 新聞稿 2026-06-24〈Rockstar Games Announces Pre-Orders for Grand Theft Auto VI〉"
PR_U = "https://www.take2games.com/ir/news/rockstar-games-announces-pre-orders-grand-theft-auto-vi"
DT = "Digital Trends 2026-06〈GTA VI finally gets a price tag and a no-disc rule for physical edition〉"
DT_U = "https://www.digitaltrends.com/gaming/gta-vi-finally-gets-a-price-tag-and-a-no-disc-rule-for-physical-edition"
PST = "PlayStation Store 台灣 搜尋〈Grand Theft Auto VI〉（2026-11-22 查詢；標準版 EP1004-PPSA01547_00-GTAVISTANDARD001、終極版 GTAVIULTIMATE001）"
PST_U = "https://store.playstation.com/zh-hant-tw/search/Grand%20Theft%20Auto%20VI"
C3C = "Cool3c 2026-06〈GTA 6數位版、實體版皆開放預購 普版2320元、終極版2900元〉"
C3C_U = "https://www.cool3c.com/article/252120"
BOT = "臺灣銀行 2026-11-20 牌告匯率（美金即期買入 32.865、賣出 33.015，中價 32.94；2026-11-22 查詢，非營業時間沿用 11-20 牌價）"
BOT_U = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
MOL = "勞動部新聞稿 2025-12-26〈2026年勞動新制上路，守護勞工不停歇！〉"
MOL_U = "https://www.mol.gov.tw/1607/1632/1633/87257/"
UDN = "經濟日報〈最低工資漲至29,500元 調幅3.1% 時薪調升至196元 明年元月上路〉"
UDN_U = "https://money.udn.com/money/amp/story/12926/9032664"
USA = "USA.gov〈Minimum wage〉"
USA_U = "https://www.usa.gov/minimum-wage"
USC = "美國法典 29 U.S.C. §206(a)(1)(C)（Cornell LII）"
USC_U = "https://www.law.cornell.edu/uscode/text/29/206"
K13 = "Take-Two 8-K Exhibit 99.1（2013-09-20）〈Grand Theft Auto V Worldwide Sales Surpass $1 Billion In First Three Days〉"
K13_U = "https://www.sec.gov/Archives/edgar/data/946581/000110465913071387/a13-21085_1ex99d1.htm"
GS13 = "GameSpot 2013-09-20〈Grand Theft Auto V sales reach $1 billion in three days〉"
GS13_U = "https://gamespot.com/articles/grand-theft-auto-v-sales-reach-1-billion-in-three-days/1100-6414762/"
DIS = "華特迪士尼公司新聞稿 2019-04-28〈Marvel Studios' 'Avengers: Endgame' Makes History with $1.2 Billion Global Debut〉"
DIS_U = "https://thewaltdisneycompany.com/marvel-studios-avengers-endgame-makes-history-with-1-2-billion-global-debut/"
CBS = "CBS News 2019-04〈'Avengers: Endgame' obliterates box office records with $1.2 billion opening〉"
CBS_U = "https://www.cbsnews.com/amp/news/avengers-endgame-box-office-1-2-billion-opening-obliterates-records"
BLS = "美國勞工統計局 CPI-U 全美城市、未季調（CUUR0000SA0）API 查詢 2026-11-22"
BLS_U = "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0"
FRED = "聖路易聯準銀行 FRED〈CPIAUCNS〉"
FRED_U = "https://fred.stlouisfed.org/series/CPIAUCNS"
LAW = "通訊交易解除權合理例外情事適用準則 第 2 條（全國法規資料庫 J0170012）"
LAW_U = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=J0170012"
EY = "行政院消費者保護處 函釋（例外從嚴、個案認定；告知義務為要件）"
EY_U = (
    "https://www.ey.gov.tw/Page/8F51FEE53AB45EA9/36663b43-67df-4bdb-b8f7-d6a649b95223"
)
LP = "法律百科〈網路購物七天鑑賞期〉問答"
LP_U = "https://www.legis-pedia.com/QA/3090/download"


def s(name, url, quote, official=False):
    return {"name": name, "url": url, "official": official, "quote": quote}


F = {
    "GT01": {
        "claim": "Take-Two 2026-11-20 公告：GTA6 首日零售額 37.9 億美元（day one retail sales，公司估計、全球、計到 11 月 19 日當天結束），自稱跨所有娛樂媒介的新紀錄；這是玩家花掉的錢，不是 Take-Two 認列的營收",
        "tokens": ["2026", "11", "20", "19", "3.79", "37.9", "億", "一"],
        "sources": [
            s(
                K8,
                K8_U,
                "Grand Theft Auto VI day one retail sales* reached $3.79 billion, setting a new record for entertainment across any medium … *based on company estimates through end of day November 19th worldwide",
                True,
            ),
            s(
                FOXB,
                FOXB_U,
                "an estimated $3.79 billion in first-day sales … The estimated worldwide sales are based on company figures through the end of Nov. 19 … a video game's first-day retail sales are different revenue measures",
            ),
        ],
    },
    "GT02": {
        "claim": "GTA6 上市前就賣出 3,250 萬套，創全平台紀錄",
        "tokens": ["3250", "3,250", "32.5", "萬"],
        "sources": [
            s(
                K8,
                K8_U,
                "Grand Theft Auto VI sold 32.5 million units pre-release, a new record across all platforms",
                True,
            ),
            s(
                FOXB,
                FOXB_U,
                "Rockstar also said the game sold 32.5 million units before its release, a record across all platforms.",
            ),
        ],
    },
    "GT03": {
        "claim": "對照：Take-Two 11-09（GTA6 上市前 10 天）給出的本季（2026 年 10～12 月）Net Bookings 預估是 33.5～35 億美元；Net Bookings 是公司數位賣出或出貨給通路的淨額——玩家一天花的 37.9 億，比公司預估整季入帳還多",
        "tokens": [
            "11",
            "9",
            "10",
            "12",
            "2026",
            "3,350",
            "3350",
            "3,500",
            "3500",
            "33.5",
            "35",
            "億",
            "37.9",
        ],
        "sources": [
            s(
                ER,
                ER_U,
                "Three Months Ending December 31, 2026 … Operational metric Net Bookings $3,350 to $3,500 … The launch of Grand Theft Auto VI is ten days away",
                True,
            ),
            s(
                Q10,
                Q10_U,
                "Net Bookings is defined as the net amount of products and services sold digitally or sold-in physically during the period",
                True,
            ),
            s(
                YF,
                YF_U,
                "projected net bookings between $3.35 billion and $3.50 billion for the quarter",
            ),
        ],
    },
    "GT04": {
        "claim": "美國售價：標準版 79.99 美元、終極版 99.99 美元；盒裝實體版盒內只有下載序號、沒有光碟；2026-06-25 開放預購、11-19 上市（PS5、Xbox Series X|S）",
        "tokens": ["79.99", "99.99", "80", "100", "2026", "6", "25", "11", "19", "5"],
        "sources": [
            s(
                PR,
                PR_U,
                "Launching November 19, 2026, for the PlayStation® 5 … and Xbox Series X|S … for $79.99 … Ultimate Edition … will be available for $99.99 … The physical version of Grand Theft Auto VI, containing a download code inside the box",
                True,
            ),
            s(
                DT,
                DT_U,
                "GTA VI finally gets a price tag and a no disc rule for physical edition",
            ),
        ],
    },
    "GT05": {
        "claim": "台灣 PlayStation Store 售價：GTA6 標準版 2,320 元、終極版 2,900 元（2026-11-22 查詢）",
        "tokens": ["2320", "2,320", "2900", "2,900", "2026", "11", "22"],
        "sources": [
            s(
                PST,
                PST_U,
                "Grand Theft Auto VI … PS5 遊戲組合包 NT$2,320 … Grand Theft Auto VI：終極版 … NT$2,900",
                True,
            ),
            s(C3C, C3C_U, "普版2320元、終極版2900元"),
        ],
    },
    "GT06": {
        "claim": "以臺銀 2026-11-20 美元即期中價 32.94 換算：37.9 億美元約 1,248 億台幣；美國標準版 79.99 美元約 2,635 元、終極版 99.99 美元約 3,294 元（美國標價未含銷售稅）——台灣標價 2,320、2,900 元反而比較低",
        "tokens": [
            "2026",
            "11",
            "20",
            "32.94",
            "32.865",
            "33.015",
            "1248",
            "1,248",
            "億",
            "79.99",
            "2635",
            "2,635",
            "99.99",
            "3294",
            "3,294",
            "2320",
            "2,320",
            "2900",
            "2,900",
            "37.9",
        ],
        "sources": [
            s(
                BOT,
                BOT_U,
                "美金 (USD) 即期匯率 本行買入 32.865 本行賣出 33.015（牌告匯率 2026/11/20）",
                True,
            ),
            s(PR, PR_U, "for $79.99 … will be available for $99.99", True),
            s(K8, K8_U, "day one retail sales* reached $3.79 billion", True),
        ],
    },
    "GT07": {
        "claim": "台灣 2026 年最低時薪 196 元（月薪 29,500 元）；2,320 元÷196 元≈11.8 小時；終極版 2,900 元÷196 元≈14.8 小時",
        "tokens": ["2026", "196", "29500", "29,500", "2320", "2,320", "11.8", "12", "2900", "2,900", "14.8"],
        "sources": [
            s(
                MOL,
                MOL_U,
                "自2026年起，每月最低工資調升為新臺幣（下同）29,500元，每小時最低工資調升為196元",
                True,
            ),
            s(UDN, UDN_U, "最低工資漲至29,500元 調幅3.1% 時薪調升至196元 明年元月上路"),
        ],
    },
    "GT08": {
        "claim": "美國聯邦最低時薪 7.25 美元；79.99 美元÷7.25≈11.0 小時；終極版 99.99 美元÷7.25≈13.8 小時（各州可訂更高）",
        "tokens": ["7.25", "79.99", "11.0", "11", "99.99", "13.8"],
        "sources": [
            s(USA, USA_U, "The federal minimum wage is $7.25 per hour.", True),
            s(
                USC,
                USC_U,
                "(C) $7.25 an hour, beginning 24 months after that 60th day",
                True,
            ),
        ],
    },
    "GT09": {
        "claim": "2013 年 GTA V 上市前三天全球零售額超過 10 億美元（Take-Two 估計）；GTA6 首日 37.9 億美元約是它的 3.8 倍",
        "tokens": ["2013", "10", "億", "3", "三", "37.9", "3.8"],
        "sources": [
            s(
                K13,
                K13_U,
                "Grand Theft Auto V … has achieved worldwide retail sales of more than $1 billion during its first three days on sale, according to Company estimates",
                True,
            ),
            s(GS13, GS13_U, "Grand Theft Auto V sales reach $1 billion in three days"),
        ],
    },
    "GT10": {
        "claim": "電影全球首週末票房紀錄：《復仇者聯盟：終局之戰》2019 年 12.09 億美元（迪士尼估計）；GTA6 首日 37.9 億美元約是 3.1 倍（兩者計算口徑不同，只當比例尺）",
        "tokens": ["2019", "12.09", "12", "億", "1.209", "3.1", "37.9"],
        "sources": [
            s(DIS, DIS_U, "Avengers: Endgame has shattered records with an unprecedented estimated global debut of $1.209 billion", True),
            s(
                CBS,
                CBS_U,
                "'Avengers: Endgame' obliterates box office records with $1.2 billion opening",
            ),
        ],
    },
    "GT11": {
        "claim": "開發成本：Take-Two 2026-09-30 帳上資本化的自製軟體開發成本 25.056 億美元（流動 0.651＋非流動 24.405），是全公司合計、沒有拆出 GTA6；GTA6 單一開發成本官方沒有公布，無從證實",
        "tokens": [
            "2026",
            "9",
            "30",
            "25.056",
            "25",
            "億",
            "65.1",
            "2,440.5",
            "2440.5",
            "2505.6",
            "6",
        ],
        "sources": [
            s(
                Q10,
                Q10_U,
                "Software development costs, internally developed $ 65.1 $ 2,440.5",
                True,
            ),
            s(
                ER,
                ER_U,
                "Software development costs and licenses 82.4 … Software development costs and licenses, net of current portion 2,494.9",
                True,
            ),
        ],
    },
    "GT12": {
        "claim": "美國 CPI-U（未季調）2013 年 9 月 234.149、2026 年 10 月 337.511，13 年間物價約漲 44%（×1.441）",
        "tokens": [
            "2013",
            "9",
            "234.149",
            "2026",
            "10",
            "337.511",
            "44",
            "1.441",
            "13",
        ],
        "sources": [
            s(
                BLS,
                BLS_U,
                "CUUR0000SA0 2013 September 234.149 … 2026 October 337.511",
                True,
            ),
            s(
                FRED,
                FRED_U,
                "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average (CPIAUCNS)",
            ),
        ],
    },
    "GT13": {
        "claim": "網路買遊戲的 7 天解除權：通訊交易原則上可在 7 天內解除；例外包括「經消費者拆封的影音商品或電腦軟體」（準則第 2 條第 4 款）和「非以有形媒介提供的數位內容，經消費者事先同意始提供」（第 5 款），而且業者要事先清楚告知；消保處說例外從嚴、依實際商品個別認定。盒裝只附序號算哪一款，查無官方明文",
        "tokens": ["7", "七", "2", "4", "5", "19"],
        "sources": [
            s(
                LAW,
                LAW_U,
                "四、經消費者拆封之影音商品或電腦軟體。五、非以有形媒介提供之數位內容或一經提供即為完成之線上服務，經消費者事先同意始提供。",
                True,
            ),
            s(
                EY,
                EY_U,
                "消費者於通訊交易，原則上仍享有7日解除權，上開準則之適用必須在合理之大前提下，而且是屬於例外之情況，在適用上及解釋上均採例外從嚴之原則。商品或服務是否屬於上開準則規範之情形，並非以企業經營者單方之主張為據 … 就個案加以認定 … 第2條序文將告知義務列為合理例外情事之要件，企業經營者如未履行告知義務，消費者仍可主張適用消保法第19條第1項規定之7日解除權",
                True,
            ),
            s(LP, LP_U, "通訊交易解除權合理例外情事適用準則"),
        ],
    },
    "GT14": {
        "claim": "Take-Two 2026 年 7～9 月（GTA6 上市前那一季）的 GAAP 營收有 81% 來自玩家持續消費（recurrent consumer spending：虛擬貨幣、追加內容、遊戲內購買、遊戲內廣告）；10-Q 附註 2：持續消費 12.102 億美元／總營收 14.970 億美元",
        "tokens": ["2026", "7", "9", "81", "12.102", "1210.2", "1,210.2", "14.970", "1497.0", "1,497.0", "6"],
        "sources": [
            s(
                "Take-Two 8-K 第二季（FY27 Q2）財報新聞稿（2026-11-09）",
                "https://www.sec.gov/Archives/edgar/data/946581/000162828026072175/ttwo2q27earningsrelease.htm",
                "Recurrent consumer spending decreased 5% and accounted for 81% of total GAAP net revenue.",
                True,
            ),
            s(
                "Take-Two 10-Q（截至 2026-09-30，2026-11-09 申報）附註 2 Net revenue by content",
                "https://www.sec.gov/Archives/edgar/data/946581/000162828026072254/ttwo-20260930.htm",
                "Recurrent consumer spending $ 1,210.2 … Total net revenue $ 1,497.0；RCS includes revenue from virtual currency, add-on content, in-game purchases, and in-game advertising.",
                True,
            ),
        ],
    },
    "GT15": {
        "claim": "台灣 PlayStation Store 取消政策：遊戲與追加內容購買日起 14 天內可取消退款，前提是尚未開始下載或串流；已開始下載或串流的不能退，除非有瑕疵；預購已開始下載主要部分也不能退；電子錢包加值不可退款。服務條款：除取消政策或適用法律另有規定，購買內容不可退款",
        "tokens": ["14", "十四"],
        "sources": [
            s(
                "PlayStation Store 取消政策（台灣，2026-11-22 查詢）",
                "https://www.playstation.com/zh-hant-tw/legal/playstation-store-cancellation-policy/",
                "您可以在購買日起14天內取消遊戲或遊戲追加內容購買並取得退款，前提是您尚未開始下載或串流該內容。／您已開始下載或串流的遊戲或追加內容不符合退款資格，除非其有瑕疵。／若您已開始下載或串流預購的主要部分，則無法取得退款，除非該商品有瑕疵。／您無法取消PlayStation™Store電子錢包加值。",
                True,
            ),
            s(
                "PlayStation Network 服務條款 第20版（2026年4月）第 8.5 條",
                "https://www.playstation.com/zh-hant-tw/legal/psn-terms-of-service/",
                "除非當時生效的PS Store取消政策…另有説明或適用法律另外規定，所購買的內容或服務均不可退款或轉讓",
                True,
            ),
        ],
    },
    "GT16": {
        "claim": "GTA6 的舞台是虛構的雷歐尼達州（Leonida）與罪惡城（Vice City）；Rockstar 官網標語「Vice City, USA. The darkest side of the sunniest place in America.」；主角是 Jason（Jason Duval）與 Lucia（Lucia Caminos）兩人",
        "tokens": ["6", "兩", "2"],
        "sources": [
            s(
                "Rockstar Games 官網〈Grand Theft Auto VI〉（2026-11-22 查詢）",
                "https://www.rockstargames.com/VI",
                "Welcome to Leonida／Vice City, USA. The darkest side of the sunniest place in America.／Jason and Lucia have always known the deck is stacked against them… a criminal conspiracy stretching across the state of Leonida",
                True,
            ),
            s(
                "Rockstar Games 官網〈Only in Leonida〉",
                "https://www.rockstargames.com/VI/only-in-leonida",
                "Home to the neon-soaked streets of Vice City and beyond.／Jason wants an easy life, but things just keep getting harder.／Lucia’s father taught her to fight as soon as she could walk.",
                True,
            ),
            s(
                "GamesRadar〈Newly revealed GTA 6 characters showcase the series' new female protagonist…〉",
                "https://www.gamesradar.com/newly-revealed-gta-6-characters-showcase-the-series-first-ever-female-protagonist-and-her-bonnie-and-clyde-style-relationship",
                "Jason Duval and Lucia Caminos",
            ),
        ],
    },
    "GT17": {
        "claim": "GTA V 的舞台是洛聖都（Los Santos），主角三人：年輕的街頭混混、退休的銀行搶匪、可怕的精神病患；GTA Online 最多 30 人同時遊玩；現在 PS5、Xbox Series X|S、PC 都能玩（Rockstar 官網）",
        "tokens": ["5", "V", "三", "3", "30", "三十"],
        "sources": [
            s(
                "Rockstar Games 官網〈Grand Theft Auto V〉（2026-11-22 查詢）",
                "https://www.rockstargames.com/gta-v",
                "Welcome to Los Santos／When a young street hustler, a retired bank robber, and a terrifying psychopath find themselves entangled…／GTA Online, a dynamic and ever-evolving online universe for up to 30 players／Now available for PlayStation 5, Xbox Series X|S, and PC",
                True,
            ),
            s(
                "GameSpot 2013〈New Grand Theft Auto V trailers April 30〉（三位主角 Michael、Franklin、Trevor，舞台 Los Santos）",
                "https://www.gamespot.com/news/new-grand-theft-auto-v-trailers-april-30-6407530",
                "Michael, Franklin and Trevor … Los Santos",
            ),
        ],
    },
    "GT18": {
        "claim": "平台：GTA V 2013 年上市時在 PlayStation 3 與 Xbox 360；GTA6 2026-11-19 上市平台為 PS5、Xbox Series X|S（Take-Two 公布的上市清單沒有 PC）；兩代相隔 13 年",
        "tokens": ["2013", "3", "360", "2026", "11", "19", "5", "13", "十三", "6"],
        "sources": [
            s(
                "Take-Two 8-K Exhibit 99.1（2013-09-20）",
                "https://www.sec.gov/Archives/edgar/data/946581/000110465913071387/a13-21085_1ex99d1.htm",
                "Grand Theft Auto V is currently available for the PlayStation®3 computer entertainment system and the Xbox 360® video game and entertainment system from Microsoft.",
                True,
            ),
            s(
                "Take-Two 第一季（FY27 Q1）財報新聞稿（2026-08-07）上市清單",
                "https://www.sec.gov/Archives/edgar/data/0000946581/000162828026054580/ttwo1q27earningsrelease.htm",
                "Grand Theft Auto VI / PS5, Xbox Series X|S / November 19, 2026",
                True,
            ),
        ],
    },
}

d = json.loads(P.read_text())
d["facts"].update(F)
P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("寫入", ", ".join(F))
