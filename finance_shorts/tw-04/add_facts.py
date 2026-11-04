"""把 tw-04（銀行防護與永豐異常轉帳）的事實寫進 facts.json；重跑會覆蓋同 id。"""

import json
import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "facts.json"

SP = "永豐銀行官網聲明 2026-11-03"
SP_U = "https://bank.sinopac.com/sinopacBT/about/introduction/announcement/content/20261103162136250000000000000741.html"
SPF = "永豐銀行客服中心常見問答：非約定轉帳限額"
SPF_U = "https://bank.sinopac.com/searchmb/FAQ/Content.aspx?sid=MMA&catID=MMA&subCatID=%E6%9C%8D%E5%8B%99%E5%8A%9F%E8%83%BD&no=269"
UD = "經濟日報 2026-11-03（廖珮君）金管會記者會"
UD_U = "https://udn.com/news/story/7239/9855068"
UD2 = "經濟日報 2026-11-04 永豐銀說明與股價"
UD2_U = "https://money.udn.com/money/story/5607/9855938"
LT = "自由財經 2026-11-03 金管會王允中說明"
LT_U = "https://ec.ltn.com.tw/article/breakingnews/5628238"
KN = "知新聞 2026-11-03 金管會說明"
KN_U = "https://www.knews.com.tw/news/0A5A3D38DF4CB550E0DA6D86EEA58A1C"
MM = "鏡週刊 2026-11-03"
MM_U = "https://www.mirrormedia.mg/story/20261103edi072"
TA = "太報／Yahoo 2026-11-04 北檢分案"
TA_U = "https://tw.news.yahoo.com/419%E5%90%8D%E5%AE%A2%E6%88%B6%E6%9C%AA%E7%99%BB%E5%85%A5app%E6%85%98%E9%81%AD%E7%9B%9C%E8%BD%89-%E6%B0%B8%E8%B1%90%E9%8A%80%E7%A8%8B%E5%BC%8F%E7%95%B0%E5%B8%B8%E5%8C%97%E6%AA%A2%E6%B4%BE%E9%BB%91%E9%87%91%E5%B0%88%E7%B5%84%E6%8F%AA%E5%85%83%E5%87%B6-032027748.html"
BS = "銀行公會《金融機構辦理電子銀行業務安全控管作業基準》115.01.07 版（第八條第二款第六目等）"
BS_U = "https://www.ba.org.tw/memberStandard/details?id=79"
BS2 = "植根法律網收錄 115.01.07 現行版作業基準"
BS2_U = "https://www.rootlaw.com.tw/LetterContent.aspx?LCode=31&SOID=249423"
CU = "歐盟法院新聞稿 No 147/26，2026-10-15，C-70/25"
CU_U = "https://curia.europa.eu/site/jcms/p1_1000088570"
TA2 = "太報 2026-11-04 受害者陳述"
FC = "金管會公告《個人網路銀行業務服務定型化契約應記載及不得記載事項》"
FC_U = "https://www.ey.gov.tw/File/FADFB96A59FC77CE"
MG = "兆豐銀行《個人網路銀行業務申請書暨服務契約》108 年 4 月版"
MG_U = "https://wwwfile.megabank.com.tw/upload/FF02/AB01P_%E5%80%8B%E4%BA%BA%E7%B6%B2%E8%B7%AF%E9%8A%80%E8%A1%8C%E6%A5%AD%E5%8B%99%E7%94%B3%E8%AB%8B%E6%9B%B8%E6%9A%A8%E6%9C%8D%E5%8B%99%E5%A5%91%E7%B4%84.pdf"
CD = "中央存款保險公司 存款保險常見問答"
CD_U = "https://www.cdic.gov.tw/main_deposit/faq.aspx?uid=59&pid=59"
CD2 = "中央存款保險公司公告：民國 100 年 1 月 1 日起保障提高為 300 萬元"
CD2_U = "https://www.cdic.gov.tw/main_insurance/docdetail.aspx?uid=19&pid=6&docid=279"
PS = "歐盟《支付服務指令》PSD2（EU）2015/2366 第 72～74 條"
PS_U = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32015L2366"
LS = "Lewis Silkin 2026-10-21 歐盟法院 C-70/25 判決解析"
LS_U = "https://www.lewissilkin.com/insights/2026/10/21/cjeu-confirms-immediate-refund-duty-for-unauthorised-payments-despite-customer-gr-102o62q"
BOT = "臺灣銀行 2026-11-04 15:08 牌告匯率（歐元即期買入 36.68、賣出 37.08，中間價約 36.88）"
BOT_U = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
BT = "今周刊 2026-01-06（引 165 打詐儀錶板）"
BT_U = "https://www.businesstoday.com.tw/article/category/183017/post/202601060042/"
SE = "三立新聞網 打詐儀表板報導（引 165 打詐儀錶板）"
SE_U = "https://www.setn.com/klist/635299"
CY = "鉅亨網 2025-03-13 銀行局王允中說明"
CY_U = "https://m.cnyes.com/news/id/5900180"
UA = "優分析：金管會修法第二類帳戶表徵"
UA_U = "https://uanalyze.com.tw/articles/4634747278"
CT = "工商時報 2026-07-07 銀行局王允中說明轉帳顯示戶名"
CT_U = "https://wantrich.chinatimes.com/news/20260707900598-420101"
CT2 = "工商時報 2026-07-07 同題報導"
CT2_U = "https://ctee.com.tw/news/20260707701823-430301"
TB = "台灣英文新聞 2026-07-28 臺灣企銀轉帳暫停鎖"
TB_U = "https://www.taiwannews.com.tw/zh/news/6409624"
TB2 = "工商時報 2026-07-30 臺企銀轉帳暫停鎖"
TB2_U = "https://www.ctee.com.tw/news/20260730700915-430201"
CB = "刑事警察局 165 報案方式"
CB_U = "https://www.cib.npa.gov.tw/ch/app/faq/view?id=18233&module=faq&serno=8306e5f3-6b7a-45e9-9d21-af24d4fac9af"
MEDIA = "金管會記者會與警方說法：查不到官方新聞稿原文，以多家媒體轉述交叉核對，片中不講原因定論"


