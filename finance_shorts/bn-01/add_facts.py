"""把 bn-01（黑五先買後付）的事實寫進 facts.json；重跑會覆蓋同 id。"""

import json
import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "facts.json"

ADOBE = "Adobe 2026-09-28 新聞稿〈U.S. Holiday Shopping Season to Hit Record $275.1 Billion Online〉"
ADOBE_U = (
    "https://news.adobe.com/news/2026/09/adobe-us-holiday-shopping-season-to-hit-record"
)
DC360 = "Digital Commerce 360 2026-09-29 Adobe 年終網購預測報導"
DC360_U = "https://www.digitalcommerce360.com/2026/09/29/adobe-projection-2026-online-holiday-sales-275-billion/"
FED = "美國聯準會〈Economic Well-Being of U.S. Households in 2025〉信用章（2026-05）"
FED_U = "https://www.federalreserve.gov/publications/2026-economic-well-being-of-us-households-in-2025-credit.htm"
FEDX = "美國聯準會〈Economic Well-Being of U.S. Households in 2025〉摘要（2026-05）"
FEDX_U = "https://www.federalreserve.gov/publications/2026-economic-well-being-of-us-households-in-2025-executive-summary.htm"
FEDC = "美國聯準會〈Consumer & Community Context〉2026-08"
FEDC_U = "https://www.federalreserve.gov/publications/2026-august-consumer-community-context-accessible.htm"
CRS = "美國國會研究處 CRS R48858〈Buy Now, Pay Later: Policy Issues and Options for Congress〉2026-02-18"
CRS_U = "https://www.everycrsreport.com/reports/R48858.html"
FR = "美國聯邦公報 2025-08286（2025-05-12）CFPB〈Interpretive Rules, Policy Statements, and Advisory Opinions; Withdrawal〉"
FR_U = "https://www.federalregister.gov/documents/2025/05/12/2025-08286/interpretive-rules-policy-statements-and-advisory-opinions-withdrawal"
FSC1 = "金管會 2025-01-20〈金管會針對先買後付(BNPL)提醒相關事項〉"
FSC1_U = "https://www.fsc.gov.tw/ch/home.jsp?id=96&parentpath=0,2&mcustomize=news_view.jsp&dataserno=202501200001&dtable=News"
FSC2 = "金管會 2024-02-07〈金管會提醒民眾使用先買後付(BNPL)服務需留意相關資訊〉"
FSC2_U = "https://www.fsc.gov.tw/ch/home.jsp?id=96&parentpath=0,2&mcustomize=news_view.jsp&dataserno=202402070002&dtable=News"
CNA = "中央社 2025-01-20 金管會先買後付提醒報導"
CNA_U = "https://www.cna.com.tw/news/afe/202501200113.aspx"
BOT = "臺灣銀行 2026-11-12 11:09 牌告匯率（美元即期買入 32.86、賣出 32.96，中間價約 32.91）"
BOT_U = "https://rate.bot.com.tw/xrt?Lang=zh-TW"


def s(name, url, quote, official=False):
    return {"name": name, "url": url, "official": official, "quote": quote}


