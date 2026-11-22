"""把 us-01（美國全國停飛：航班取消錢誰賠）的事實寫進 facts.json；重跑會覆蓋同 id。查詢日期 2026-11-20。"""

import json
import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "facts.json"

FAA = "美國聯邦航空總署 FAA〈Nationwide Ground Stop: Questions and Answers〉2026-11-15"
FAA_U = "https://www.faa.gov/newsroom/faa-statement-nationwide-ground-stop"
FOX = "Fox Weather 2026-11-14〈Thousands of flights canceled, delayed as US air travel slowly recovers from historic nationwide ground stop〉"
FOX_U = "https://www.foxweather.com/weather-news/flights-canceled-delayed-us-ground-stop-november-2026"
CNN = "CNN 2026-11-13 直播〈Some US flights resume after hours-long ground stop〉"
CNN_U = "https://www.cnn.com/2026/11/13/us/live-news/flights-ground-stop-faa"
DOT50 = "美國交通部 2026-11-17 新聞稿〈Trump Administration Calls on Congress to Fully Fund Air Traffic Control Modernization with $50.1 Billion Investment〉"
DOT50_U = "https://www.transportation.gov/briefing-room/trump-administration-calls-congress-fully-fund-air-traffic-control-modernization-501"
ABC = "ABC News 2026-11〈Duffy asked for $50B for air traffic control after ground stop, a marked increase〉"
ABC_U = "https://abc7news.com/story/duffy-asked-50b-air-traffic-control-ground-stop-marked-increase/20047563/"
DOTR = "美國交通部〈What Airline Passengers Need to Know About DOT's Automatic Refund Rule〉2024-11-18"
DOTR_U = "https://www.transportation.gov/briefing-room/what-airline-passengers-need-know-about-dots-automatic-refund-rule"
CFR = "美國聯邦法規 14 CFR Part 260（Refunds and Other Consumer Protections）§260.2、§260.6"
CFR_U = "https://www.ecfr.gov/current/title-14/chapter-II/subchapter-A/part-260"
NN = "NewsNation〈Canceled flight? DOT's automatic cash refund rules explained〉"
NN_U = "https://digital-release.newsnationnow.com/travel/canceled-delayed-flight-dots-automatic-cash-refund-rules"
FR26 = "美國聯邦公報 2026-13675（2026-07-07）〈Airline Refunds and Other Consumer Protections〉執法裁量延長"
FR26_U = "https://www.govinfo.gov/content/pkg/FR-2026-07-07/html/2026-13675.htm"
FR25B = "美國聯邦公報 2025-22140（2025-12-05）執法裁量公告"
FR25B_U = "https://www.govinfo.gov/content/pkg/FR-2025-12-05/html/2025-22140.htm"
DASH = "美國交通部〈Airline Customer Service Dashboard〉（2026-11-20 查詢）"
DASH_U = "https://www.transportation.gov/airconsumer/airline-customer-service-dashboard"
FR25 = "美國聯邦公報 2025-20042（2025-11-17）〈Airline Passenger Rights〉撤回 ANPRM"
FR25_U = "https://www.govinfo.gov/content/pkg/FR-2025-11-17/html/2025-20042.htm"
CBS = "CBS News 2025-11〈White House drops plan to make airlines pay travelers for delayed flights〉"
CBS_U = "https://www.cbsnews.com/news/trump-drops-biden-proposal-delayed-flights-airlines-compensation/"
EU = "歐盟 261/2004 號規則（EUR-Lex 32004R0261）前言第 15 點、第 5(3)、7、9 條"
EU_U = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32004R0261"
YE = "歐盟 Your Europe〈Air passenger rights〉"
YE_U = "https://europa.eu/youreurope/citizens/travel/passenger-rights/air/index_en.htm"
TW = "交通部〈民用航空乘客與航空器運送人運送糾紛調處辦法〉第 3、4、8 條（108-05-30 修正）"
TW_U = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=K0090047"
CNA = "中央社 2017-09-16〈民航局修法 航班延誤5小時可全額退費〉"
CNA_U = "https://www.cna.com.tw/news/firstnews/201709165004.aspx"
BOT = "臺灣銀行 2026-11-20 17:01 牌告匯率（美元即期買入 32.865、賣出 33.015，中價 32.94；歐元即期買入 35.835、賣出 36.435，中價 36.135）"
BOT_U = "https://rate.bot.com.tw/xrt?Lang=zh-TW"


