"""把 mem-01（記憶體漲價）的事實寫進 facts.json；重跑會覆蓋同 id。"""

import json
import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "facts.json"

SS = "三星電子官方新聞稿 2026-10-29 第三季財報"
SS_U = "https://news.samsung.com/global/samsung-electronics-announces-third-quarter-2026-results"
SM = "SamMobile 2026 第三季財報報導"
SM_U = "https://www.sammobile.com/news/samsung-record-breaking-profit-usd-80-5-billion-q3-2026"
TF = "TrendForce 2026-09-30 第四季記憶體合約價預測"
TF_U = "https://www.trendforce.com/presscenter/news/20260930-13258.html"
TFI = "TrendForce 2026-08-10 iPhone 18 成本分析"
TFI_U = "https://trendforce.com/presscenter/news/20260810-13172.html"
TFN = "TrendForce 2026-09-04 筆電成本分析"
TFN_U = "https://www.trendforce.com/presscenter/news/20260904-13217.html"
CP = "Counterpoint Research 2026-09-03 現有手機售價追蹤"
CP_U = "https://counterpointresearch.com/en/insights/global-existing-smartphone-prices-climb-about-15-percent-in-2026"
EE = "電子工程專輯 2026-10-28 轉述 Counterpoint"
EE_U = "https://www.eettaiwan.com/20261028nt21-smartphone-prices-up-2026-memory-cost/"
CNA = "中央社 2026-11-01〈AI通膨席捲手機市場〉（聯合新聞網）"
CNA_U = "https://udn.com/news/story/7240/9849857"
LTN = "自由財經 2026〈財經週報-AI通膨〉"
LTN_U = "https://ec.ltn.com.tw/article/paper/1774239"
CNBC = "CNBC 2026-11-02 蘋果財報"
CNBC_U = "https://www.cnbc.com/2026/11/02/apple-aapl-q4-2026-earnings-live-updates.html"
AK = "蘋果 FY2026 10-K 年報（SEC）"
AK_U = "https://www.sec.gov/Archives/edgar/data/0000320193/000032019326000026/aapl-20260926.htm"
EU = "Euronews 2026-11-03 蘋果財報"
EU_U = "https://www.euronews.com/2026/11/03/apple-earnings-beat-expectations-but-rising-chip-costs-worry-investors"
MP = "美光官方新聞稿 2025-12-03 退出 Crucial 消費者業務"
MP_U = "https://micron.gcs-web.com/node/49841"
SR = "StorageReview 美光退出 Crucial 報導"
SR_U = "https://www.storagereview.com/news/micron-exits-crucial-consumer-business-to-focus-on-higher-growth-segments"
BF = "Blocks and Files 2025-03-21 美光財報會議報導"
BF_U = "https://www.blocksandfiles.com/ai-ml/2025/03/21/micron-warns-of-inventory-drag-outside-datacenters/1607342"
TH = "Tom's Hardware 美光 Hot Chips 2026 報導"
TH_U = "https://www.tomshardware.com/tech-industry/semiconductors/micron-says-the-silicon-gap-between-hbm-and-ddr5-is-widening-with-every-generation"
KT = "Korea Times 2026-11-01 韓國 10 月出口（貿易產業資源部初步數字）"
KT_U = "https://www.koreatimes.co.kr/economy/20261101/koreas-monthly-exports-hit-1153-bil-in-oct-on-record-chip-sales"
AE = "Asia Business Daily 2026-11-01 韓國 10 月出口"
AE_U = "https://www.asiae.co.kr/en/article/2026110110285709510"
DG = "經濟日報 2026-10-07 主計總處簡任視察蔡秀慧說明 9 月物價"
DG_U = "https://money.udn.com/money/story/10869/9801163"
DG2 = "聯合新聞網 2026-10-07 主計總處 9 月 CPI"
DG2_U = "https://udn.com/news/story/7238/9801202"
BOT = "臺灣銀行 2026-11-04 牌告匯率（韓元現金買賣中間價約 0.0246、美元即期中間價約 32.76）"
BOT_U = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
MARKET = "市場研究機構估算：查不到官方統計，片中標明機構名稱（2026-11-04 分工規則）"
MEDIA = (
    "媒體採訪業者與市場售價：查不到官方統計，片中標明是業者說法（2026-11-04 分工規則）"
)


