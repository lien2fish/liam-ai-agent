"""把 ms-02（網購拆封就不能退？）的事實寫進 facts.json；重跑會覆蓋同 id。"""

import json
import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "facts.json"

CPA = "消費者保護法第19條"
CPA_U = "https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=J0170001&flno=19"
ER17 = "消費者保護法施行細則第17條"
ER17_U = "https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=J0170002&flno=17"
LT96 = "行政院消費者保護委員會 96-07-05 消保法字第0960005992號函"
LT96_U = "https://www.ey.gov.tw/Page/8F51FEE53AB45EA9/c095d76c-9ec4-44f2-98b8-70204d625f98"
LT100 = "行政院消費者保護委員會 100-05-17 消保法字第1000004336號函"
LT100_U = "https://www.ey.gov.tw/Page/8F51FEE53AB45EA9/66c629e5-a5e4-48a4-8fbd-c7e87a7ad043"
FAQ = "行政院消費者保護會 網路購物問答〈收受商品後7日內拆開包裝或使用商品，是否仍可解除〉"
FAQ_U = "https://cpc.ey.gov.tw/Page/BC16ACF0BBB9CCC2/2055825e-e262-47da-9f56-398a71c92c5b"
FAQ2 = "行政院消費者保護會 網路購物問答〈網路購物刷卡，商品有瑕疵怎麼辦〉"
FAQ2_U = "https://cpc.ey.gov.tw/Page/BC16ACF0BBB9CCC2/a280669e-411c-4d1f-a600-28e10120bf2e"
EXC = "通訊交易解除權合理例外情事適用準則第2條（104-12-31 發布）"
EXC_U = "https://law.moj.gov.tw/LawClass/LawAll.aspx?PCode=J0170012"
LP = "法律百科〈七日鑑賞期〉"
LP_U = "https://www.legis-pedia.com/dictionary/53"


def s(name, url, quote, official=False):
    return {"name": name, "url": url, "official": official, "quote": quote}


F = {
    "RT01": {
        "claim": "消費者向企業經營者以通訊交易或訪問交易購買（實體店面現場購物不在此條），收到商品後 7 天內，可退回商品或書面通知解除契約，不用說理由；期限內交運商品或發出書面即視為解除；一般從收到商品隔天起算（業者未提供解除資訊時另依第 3 項延後起算）",
        "tokens": ["7", "19"],
        "sources": [
            s(CPA, CPA_U, "通訊交易或訪問交易之消費者，得於收受商品或接受服務後七日內，以退回商品或書面通知方式解除契約，無須說明理由及負擔任何費用或對價。", True),
            s(CPA, CPA_U, "消費者於第一項及第三項所定期間內，已交運商品或發出書面者，契約視為解除。", True),
            s(FAQ2, FAQ2_U, "消費者得於收受商品之寄達翌日起算七日內，向廠商要求解除買賣契約", True),
        ],
    },
    "RT02": {
        "claim": "因檢查之必要而拆封或使用，解除權不消滅（是否必要個案判斷）；業者以定型化條款「一經拆封，不得退換」排除消費者檢查商品的權利，屬無效條款（仍受合理例外準則限制）",
        "tokens": ["17", "12", "7"],
        "sources": [
            s(ER17, ER17_U, "消費者因檢查之必要或因不可歸責於自己之事由，致其收受之商品有毀損、滅失或變更者，本法第十九條第一項規定之解除權不消滅。", True),
            s(LT96, LT96_U, "企業經營者自行訂立「一經拆封，不得退換」或「一旦購買後則無法換貨」之定型化契約條款，排除消費者檢查商品之權利……應屬無效之條款。", True),
            s(FAQ, FAQ_U, "通訊交易之消費者於收受商品後7日內，依消費者保護法第19條第1項規定得行使解除權", True),
        ],
    },
    "RT03": {
        "claim": "即使仍有解除權，商品若有毀損或減損，消費者仍應依民法第 259 條第 6 款，按比例償還減少的價值",
        "tokens": ["259", "6"],
        "sources": [
            s(LT100, LT100_U, "仍應依民法第259條第6款規定，就商品之毀損或減損而減少之價值，按比例償還其價額", True),
            s(FAQ, FAQ_U, "就商品之毀損或減損而減少之價值，按比例償還其價額", True),
        ],
    },
    "RT04": {
        "claim": "通訊交易的 7 天解除權有 7 類合理例外，須符合要件且經業者告知才排除：易於腐敗、保存期限較短或解約時即將逾期；依消費者要求所為之客製化給付；報紙、期刊或雜誌；經消費者拆封之影音商品或電腦軟體；非以有形媒介提供之數位內容或一經提供即完成之線上服務（經消費者事先同意始提供）；已拆封之個人衛生用品；國際航空客運服務",
        "tokens": ["7", "2", "104", "12", "31"],
        "sources": [
            s(EXC, EXC_U, "指通訊交易之商品或服務有下列情形之一，並經企業經營者告知消費者，將排除本法第十九條第一項解除權之適用", True),
            s(EXC, EXC_U, "四、經消費者拆封之影音商品或電腦軟體。……六、已拆封之個人衛生用品。七、國際航空客運服務。", True),
            s(LP, LP_U, "易於腐敗、保存期限較短或解約時即將逾期；依消費者要求所為之客製化給付；報紙、期刊或雜誌"),
        ],
    },
}

d = json.loads(P.read_text())
d["facts"].update(F)
P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print(len(F), "條")