def s(name, url, quote, official=False):
    return {"name": name, "url": url, "official": official, "quote": quote}


F = {
    "BK01": {
        "claim": "2026-11-03 永豐銀行新網銀異常：427 筆匯出、每筆約 10 萬元、總金額 4 千多萬元、影響 419 人；受款是北富銀同一帳戶",
        "tokens": ["2026", "11", "3", "427", "10", "419", "4000"],
        "exception": MEDIA,
        "sources": [
            s(LT, LT_U, "經銀行統計共有427筆匯出紀錄，每筆大約10萬元，總金額約4千多萬元，共計419人受到影響"),
            s(UD, UD_U, "419 people who had not logged into the new internet banking app；427 transfers；More than NT$40 million；one account at 北富銀"),
            s(KN, KN_U, "全部款項都進到北富銀的同一個帳戶"),
        ],
    },
    "BK02": {
        "claim": "永豐銀行聲明：2026/11/3 內部發現新網銀交易系統程式異常，造成部分帳戶不明轉出款項，已掌握原因並暫停服務，款項含手續費已全數返還；聲明未說明具體原因",
        "tokens": ["2026", "11", "3"],
        "sources": [
            s(SP, SP_U, "今日(2026/11/3)內部發現「新網銀交易系統」程式異常，造成部分帳戶不明轉出款項，目前已掌握原因並暫停服務，之後即無相同情事發生。同時為保障及維護客戶權益，款項包含手續費等，已全數返還予客戶。", True),
            s(UD2, UD2_U, "永豐銀僅說明新網銀程式異常；未說明程式異常的具體原因"),
        ],
    },
    "BK03": {
        "claim": "金管會：原因尚無法確認，系統錯誤或駭客入侵未定；永豐銀下架新版 App；11/12 前交重大偶發事件調查報告；是否裁罰不預設立場",
        "tokens": ["11", "12", "30", "7"],
        "exception": MEDIA,
        "sources": [
            s(LT, LT_U, "目前仍在釐清相關技術細節，尚無法確認實際原因；不會先預設立場、是否裁罰；應於發現後 30 分鐘內先以電話通報金管會；通報後7日內，將事件調查及清查結果、正式報送金管會"),
            s(UD, UD_U, "Sinopac must submit a major incident investigation report by November 12；take the new app offline"),
            s(UD2, UD2_U, "於11月12日前提交重大偶發事件調查報告"),
        ],
    },
    "BK04": {
        "claim": "客戶反映（當事人說法，未經官方證實）：沒開 App、沒收到驗證碼，交易紀錄卻顯示臉部掃描確認，轉出 10 萬元",
        "tokens": ["10"],
        "exception": "當事人說法，片中標明「客戶反映」，官方尚未證實",
        "sources": [
            s(MM, MM_U, "未登入網銀APP，也未收到簡訊驗證碼或身分確認通知，帳戶卻遭扣款10萬元；交易紀錄顯示經過臉部掃描確認"),
            s(UD2, UD2_U, "用戶反映：未開啟APP，卻遭以臉部掃描確認轉出"),
            s(TA2, TA_U, "未操作App、未收到登入或驗證碼通知，僅透過LINE官方帳號收到出帳通知"),
        ],
    },
    "BK05": {
        "claim": "北檢以他字案、由黑金專組檢察官偵辦，朝妨害電腦使用方向；目前報導未提到具名被告",
        "tokens": [],
        "exception": MEDIA,
        "sources": [
            s(TA, TA_U, "北檢受理後以「他」字案偵辦，朝妨害電腦使用罪方向查辦；指派檢肅黑金專組檢察官"),
            s("自由財經 2026-11-04 台北地檢署分案", "https://ec.ltn.com.tw/article/breakingnews/5628838", "全案將朝妨害電腦使用等罪偵辦，交由檢肅黑金專組檢察官"),
        ],
    },
    "BK06": {
        "claim": "受款帳戶已遭凍結，金管會稱資金不會流出；永豐銀先代墊返還",
        "tokens": [],
        "exception": MEDIA,
        "sources": [
            s(LT, LT_U, "該帳戶目前已遭凍結，資金不會流出"),
            s(KN, KN_U, "收款方銀行暫時凍結該異常帳戶，確保遭匯出的資金未被提走或轉移；代墊款項返還"),
        ],
    },
    "BK07": {
        "claim": "現行基準 115.01.07：非約定轉帳每筆要用中信賴等級以上、簡訊 OTP 或軟體 OTP 等確認身分；網際網路低風險交易每筆 5 萬、每天 10 萬、每月 20 萬；若採列舉的技術防護（含直接人臉辨識軌跡等），提供客戶確認交易內容並能防止身分確認資料與交易內容被竄改，可由銀行視風險提高，最高當日累計 300 萬。永豐客服問答寫 5／10／20 萬",
        "tokens": ["115", "5", "10", "20", "300", "五萬", "十萬", "二十萬", "三佰萬"],
        "sources": [
            s(BS, BS_U, "透過網際網路之低風險交易，以每一帳戶每筆不超過等值新臺幣五萬元、每天累積不超過等值新臺幣十萬元、每月累積不超過等值新臺幣二十萬元為限", True),
            s(BS, BS_U, "若採用之技術防護措施(如憑證簽章、晶片金融卡、非簡訊傳送之一次性密碼、視訊會議、第三人覆核、簡訊簡碼回傳、直接人臉辨識軌跡等…)…可由個別金融機構視風險承擔之能力斟酌予以適當提高，最高該轉出帳號不超過當日累計等值新臺幣三佰萬元為限", True),
            s(BS2, BS2_U, "最高該轉出帳號不超過當日累計等值新臺幣三佰萬元為限"),
            s(SPF, SPF_U, "單筆不得超過新臺幣5萬元，單一營業日累計不得超過新臺幣10萬元，每月累計不得超過新臺幣20萬元", True),
        ],
    },
    "BK08": {
        "claim": "現行基準：身分核驗資訊含固定密碼、生物特徵（指紋、臉部等）；裝置綁定發送一次性密碼或推播；用簡訊 OTP 做非約轉時，考量裝置可能遭植入惡意程式竊取 OTP，要加強防護（設備指定、推播確認等）",
        "tokens": [],
        "sources": [
            s(BS, BS_U, "身分核驗資訊：固定密碼、生物特徵(如指紋、臉部、虹膜、聲音、掌紋、靜脈、簽名等)", True),
            s(BS, BS_U, "若採用簡訊傳送一次性密碼並應用於非約定轉入帳戶轉帳交易者…考量客戶交易使用之電腦或行動裝置，可能遭植入惡意程式竊取OTP等身分核驗資訊或機敏資訊，應加強防護機制(如交易密碼驗證、設備指定、推播確認…)", True),
            s(BS, BS_U, "確認手機號碼或裝置綁定進行一次性密碼發送或推播等", True),
            s(BS2, BS2_U, "非約轉交易每筆應採用中信賴等級以上、簡訊OTP或軟體OTP等任一安全設計進行身分確認"),
        ],
    },
    "BK09": {
        "claim": "轉帳顯示受款人部分隱碼戶名（如王〇明），2025 年 9 月底開始推動，到 2026 年 5 月底 54 家金融機構上線",
        "tokens": ["2025", "9", "2026", "5", "54"],
        "exception": MEDIA,
        "sources": [
            s(CT, CT_U, "截至今年5月底,合計54家金融機構上線；自2025年9月底開始推動實施"),
            s(CT2, CT2_U, "於輸入完整受款帳號後，系統將自動顯示部分隱碼的受款人戶名（如「王〇明」）"),
        ],
    },
    "BK10": {
        "claim": "銀行接獲警示通報後，依管理辦法第 5 條應即暫停帳戶全部交易功能；第二類帳戶監控表徵增至 14 項，含短期頻繁開戶或設定約定帳號，列入不代表一定違法",
        "tokens": ["5", "14", "10", "30"],
        "exception": MEDIA,
        "sources": [
            s(CY, CY_U, "依「存款帳戶及其疑似不法或顯屬異常交易管理辦法」第 5 條規定，應即暫停帳戶全部交易功能；通報至凍結時間已可大幅縮短至 10 分鐘至半小時"),
            s(UA, UA_U, "第二類帳戶的監控表徵增至 14 項；列入第二類帳戶並不代表一定是不法"),
        ],
    },
    "BK11": {
        "claim": "2025 年台灣詐騙財損 893.26 億元、受理約 16.2 萬件（165 打詐儀錶板）；假投資是過去財損最大的類型",
        "tokens": ["2025", "893.26", "16.2", "893"],
        "exception": "警政署 165 打詐儀錶板頁面抓不到數字，以引用它的媒體交叉核對",
        "sources": [
            s(BT, BT_U, "2025年台灣整體詐騙財損金額達893.26億元；受理件數約16.2萬件；假投資詐騙過去財損最大"),
            s(SE, SE_U, "2025年全台詐騙受理件數高達16.2萬件，整體財損金額直逼新台幣900億元；若以財損數來看，則以假投資詐騙為最高"),
        ],
    },
    "BK12": {
        "claim": "應記載事項十四：第三人冒用或盜用，銀行接到通知前已發生的效力由銀行負責，但銀行能證明客戶有故意或過失、或通知核對資料後超過約定日數（不得少於 45 日）者除外；特殊事由從結束日起算，銀行有故意或過失則不適用逾期例外；鑑識費用由銀行負擔",
        "tokens": ["45", "四十五"],
        "sources": [
            s(FC, FC_U, "銀行或客戶於發現有第三人冒用或盜用…應立即以雙方約定方式通知他方。銀行接受前項通知前，對第三人使用該服務已發生之效力，由銀行負責。但有下列任一情形者，不在此限：(一)銀行能證明客戶有故意或過失。(二)銀行依雙方約定方式通知交易核對資料或帳單後超過oo日（此空白填載日不得少於四十五日）", True),
            s(FC, FC_U, "惟客戶有特殊事由（如長途旅行、住院等）致無法通知者，以該特殊事由結束日起算oo日…但銀行有故意或過失者，不在此限。針對第二項冒用、盜用事實調查所生之鑑識費用由銀行負擔", True),
            s(MG, MG_U, "銀行能證明客戶有故意或過失。二、銀行依前項雙方約定方式通知交易核對資料或帳單後超過四十五日", True),
        ],
    },
    "BK13": {
        "claim": "應記載事項十五：第三人破解銀行系統或利用漏洞的爭議，由銀行就該事實不存在負舉證責任；第三人入侵銀行資訊系統造成客戶損害由銀行負擔。十三：可歸責銀行的錯誤要立即更正",
        "tokens": [],
        "sources": [
            s(FC, FC_U, "第三人破解銀行資訊系統之保護措施或利用資訊系統之漏洞爭議，由銀行就該事實不存在負舉證責任。第三人入侵銀行資訊系統對客戶所造成之損害，由銀行負擔。", True),
            s(FC, FC_U, "前項服務因可歸責於銀行之事由而發生錯誤時，銀行應於知悉時，立即更正", True),
            s(MG, MG_U, "第三人入侵銀行資訊系統對客戶所造成之損害，由銀行負擔。", True),
        ],
    },
    "BK14": {
        "claim": "應記載事項十一、十二：客戶對密碼等身分工具負保管之責；銀行每筆交易處理完要通知客戶，客戶要核對，不符要在約定日數內（不得少於 45 日）通知",
        "tokens": ["45", "四十五"],
        "sources": [
            s(FC, FC_U, "客戶對銀行所提供之使用者代號、密碼、憑證及其它足以識別身分之工具，應負保管之責。", True),
            s(FC, FC_U, "銀行於每筆交易指示處理完畢後，以電子文件或雙方約定之方式通知客戶，客戶應核對其結果有無錯誤。如有不符，應於使用完成之日起○○日內（此空白填載日不得少於四十五日）", True),
            s(MG, MG_U, "客戶應核對其結果有無錯誤。如有不符，應於使用完成之日起四十五日內", True),
        ],
    },
    "BK15": {
        "claim": "存款保險：每人在同一家要保機構本金加利息最高 300 萬元，機構遭勒令停業才賠付；存款遭詐騙或盜領不屬存保責任範疇",
        "tokens": ["300", "三百", "350"],
        "sources": [
            s(CD, CD_U, "倘要保機構經其主管機關勒令停業，中央存保公司將在最高保額新臺幣300萬元內，依法賠付存款人", True),
            s(CD, CD_U, "民眾於金融機構之存款如遭詐騙或盜領，非屬中央存保公司履行保險責任範疇", True),
            s(CD, CD_U, "同一人在同一家機構的多筆存款合併計算；例如存款合計350萬元時，只賠付300萬元", True),
            s(CD2, CD2_U, "民國100年1月1日起，存款保險保障提高為新臺幣300萬元", True),
        ],
    },
    "BK16": {
        "claim": "歐盟 PSD2：客戶否認授權時銀行要舉證交易經驗證、記錄、未受技術故障影響，光有使用紀錄不足以證明；原則上知悉或獲通知後立即、最遲次一營業日結束前退款，合理懷疑詐欺並通報主管機關除外；遺失或被盜工具特定情形最多負擔 50 歐元（約新台幣 1,800 元，本頻道試算），詐欺或故意、重大過失違反義務則全負。歐盟法院 C-70/25（2026-10-15）：重大過失不免除立即退款義務，之後可就重大過失造成的損失向客戶求償；該案客戶在假網站輸入帳密，被轉約 700 歐元（約新台幣 2.6 萬元）",
        "tokens": ["2026", "10", "15", "50", "1800", "1,800", "700", "2.6"],
        "sources": [
            s(CU, CU_U, "gross negligence on the part of the customer does not exempt the payment service provider from the obligation to immediately refund the amount of an unauthorised payment transaction; may, however, subsequently seek reimbursement from the customer for losses resulting from the customer's gross negligence", True),
            s(CU, CU_U, "a website spoofing her bank's website where she entered her online banking service login details; a sum equivalent to approximately €700", True),
            s(PS, PS_U, "it is for the payment service provider to prove that the payment transaction was authenticated", True),
            s(PS, PS_U, "immediately, and in any event no later than by the end of the following business day", True),
            s(PS, PS_U, "up to a maximum of EUR 50", True),
            s(LS, LS_U, "提供者不能僅因認為客戶有重大過失而拒絕立即退款"),
            s(BOT, BOT_U, "歐元即期買入 36.68、賣出 37.08", True),
        ],
    },
    "BK17": {
        "claim": "部分銀行提供客戶自己鎖轉帳的功能，例如臺灣企銀轉帳暫停鎖可設 1 天到 3 個月，含非約定轉帳；各銀行功能不同",
        "tokens": ["1", "3"],
        "exception": "銀行產品功能，以媒體報導核對；片中只當例子，不推薦特定銀行",
        "sources": [
            s(TB, TB_U, "自主設定暫停行動銀行與網路銀行之臺幣轉帳與台灣Pay交易日期"),
            s(TB2, TB2_U, "最短1天、最長3個月"),
        ],
    },
    "BK18": {
        "claim": "遇到存款遭詐騙或盜領：報警、洽金融機構、撥 165；165 也可網路報案",
        "tokens": ["165"],
        "sources": [
            s(CB, CB_U, "遭遇詐騙洽詢相關事宜，可撥打165反詐騙諮詢專線諮詢、檢舉或報案", True),
            s(CD, CD_U, "存款如遭詐騙或盜領，非屬中央存保公司履行保險責任範疇，應儘速報警、洽詢金融機構或撥打165", True),
        ],
    },
    "BK19": {
        "claim": "2026-11-03 時間軸：上午 10:48 165 接獲客戶報案；中午刑事局已受理 68 案；接近中午 12 時餘永豐銀電話通知金管會",
        "tokens": ["2026", "11", "3", "10", "48", "68", "12", "165"],
        "exception": MEDIA,
        "sources": [
            s("中央社 2026-11-03 多帳戶遭盜轉", "https://www.cna.com.tw/news/asoc/202611030213.aspx", "上午10時48分接獲永豐銀行客戶報案；刑事局截至中午受理68案；下午北富銀表示已將相關帳戶列為禁提並暫停交易"),
            s("中央社 2026-11-03 金管會說明", "https://www.cna.com.tw/news/afe/202611030259.aspx", "金管會今天接近中午12時餘，接到永豐銀行電話通知"),
            s(MM, MM_U, "上午10時48分；中午12時16分正式受理68件"),
        ],
    },
    "BK21": {
        "claim": "銀行公會《作業基準》最新版本為 115 年 1 月 7 日（2026-01-07），公會網站 2026-02-05 發布",
        "tokens": ["2026", "1", "7", "115"],
        "sources": [
            s(BS, BS_U, "金融機構辦理電子銀行業務安全控管作業基準含附錄1150107；發布日期 2026/02/05", True),
            s(BS2, BS2_U, "中華民國115年1月7日 (現行法規)"),
        ],
    },
    "BK20": {
        "claim": "現行基準：直接驗證生物特徵要確認真人及本人，銀行依風險調整參數（近似率、錯誤接受率、錯誤拒絕率），要透過第三方檢測，確保不是變造或偽冒；應記載事項：密碼連續錯誤 3 到 5 次停用服務",
        "tokens": ["3", "5", "三", "五"],
        "sources": [
            s(BS, BS_U, "採用直接驗證生物特徵技術者，應確認真人及本人辦理…依據其風險承擔能力調整生物特徵參數(如近似率、錯誤接受率、錯誤拒絕率)…透過第三方依據ISO/IEC30107攻擊樣態逐一進行檢測，以確保感測器所擷取的生物特徵是客戶的真實生物特徵，而非經過變造或偽冒", True),
            s(FC, FC_U, "客戶輸入前項密碼連續錯誤達○次時（三次以上，五次以下），銀行電腦即自動停止客戶使用本契約之服務", True),
        ],
    },
}

d = json.loads(P.read_text())
d["facts"].update(F)
P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print(len(F), "條")