def s(name, url, quote, official=False):
    return {"name": name, "url": url, "official": official, "quote": quote}


F = {
    "MM01": {
        "claim": "三星 2026 第三季營收 195.3 兆韓元、營業利益 107.4 兆韓元，全球首家單季破 100 兆韓元的科技公司；半導體部門 106.5 兆；手機與網通合計虧 0.6 兆",
        "tokens": ["2026", "195.3", "107.4", "100", "106.5", "0.6", "3"],
        "sources": [
            s(
                SS,
                SS_U,
                "making Samsung Electronics the world’s first tech company to exceed KRW 100 trillion in quarterly operating profit",
                True,
            ),
            s(
                SS,
                SS_U,
                "The MX and Networks Businesses posted a combined KRW 37.7 trillion in consolidated revenue and reported an operating loss of KRW 0.6 trillion",
                True,
            ),
            s(SM, SM_U, "an operating profit of KRW 106.5 trillion"),
        ],
    },
    "MMFX": {
        "claim": "新台幣換算為本頻道試算：107.4 兆韓元≈2.6 兆、106.5 兆≈2.6 兆、0.6 兆≈150 億；564 億美元≈1.8 兆；半導體占三星獲利 106.5÷107.4≈99%",
        "tokens": ["2.6", "150", "1.8", "99", "2026", "11", "4"],
        "sources": [
            s(
                BOT,
                BOT_U,
                "韓元現金買入 0.02262、賣出 0.02652；美金即期 32.685／32.835",
                True,
            ),
            s(SS, SS_U, "KRW 107.4 trillion", False),
        ],
        "exception": "本頻道試算：匯率與算式列於事實表，片中標明試算",
    },
    "MM02": {
        "claim": "三星：伺服器需求帶動所有應用的記憶體價格上漲；預期 2027 年 AI 帶動的需求將遠超產業供給；2026 全年資本支出約 84.4 兆韓元，半導體占 76.8 兆",
        "tokens": ["2027", "2026", "84.4", "76.8"],
        "sources": [
            s(
                SS,
                SS_U,
                "Strong demand momentum for servers led to higher market prices across all applications",
                True,
            ),
            s(
                SS,
                SS_U,
                "increasing AI-driven demand will far exceed the industry supply in comparison with 2026",
                True,
            ),
            s(
                SS,
                SS_U,
                "The full-year capital expenditure for 2026 is expected at approximately KRW 84.4 trillion, including KRW 76.8 trillion allocated to the DS Division",
                True,
            ),
        ],
    },
    "MM03": {
        "claim": "美光：同樣容量，HBM3E 用掉的晶圓約為 DDR5 的 3 倍，而且下一代差距更大",
        "tokens": ["3"],
        "sources": [
            s(
                BF,
                BF_U,
                "HBM3E needs roughly three times the silicon of DDR5 for the same number of bits",
            ),
            s(
                TH,
                TH_U,
                "roughly three times the wafer area of DDR5 for the same capacity",
            ),
        ],
        "exception": "公司在財報會議與技術會議的說法，只有媒體轉述原文（2026-11-04 分工規則）",
    },
    "MM04": {
        "claim": "美光 2025-12-03 宣布退出 Crucial 消費者業務，理由是把供給與支援留給成長更快領域的大型策略客戶",
        "tokens": ["2025", "12"],
        "sources": [
            s(
                MP,
                MP_U,
                "improve supply and support for our larger, strategic customers in faster-growing segments",
                True,
            ),
            s(
                SR,
                SR_U,
                "Micron exits Crucial consumer business to focus on higher-growth segments",
            ),
        ],
    },
    "MM05": {
        "claim": "TrendForce 預估 2026 第四季一般 DRAM 合約價季增 10–15%、NAND 季增 15–20%，漲勢放慢；DRAM 供給 2027 仍吃緊；品牌下修主流筆電 SSD 容量；電視、機上盒、穿戴裝置難吸收成本",
        "tokens": ["2026", "4", "10", "15", "20", "2027", "四"],
        "sources": [
            s(
                TF,
                TF_U,
                "Conventional DRAM contract prices are forecast to rise 10–15% QoQ, with NAND Flash up 15–20%",
            ),
            s(
                TF,
                TF_U,
                "PC brands are cutting SSD capacities in mainstream models to reduce bill-of-materials costs",
            ),
            s(
                "iPhone Wired 轉述 TrendForce 第四季預測",
                "https://iphonewired.com/industry/1200023/",
                "4Q26 DRAM contracts up 10–15%",
            ),
        ],
        "exception": MARKET,
    },
    "MM06": {
        "claim": "韓國 2026 年 10 月半導體出口 564 億美元、年增 259%，占總出口約 49%；總出口 1,153 億美元（初步數字）",
        "tokens": ["2026", "10", "564", "259", "49", "1153", "1,153"],
        "sources": [
            s(
                KT,
                KT_U,
                "South Korea's exports jumped 93.7 percent to a record $115.3 billion in October",
            ),
            s(
                AE,
                AE_U,
                "Semiconductors Drive South Korea's Exports, Accounting for 49% of October's $115.3 Billion Total",
            ),
        ],
        "exception": "韓國貿易產業資源部初步數字，媒體轉述；待補官方原文連結",
    },
    "MM07": {
        "claim": "TrendForce 估 iPhone Pro 256GB 記憶體占材料成本，由一年前約 10% 升到 2026 第三季約 34%，2027 上半年可能超過 40%；iPhone 18 Pro 256GB 材料成本較前代高約 38%；低階中階機利潤薄最吃緊；記憶體價格自 2025 年初漲到 5 至 7 倍",
        "tokens": [
            "256",
            "10",
            "2026",
            "3",
            "34",
            "2027",
            "40",
            "18",
            "38",
            "2025",
            "5",
            "7",
            "三",
        ],
        "sources": [
            s(
                TFI,
                TFI_U,
                "from around 10% a year ago to approximately 34% in 3Q26, and is expected to exceed 40% in 1H27",
            ),
            s(
                TFI,
                TFI_U,
                "With memory prices having risen five- to sevenfold since the beginning of 2025",
            ),
            s(CNA, CNA_U, "記憶體成本占比從一年前約10%升到2026年第3季的34%左右"),
        ],
        "exception": MARKET,
    },
    "MM08": {
        "claim": "蘋果 9 月季毛利率 47.9%（含約 1 個百分點關稅退款），預估 12 月季 45%–46%；執行長 Ternus 稱「勉強」調漲；6 月 iPhone 美國調漲 100 美元；iPhone 營收年增逾 17%；年報寫記憶體與儲存成本上升趨勢將加劇",
        "tokens": ["9", "47.9", "1", "12", "45", "46", "6", "100", "17"],
        "sources": [
            s(
                CNBC,
                CNBC_U,
                "CFO Kevan Parekh guided December-quarter gross margin to 45% to 46%",
            ),
            s(CNBC, CNBC_U, "Ternus said Apple reluctantly raised prices"),
            s(
                AK,
                AK_U,
                "The Company expects these trends to intensify for memory and storage components.",
                True,
            ),
            s(
                EU,
                EU_U,
                "Apple earnings beat expectations, but rising chip costs worry investors",
            ),
        ],
    },
    "MM09": {
        "claim": "vivo 台灣總經理：5,000 元以下區間已往上移到接近 1 萬元；三星台灣總經理：6,000 元以下手機幾乎看不到；業者看法分別為壓力到 2027 第一季以上、2027 年底、可能到 2028",
        "tokens": ["5000", "5,000", "1", "6000", "6,000", "2027", "2028"],
        "sources": [
            s(
                CNA,
                CNA_U,
                "vivo 陳怡婷：5000 元以下區間已上移接近 1 萬元；三星陳啓蒙：市場幾乎看不到 6000 元以下手機",
            ),
            s(
                "中央社 2026-10-29 OPPO 新機發表",
                "https://www.cna.com.tw/news/afe/202610290252.aspx",
                "記憶體漲價壓力可能延續到明年，甚至2028年",
            ),
        ],
        "exception": MEDIA,
    },
    "MM10": {
        "claim": "Counterpoint：2026 年至今全球現有手機零售價平均漲約 15%，亞太約 19%、美國約 5%；新機上市價較去年同期高約 25%；超過四成機型漲價；記憶體價格自 2025 第四季起漲到約 4 倍",
        "tokens": ["2026", "15", "19", "5", "25", "2025", "4", "四", "40"],
        "sources": [
            s(
                CP,
                CP_U,
                "global existing smartphone prices climb about 15 percent in 2026",
            ),
            s(
                EE,
                EE_U,
                "2026年智慧型手機價格平均上漲15%；亞太19%、美國5%；新機約高25%；逾40%機型調漲",
            ),
        ],
        "exception": MARKET,
    },
    "MM11": {
        "claim": "台灣：iPhone 18 Pro 系列比前代貴 5,000 元以上，iPhone 17 系列不降反漲；Galaxy S26 Ultra 16GB/1TB 官網由 59,900 調到 67,900 元（多 8,000 元）",
        "tokens": [
            "18",
            "5000",
            "5,000",
            "17",
            "26",
            "16",
            "1",
            "59900",
            "59,900",
            "67900",
            "67,900",
            "8000",
            "8,000",
        ],
        "sources": [
            s(
                CNA,
                CNA_U,
                "Galaxy S26 Ultra 16GB/1TB 由 59,900 元調至 67,900 元；iPhone 18 Pro 系列較前代高出 5,000 元以上",
            ),
            s(
                LTN,
                LTN_U,
                "蘋果9月推出的iPhone18Pro系列更較前一代上漲約5,000元，且過去新機推出時前一代手機價格會降價，但今年iPhone17系列不降反漲",
            ),
        ],
        "exception": MEDIA,
    },
    "MM12": {
        "claim": "TrendForce：建議售價 900 美元的主流筆電，CPU、DRAM、SSD 占材料成本由 2025 第一季約 45% 升到 2026 第三季約 68%；2026 全球筆電出貨預估年減 9.4%",
        "tokens": ["900", "2025", "1", "45", "2026", "3", "68", "9.4", "三"],
        "sources": [
            s(
                TFN,
                TFN_U,
                "core components including the CPU, DRAM, and SSD accounted for approximately 45% of the system's total BOM cost",
            ),
            s(LTN, LTN_U, "相關核心零組件占比在2026年第三季已上升至68%"),
        ],
        "exception": MARKET,
    },
    "MM13": {
        "claim": "截至 2026 第三季 PC 相關產品漲幅逾 30%；宏碁預期第四季 PC 再漲 5%–20%；筆電業者只能調漲售價或降低規格",
        "tokens": ["2026", "3", "30", "4", "5", "20", "四", "三"],
        "sources": [
            s(
                LTN,
                LTN_U,
                "截至第三季止，PC相關產品漲幅已逾30%。宏碁預期，第四季PC價格將續漲5%至20%",
            ),
            s(LTN, LTN_U, "NB廠只能以兩種方法因應，一是調漲售價，二是降低規格"),
        ],
        "exception": MEDIA,
    },
    "MM14": {
        "claim": "主計總處：2026 年 9 月教養設備及用具（電腦、隨身碟、印表機等）年增 9.75%，連 10 個月上漲，44 年來最高；權重 1.76 個百分點，購買頻率低，影響不大，「國內沒有 AI 通膨」；9 月進口物價新台幣計價漲 29.59%，多為加工後再出口",
        "tokens": ["2026", "9", "9.75", "10", "44", "1.76", "29.59"],
        "sources": [
            s(DG, DG_U, "9月價格上揚9.75%……為44年來、有統計以來最高"),
            s(DG2, DG2_U, "涵蓋電腦、隨身碟的教養設備及用具大漲9.75%"),
        ],
        "exception": "主計總處官員說明，媒體轉述；10 月數字 11/05 公布後要更新並補官方連結",
    },
}