F = {
    "BN01": {
        "claim": "Adobe 2026-09 預估：美國 2026 年 11–12 月網購 2,751 億美元（年增 6.7%）；黑色星期五網購 129 億美元（年增 9.2%）；先買後付 11–12 月帶動 213 億美元（年增 6.6%），黑五當天 8.07 億美元、網路星期一 10.9 億美元。皆為預估（黑色星期五＝感恩節隔天的星期五，簡稱黑五）",
        "tokens": ["9", "5", "五", 
            "2026",
            "275.1",
            "2751",
            "6.7",
            "12.9",
            "129",
            "9.2",
            "21.3",
            "213",
            "6.6",
            "807",
            "8.07",
            "8",
            "1.09",
            "10.9",
            "11",
            "12",
            "1",
        ],
        "sources": [
            s(
                ADOBE,
                ADOBE_U,
                "BNPL is expected to drive $21.3 billion in November and December, up 6.6% YoY … Black Friday … $807 million in online spend … Cyber Monday … $1.09 billion in online spend … Black Friday … $12.9 billion (up 9.2% YoY)",
                True,
            ),
            s(
                DC360,
                DC360_U,
                "Adobe projects BNPL spending on online orders to reach $807 million on Black Friday 2026 … $21.3 billion … $275.1 billion",
            ),
        ],
    },
    "BN02": {
        "claim": "先買後付是一種在結帳時提供的融資（point-of-sale financing）；常見型態「分四期」通常先付 25%，其餘三期每兩週付一次，通常不收利息但可能收逾期費；CFPB 2025-12 研究（受查業者）：4.1% 的分四期貸款被計收逾期費，每次平均計收 9.70 美元、實收 5.70 美元；CFPB 統計分四期放款名目金額 2019 年 22 億美元→2023 年 439 億美元（未扣通膨）",
        "tokens": ["2025", "5.70", "6", "1", 
            "4",
            "25",
            "3",
            "2",
            "4.1",
            "9.70",
            "9.7",
            "2019",
            "22",
            "2.2",
            "2023",
            "439",
            "43.9",
            "20",
            "四",
            "兩",
            "三",
        ],
        "sources": [
            s(
                CRS,
                CRS_U,
                "BNPL is a form of point-of-sale financing … Pay in 4 typically requires 25% up front, with three more payments in two-week intervals … charges no interest but may carry late or other fees … 4.1% of Pay in 4 loans were assessed late fees, with $9.70 assessed and $5.70 collected per late fee … grew from $2.2 billion in 2019 to $43.9 billion in 2023",
                True,
            ),
            s(
                FEDC,
                FEDC_U,
                "Figure 4: Paid late fee or overdraft, among BNPL users",
                True,
            ),
        ],
        "exception": "分四期結構與 CFPB 數字以國會研究處報告為主，聯準會資料佐證逾期費存在",
    },
    "BN03": {
        "claim": "聯準會 2025 年家庭問卷（2025-10 進行，2026-05 出版）：過去 12 個月用過先買後付的成年人占 16%（2021 年 10%、2024 年 15%）；家庭年收入未滿 2.5 萬美元 18%、10 萬以上 12%；18–29 歲成年人 22%。註：信用章原文寫『up from 15 percent in 2025』，年份疑為原文筆誤，2024 年 15% 以 8 月出版品圖 1 為準",
        "tokens": [
            "2025",
            "16",
            "2021",
            "10",
            "12",
            "25000",
            "2.5",
            "100000",
            "10",
            "18",
            "22",
            "29",
            "百分之十六",
            "六分之一",
            "6",
        ],
        "sources": [
            s(
                FED,
                FED_U,
                "Sixteen percent of people used BNPL in the prior 12 months, up from 15 percent in 2025 and 10 percent in 2021 … Table 41: Less than $25,000 18; $100,000 or more 12; 18–29 22",
                True,
            ),
            s(
                FEDX,
                FEDX_U,
                "Buy Now, Pay Later (BNPL) use edged up 1 percentage point to 16 percent of all adults.",
                True,
            ),
            s(FEDC, FEDC_U, "Figure 1: 2021 10 … 2024 15 … 2025 16 (Among all adults)", True),
        ],
        "exception": "聯準會原始調查僅此一份；三份為聯準會不同出版品，數字一致",
    },
    "BN04": {
        "claim": "聯準會：用戶的主要理由（分母＝先買後付用戶）——整體 31% 想分攤付款、29%「唯一負擔得起這筆購買的方式」；家庭年收入未滿 2.5 萬美元的用戶 40%、10 萬以上 15%；10 萬以上用戶 26% 以避開利息為主要理由。有信用卡比例（分母＝各收入組全體成年人）：未滿 2.5 萬 46%、10 萬以上 97%",
        "tokens": [
            "31",
            "29",
            "40",
            "15",
            "26",
            "46",
            "97",
            "25000",
            "2.5",
            "100000",
            "10",
            "四成",
            "4",
        ],
        "sources": [
            s(
                FED,
                FED_U,
                "Table 42: Wanted to spread out payments 31 … Only way I could afford it <$25K 40 … $100K+ 15 … Overall 29; Avoid interest charges $100K+ 26; Table 40: Has a credit card <$25,000 46 … $100,000 or more 97",
                True,
            ),
            s(
                FEDC,
                FEDC_U,
                "Figure 2: use by emergency savings: less than $100, 31 … $2,000 or more, 8",
                True,
            ),
        ],
        "exception": "主因與信用卡比例僅聯準會此份調查有；第二份為聯準會同一調查的另一出版品",
    },
    "BN05": {
        "claim": "聯準會：過去 12 個月的先買後付用戶中 26% 曾逾期付款（略多於四分之一）；家庭年收入未滿 2.5 萬美元 40%、10 萬以上 11%；18–29 歲用戶 32%；逾期者 64% 表示被加收費用（約占全部用戶 17%）；多數消費者須登記自動扣款才能使用；11% 用戶因先買後付扣款被銀行收取透支或存款不足費",
        "tokens": ["12", 
            "26",
            "四分之一",
            "4",
            "40",
            "11",
            "32",
            "18",
            "29",
            "64",
            "17",
            "25000",
            "2.5",
            "100000",
            "10",
            "四成",
            "百分之十一",
        ],
        "sources": [
            s(
                FED,
                FED_U,
                "Slightly more than one-fourth of BNPL users were late making a payment … Overall 26 … 18–29 32 … Since most consumers need to enroll in automatic payments in order to use BNPL, many payments are made via autopay … Less than $25,000 40 … $100,000 or more 11 … Sixty-four percent of those BNPL users who were late making a payment (17 percent of those who used BNPL) said they were charged extra … Eleven percent of adults who used BNPL had a payment trigger an overdraft or non-sufficient funds (NSF) fee",
                True,
            ),
            s(
                FEDX,
                FEDX_U,
                "Eleven percent of BNPL users had a payment trigger an overdraft or non-sufficient funds (NSF) fee from their bank in the prior year.",
                True,
            ),
        ],
        "exception": "聯準會原始調查僅此一份；兩份為聯準會不同出版品，數字一致",
    },
    "BN06": {
        "claim": "聯準會：過去一年五分之一用戶曾用它買食品雜貨或外送，其中 45% 把「唯一負擔得起」列為主要理由；買過食品雜貨或外送的用戶 43% 曾被加收逾期費或產生銀行透支／存款不足費（全部用戶 21%）；將近一半用戶用它買過服飾配件",
        "tokens": ["5", "五分之一", "一", "45", "43", "21", "四成", "一半"],
        "sources": [
            s(
                FED,
                FED_U,
                "One in five BNPL users used the product to pay for groceries or food delivery in the prior year … Forty-five percent of those who used BNPL for grocery or food delivery purchases said that the main reason for using BNPL is that it was the only way that they could afford a purchase … Nearly half of BNPL users said that they bought clothing and accessories",
                True,
            ),
            s(
                FEDC,
                FEDC_U,
                "Figure 4: Overall 21 … groceries or food delivery 43 (Paid late fee or overdraft, among BNPL users)",
                True,
            ),
        ],
        "exception": "聯準會原始調查僅此一份；兩份為聯準會不同出版品",
    },
    "BN07": {
        "claim": "CFPB 2024 年 5 月發布解釋性規則，認為透過數位帳戶使用的分四期須遵守部分信用卡消費者保護規定（TILA subpart B）；2025-05-12 撤回（聯邦公報 2025-08286 撤回清單之一）；紐約已立法建立先買後付揭露與牌照制度（部分條文另有生效條件）",
        "tokens": ["2024", "5", "2025", "4", "12", "四"],
        "sources": [
            s(
                CRS,
                CRS_U,
                "May 2024: The CFPB issued an interpretive rule treating Pay in 4 as a credit card for purposes of TILA subpart B … May 2025: Acting CFPB Director Russell Vought withdrew the rule … Federal Register on May 12, 2025 (90 FR 20084) … New York recently passed a law imposing certain disclosure and licensing requirements … California requires BNPL providers to hold a BNPL-specific license",
                True,
            ),
            s(
                FR,
                FR_U,
                "Use of Digital User Accounts to Access Buy Now, Pay Later Loans（撤回清單之一）",
                True,
            ),
        ],
    },
    "BN08": {
        "claim": "金管會 2025-01-20：先買後付是應收債權轉讓後的分期還款服務，非屬金融特許業務，一般企業依民法即可提供；本質為借貸，可能有違約金、遲延利息及其他費用；已協助台北市租賃公會訂自律規範，建議揭示總價款、期數、利率、遲延利息；2024-02-07 提醒：買預付型商品，要注意商家違約時是否仍須還款",
        "tokens": ["2025", "1", "20", "2024", "2", "7"],
        "sources": [
            s(
                FSC1,
                FSC1_U,
                "先買後付(Buy Now Pay Later, BNPL)係基於買賣商品或服務所衍生之應收債權轉讓後之分期還款服務，非屬金融特許業務，依民法一般企業即可提供……該項服務本質為借貸，可能有違約金、遲延利息及其他費用等……揭示債權讓與契約之總價款、期數、利率等還款相關內容，及消費者未按期付款時應負擔之遲延利息與其他費用……同時提醒消費者「清楚還款條件，理性使用服務」",
                True,
            ),
            s(
                FSC2,
                FSC2_U,
                "尤其是當使用BNPL服務購買預付型商品服務時，應再注意如商家違約無法繼續提供服務時，是否仍須還款",
                True,
            ),
            s(CNA, CNA_U, "BNPL服務本質為借貸，可能有違約金、遲延利息及其他費用等"),
        ],
    },
    "BNFX": {
        "claim": "新台幣換算為本頻道試算，採一美元 32.91 元概算（臺灣銀行 2026-11-12 上午美元即期買賣中間價）：8.07 億美元≈266 億元；213 億美元≈7,010 億元（約 7 千億）；129 億美元≈4,245 億元；9.70 美元≈319 元（約 320 元）；分四期 2019→2023 約 20 倍（43.9÷2.2≈20）",
        "tokens": ["1000", 
            "32.91",
            "266",
            "7010",
            "7000",
            "7",
            "千",
            "4245",
            "319",
            "320",
            "20",
            "43.9",
            "2.2",
        ],
        "sources": [
            s(
                BOT,
                BOT_U,
                "美金 即期買入 32.86、即期賣出 32.96（2026/11/12 11:09）",
                True,
            ),
            s(ADOBE, ADOBE_U, "$807 million … $21.3 billion … $12.9 billion", True),
        ],
        "exception": "本頻道試算：匯率與算式列於事實表，片中標明試算",
    },
}

d = json.loads(P.read_text())
d["facts"].update(F)
P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("寫入", ", ".join(F))