def s(name, url, quote, official=False):
    return {"name": name, "url": url, "official": official, "quote": quote}


F = {
    "UA01": {
        "claim": "2026 年 11 月 13 日美東時間約下午 3:30，FAA 因技術問題發布全國停飛令；同日晚上 8:15 系統穩定、恢復飛行（約 4 小時 45 分，近 5 小時）。22 座航路管制中心有 17 座出現不穩；停飛時約 3,500 架在空中的飛機全數安全降落",
        "tokens": [
            "2026",
            "11",
            "13",
            "3",
            "30",
            "8",
            "15",
            "4",
            "45",
            "5",
            "22",
            "17",
            "3500",
            "3,500",
            "近 5 小時",
            "五",
        ],
        "sources": [
            s(
                FAA,
                FAA_U,
                "On November 13 at approximately 3:30 p.m. ET, the FAA experienced a technical problem that resulted in issuing a nationwide ground stop. … air traffic resumed as of 8:15 p.m. that same day. … We began experiencing instability at 17 of our 22 Air Route Traffic Control Centers … Approximately 3,500 aircraft safely landed",
                True,
            ),
            s(
                FOX,
                FOX_U,
                "Friday's nationwide ground stop, which lasted more than four hours",
            ),
            s(CNN, CNN_U, "Some US flights resume after hours-long ground stop"),
        ],
    },
    "UA02": {
        "claim": "FAA：11 月 13 日（週五）業者取消約 12,462 班（其中主要航空 9,082 班），並說明不全是停飛直接造成；FlightAware 統計當天超過 9,100 班取消、24,500 班延誤（兩者統計口徑不同）",
        "tokens": [
            "11",
            "13",
            "12462",
            "12,462",
            "1.2",
            "萬",
            "9082",
            "9,082",
            "9100",
            "9,100",
            "24500",
            "24,500",
            "2.45",
        ],
        "sources": [
            s(
                FAA,
                FAA_U,
                "operators canceled approximately 12,462 flights, including 9,082 cancellations by major airlines, out of an abundance of caution. While not all cancellations were directly caused by the nationwide ground stop",
                True,
            ),
            s(
                FOX,
                FOX_U,
                "more than 9,100 flights were canceled and more than 24,500 were delayed Friday, according to FlightAware",
            ),
        ],
    },
    "UA03": {
        "claim": "FAA 說明原因：舊設備在 FTI 網路湧入每 4 到 5 秒 1,000 次連線請求的資料後變得不穩；初步調查指向德州 Amarillo 雷達站與阿肯色州 El Dorado 通訊站，網路服務商 L3Harris 曾在 El Dorado 部署新路由器；目前證據顯示不是網路攻擊；已停用另外 60 多台同型路由器的相同功能",
        "tokens": ["4", "5", "1000", "1,000", "60", "L3Harris"],
        "sources": [
            s(
                FAA,
                FAA_U,
                "data began flooding the FAA FTI network, at a rate of 1,000 connection attempts every 4 to 5 seconds … a radar site in Amarillo, Texas and a radio communications site in El Dorado, Arkansas. L3 Harris … including deployment of a new router … we have no indication that this was a cyberattack … disabled the same functionality on more than 60 other Juniper routers",
                True,
            ),
            s(
                ABC,
                ABC_U,
                "FAA halts router installation following nationwide ground stop, root cause of issue unknown",
            ),
        ],
    },
    "UA04": {
        "claim": "2026-11-17 美國政府要求國會撥款 501 億美元翻新航管：含 101 億數位架構、100 億興建 5 座新的整併航路管制中心（取代現有 22 座，最近一座建於 1969 年）、100 億興建或改善最多 140 座塔台等；2025 年 7 月已撥 125 億美元",
        "tokens": [
            "2026",
            "11",
            "17",
            "50.1",
            "501",
            "10.1",
            "101",
            "10",
            "100",
            "5",
            "22",
            "1969",
            "140",
            "12.5",
            "125",
            "2025",
            "7",
            "億",
        ],
        "sources": [
            s(
                DOT50,
                DOT50_U,
                "The Trump Administration is requesting $50.1 billion … $10.1 billion to complete a reliable digital architecture … $10 billion to build five new consolidated Air Route Traffic Control Centers (ARTCC), replacing the current 22 deteriorating ATRCCs–the last was built in 1969. $10 billion to build and improve up to 140 air traffic control towers … With $12.5 billion from the Working Families Tax Cut passed in July 2025",
                True,
            ),
            s(
                ABC,
                ABC_U,
                "from the $12.5 billion that was appropriated by Congress to an additional $50 billion that Duffy asked for in the wake of the ground stop",
            ),
        ],
    },
    "UA05": {
        "claim": "美國交通部退款規定：航空公司取消航班，不論原因，只要沒改搭、也沒主動接受抵用券或里程等替代補償，就有權拿回票款；要退現金或原付款方式（信用卡 7 個營業日內、其他 20 天內）；接受改搭就不能退",
        "tokens": ["7", "20", "2024"],
        "sources": [
            s(
                DOTR,
                DOTR_U,
                "You are entitled to a refund if the airline cancels a flight, regardless of the reason, and does not rebook you on a new flight or you do not proactively accept alternative compensation, such as a flight voucher or miles. … You are not entitled to a refund if you accept a rebooked flight … within seven business days … 20 calendar days … in cash or in the form of original payment",
                True,
            ),
            s(
                CFR,
                CFR_U,
                "Prompt refund means refunds made within 7 business days … for credit card purchases and within 20 calendar days … for cash, check, debit card, or other forms of purchases",
                True,
            ),
            s(
                NN,
                NN_U,
                "Examples of significant changes include departure or arrival times that are altered more than three hours domestically and six hours internationally",
            ),
        ],
    },
    "UA06": {
        "claim": "14 CFR 260：起飛或抵達時間變動，美國國內 3 小時以上、國際 6 小時以上算重大變更，不接受也可退票；規定適用飛美國、從美國出發或美國境內的定期航班，外國航空公司也包括在內",
        "tokens": ["3", "6", "260"],
        "sources": [
            s(
                CFR,
                CFR_U,
                "three hours or more for domestic itineraries and six hours or more for international itineraries … Covered carrier means an air carrier or a foreign air carrier operating to, from, or within the United States, conducting scheduled passenger service",
                True,
            ),
            s(
                NN,
                NN_U,
                "altered more than three hours domestically and six hours internationally",
            ),
        ],
    },
    "UA07": {
        "claim": "例外：被改成不同航班編號、並被改搭到該航班的情況，美國交通部自 2025-12-05 起暫不執行退款規定，2026-07-07 再延長；退款規則的修訂（Refund III）仍在進行",
        "tokens": ["2025", "12", "5", "2026", "7"],
        "sources": [
            s(
                FR26,
                FR26_U,
                "a flight assigned a different flight number than was active at the time of ticket purchase is considered a ``cancelled flight,'' … The Department is extending its discretion to not enforce these requirements",
                True,
            ),
            s(
                FR25B,
                FR25B_U,
                "The Department is exercising its discretion to not enforce the requirements in 14 CFR 260.6, 260.9 and 14 CFR 399.80(l)",
                True,
            ),
        ],
    },
    "UA08": {
        "claim": "美國交通部儀表板列出 9 家大航空「自己造成」的取消時的自願承諾：9 家保證等待 3 小時以上給餐券、8 家保證過夜住宿（Frontier 沒有）、0 家給現金賠償；不是航空公司造成的（如這次航管）不在承諾範圍",
        "tokens": ["9", "3", "8", "0"],
        "sources": [
            s(
                DASH,
                DASH_U,
                "Commitments airlines make when they cause a cancellation. … Meal or meal cash/voucher when the cancellation results in a wait of 3 hours or more … Complimentary hotel accommodations … FrontierNo … Cash compensation when the cancellation results in a wait of 3 hours or more … AlaskaNo | AllegiantNo | AmericanNo | DeltaNo | FrontierNo | HawaiianNo | JetBlueNo | SouthwestNo | UnitedNo",
                True,
            ),
            s(
                FR25,
                FR25_U,
                "voluntary commitments … to assist passengers affected by cancellations and significant delays that are controllable by the carrier. Those voluntary commitments are reflected on the Department's Delay and Cancellation Dashboard",
                True,
            ),
        ],
    },
    "UA09": {
        "claim": "2024 年拜登政府提案要航空公司對自身造成的延誤付現金（國內延誤 3 小時以上 200–300 美元、9 小時以上最高 775 美元）；川普政府 2025-11-17 在聯邦公報正式撤回",
        "tokens": ["2024", "3", "200", "300", "9", "775", "2025", "11", "17"],
        "sources": [
            s(
                FR25,
                FR25_U,
                "The Department is withdrawing the ANPRM on Airline Passenger Rights issued on December 11, 2024",
                True,
            ),
            s(
                CBS,
                CBS_U,
                "would have required airlines to pay passengers $200 to $300 for domestic delays lasting at least three hours, and up to $775 for flight delays lasting at least nine hours",
            ),
        ],
    },
    "UA10": {
        "claim": "歐盟 261/2004：航班取消原則上依距離賠 250／400／600 歐元，但業者能證明是無法避免的特殊情況可以不賠，航管決定屬於特殊情況；不論是否賠償，取消時仍要依等待時間提供餐食，需過夜時提供住宿",
        "tokens": ["261", "2004", "250", "400", "600", "1500", "3500"],
        "sources": [
            s(
                EU,
                EU_U,
                "EUR 250 for all flights of 1500 kilometres or less; EUR 400 … EUR 600 … shall not be obliged to pay compensation … if it can prove that the cancellation is caused by extraordinary circumstances … (15) Extraordinary circumstances should be deemed to exist where the impact of an air traffic management decision … meals and refreshments in a reasonable relation to the waiting time; hotel accommodation",
                True,
            ),
            s(
                YE,
                YE_U,
                "Examples of events defined as extraordinary circumstances are air traffic management decisions, political instability, adverse weather conditions and security risks … 250 1 500 km or less 400 … 600 More than 3 500 km",
                True,
            ),
        ],
    },
    "UA11": {
        "claim": "台灣：國內線遲延 15 分鐘、國際線 30 分鐘以上，航空公司要說明原因與處理方式；遲延逾 5 小時、乘客不接受安排，可退票且不收手續費（颱風等天候也適用、外籍航空飛台灣也適用）；應視情況免費提供必要飲食或膳宿；可歸責於航空公司的遲延，才負賠償或補償責任",
        "tokens": ["15", "30", "5", "108", "3", "4", "8", "2017"],
        "sources": [
            s(
                TW,
                TW_U,
                "致國內航線遲延十五分鐘以上、國際航線遲延三十分鐘以上者…應即向乘客詳實說明原因及處理方式。前項遲延時間逾五小時以上，且乘客未接受運送人安排者，得向原售票單位辦理退票，運送人不得收取退票手續費。…（二）必要之飲食或膳宿。…運送人對因可歸責於自己之事由遲延，致損害乘客權益者，應負賠償或補償責任。",
                True,
            ),
            s(
                CNA,
                CNA_U,
                "國內外航班延誤超過5小時，旅客若不接受航空公司安排，可選擇全額退票，航空公司不得收取手續費，颱風天等天候不可抗力因素也適用…無論是國籍航空或是外籍航空，只要降落在台灣的機場航班都適用",
            ),
        ],
    },
    "UAFX": {
        "claim": "本頻道試算（臺銀 2026-11-20 即期中價：美元 32.94、歐元 36.135）：501 億美元≈新台幣 1.65 兆；125 億美元≈4,100 億；歐盟賠償 250 歐元≈9 千、400 歐元≈1.4 萬、600 歐元≈2.2 萬；美國撤回提案 200 美元≈6,600、775 美元≈2.6 萬",
        "tokens": [
            "32.94",
            "36.135",
            "50.1",
            "501",
            "1.65",
            "兆",
            "12.5",
            "125",
            "4100",
            "4,100",
            "250",
            "9",
            "千", "9000", "9,000",
            "400",
            "1.4",
            "萬",
            "600",
            "2.2",
            "200",
            "6600",
            "6,600",
            "775",
            "2.6",
            "2026",
            "11",
            "20",
        ],
        "sources": [
            s(
                BOT,
                BOT_U,
                "美金 即期 32.865 / 33.015；歐元 即期 35.835 / 36.435（2026/11/20 17:01）",
                True,
            ),
            s(DOT50, DOT50_U, "$50.1 billion … $12.5 billion", True),
            s(EU, EU_U, "EUR 250 … EUR 400 … EUR 600", True),
        ],
        "exception": "本頻道試算：匯率與算式列於事實表，片中標明試算",
    },
}