EXTRA = {
    "MM01": ["三"],
    "MM02": ["三"],
    "MM07": ["零", "8"],
    "MM09": ["三", "2027"],
    "MM10": ["9", "零"],
    "MM11": ["10", "3", "1,000", "1000", "3,000", "3000", "5,000", "11,000", "11000"],
    "MM13": ["兩", "1"],
    "MMFX": ["九", "兩"],
}
EXTRA["MM02"] += ["3"]
EXTRA["MM07"] += ["0"]
EXTRA["MM09"] += ["3"]
EXTRA["MM10"] += ["0"]
EXTRA["MM13"] += ["2"]
EXTRA["MMFX"] += ["9", "2"]
EXTRA["MM14"] = ["0"]
for k, v in EXTRA.items():
    F[k]["tokens"] += v
F["MM11"]["claim"] += "；S26 系列 3 月開賣較前代多 1,000–3,000 元，10 月再多 3,000–5,000 元；iPhone Air 1TB 調高 11,000 元"
F["MM11"]["sources"].append(s(LTN, LTN_U, "Galaxy S26系列今年3月開賣，售價較前一代調漲1,000元至3,000元，而10月1日S系列價格則又上調漲3,000元至5,000元"))
F["MM13"]["sources"].append(s(LTN, LTN_U, "不少消費者已在上半年提早採購，接下來買氣恐明顯下滑"))
F["MM15"] = {
    "claim": "記憶體主要分 DRAM（運行時暫存）與 NAND 快閃記憶體（儲存）兩類",
    "tokens": ["兩"],
    "sources": [
        s(TF, TF_U, "Conventional DRAM contract prices ... NAND Flash"),
        s("美光官方：DRAM 與 NAND 產品分類", "https://www.micron.com/products", "DRAM, NAND", True),
    ],
}