F["UA03"]["claim"] += "；FAA 也說大型管制設施的維修通常在夜間做，這次是偏遠站點的例行更換，之後會重新評估施工時段"
F["UA03"]["sources"][0]["quote"] += " … Maintenance at major air traffic control facilities is typically conducted at night, when there's less traffic. This disruption was a result of a routine replacement at a remote facility … we will reevaluate when we do replacement/maintenance work."
F["UA10"]["claim"] += "；航班延誤時，依距離在 2、3、4 小時以上就要提供餐飲照顧；延誤 5 小時以上可選擇在 7 天內退回票款"
F["UA10"]["tokens"] += ["2", "3", "4", "5", "7"]
F["UA10"]["sources"][0]["quote"] += " … for two hours or more in the case of flights of 1500 kilometres or less; or (b) for three hours or more … (c) for four hours or more … when the delay is at least five hours … reimbursement within seven days"
F["UA12"] = {
    "claim": "14 CFR 260 也規定：付了錢但沒提供的加購服務（如 Wi-Fi、選位）要退費；托運行李遺失或嚴重延誤要退行李費——美國國內 12 小時內沒送到、國際直飛 12 小時以內的航線 15 小時、直飛超過 12 小時的航線 30 小時",
    "tokens": ["260", "12", "15", "30", "Wi-Fi"],
    "sources": [
        s(CFR, CFR_U, "carriers promptly refund consumers for: (a) Fees for ancillary services related to air travel that consumers paid for but were not provided; (b) Fees to transport checked bags that are lost or significantly delayed … within 12 hours of the last flight segment's arrival for domestic itineraries, within 15 hours … 12 hours or less in duration, and within 30 hours … more than 12 hours in duration", True),
        s(NN, NN_U, "the airline fails to provide extra services such as Wi-Fi or seat selection if the passenger paid for those services … within 12 hours of their domestic flight arriving at the gate or 15-30 hours for an international flight"),
    ],
}