APPLE = "蘋果官方新聞稿 2026-11-02 第四財季財報"
APPLE_U = "https://www.apple.com/newsroom/2026/11/apple-reports-fourth-quarter-results/"
TN = "科技新報 2026-10-01 三星 Galaxy S26／A 系列調價"
TN_U = "https://technews.tw/2026/10/01/galaxy-s26-a-series-raise-prices/"
F["MM02"]["sources"].append(s(SM, SM_U, "Samsung Q3 2026 record-breaking operating profit, thanks to memory chips"))
F["MM02"]["tokens"] += ["2.1"]
F["MM03"]["sources"][0] = s(BF, BF_U, "HBM3E consumes three times the amount of silicon compared to D5 to produce the same number of bits")
F["MM03"]["claim"] = "美光執行長：同樣位元數，HBM3E 用掉的矽約為 DDR5 的 3 倍，並預期 HBM4 之後差距更大"
F["MM08"]["sources"].insert(0, s(APPLE, APPLE_U, "Company gross margin was 47.9 percent", True))
F["MM11"]["sources"].append(s(TN, TN_U, "Galaxy S26 Ultra 16GB+1TB 59,900→67,900；S26 其他版本 +3,000～5,000；A17 +1,000"))
F["MM11"]["tokens"] += ["1,000", "17"]
F["MM12"]["sources"].append(s(TFN, TFN_U, "the decline in global notebook shipments for full-year 2026 is expected to narrow to 9.4% YoY"))
F["MM12"]["tokens"] += ["9", "2", "29000"]
F["MMFX"]["tokens"] += ["2.1", "29", "2", "9", "4", "0"]
F["MMFX"]["claim"] += "；84.4 兆韓元≈2.1 兆；900 美元≈2 萬 9 千元"
F["MM13"]["sources"].append(s("民報 2026-09-20〈宏碁下一局〉（江星翰）", "https://www.peoplenews.tw/?p=56432", "PC在第四季價格恐再上漲5%至20%"))

F["MM15"]["tokens"] += ["2"]
F["MMFX"]["tokens"] += ["1000", "千"]
F["MM14"]["tokens"] += ["7"]

F["MM13"]["tokens"] += ["2027"]
F["MM13"]["sources"].append(s("民報 2026-09-20〈宏碁下一局〉（江星翰）", "https://www.peoplenews.tw/?p=56432", "PC平均售價可能到2027年中才來到高點"))
F["MM08"]["sources"].append(s(AK, AK_U, "Actions, such as price increases, that have been and may in the future be taken by the Company may not effectively mitigate these negative impacts and may also reduce demand for the Company's products.", True))
F["MM05"]["sources"].append(s(TF, TF_U, "The market depends heavily on Taiwanese suppliers because major suppliers are cutting production"))

d = json.loads(P.read_text())
d["facts"].update(F)
P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print(len(F), "條")