F["UA03"]["claim"] += "；停飛期間部分無線電頻率和雷達訊號仍可使用，不是完全斷線"
F["UA03"]["sources"][0]["quote"] += " … certain radio frequencies and radar feeds remained operational … No, this was not a full outage. Some frequencies and radar feeds remained reliable."
F["UA07"]["claim"] = "例外：只是換了航班編號、旅客也成功改訂到新編號航班，而且沒有重大變更或延誤時，美國交通部自 2025-12-05 起暫緩執行相關退款與通知規定；2026-07-07 再延長一年到 2027-07-07；修改「航班取消」定義的規則修訂（Refund III）仍在進行"
F["UA07"]["tokens"] = ["2025", "12", "5", "2026", "7", "2027"]
F["UA07"]["sources"][0]["quote"] = "provided that the passenger is rebooked on a flight with a new number and the flight operates without any ``significant change or delay'' … This enforcement discretion is extended for 1-year from the date of this publication, expiring on July 7, 2027 … Refund III … aims to … modifying the definition of a flight cancellation"
F["UA09"]["claim"] = "2024-12-11 美國交通部發布航空旅客權益的預先規則制定通知（ANPRM），徵詢航空公司對自身可控延誤付現金的方案（媒體報導：國內延誤 3 小時以上 200–300 美元、9 小時以上最高 775 美元）；2025-11-17 在聯邦公報正式撤回這份徵詢"
F["UA09"]["tokens"] += ["12", "11"]
F["UA10"]["claim"] += "；取消前至少 14 天通知、或在期限內提供時間相近的改搭，可免賠；業者要證明特殊情況且已採取所有合理措施仍無法避免；取消時旅客可選退款或改搭，等候改搭期間提供餐飲，需過夜提供住宿與交通"
F["UA10"]["tokens"] += ["14"]
F["UA10"]["sources"][0]["quote"] += " … they are informed of the cancellation at least two weeks before the scheduled time of departure … could not have been avoided even if all reasonable measures had been taken … Article 8 Right to reimbursement or re-routing … transport between the airport and place of accommodation"
F["UA12"]["claim"] += "；行李費退款要先提出行李異常報告"
F["UA12"]["sources"][1]["quote"] += " … Passengers who file a mishandled baggage report may also receive a refund of their checked baggage fee"
F["UAFX"]["sources"].append(s(CBS, CBS_U, "$200 to $300 … up to $775"))

d = json.loads(P.read_text())
d["facts"].update(F)
P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("寫入", ", ".join(F))
