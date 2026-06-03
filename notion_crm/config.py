import os

_LOCAL_SECRETS = os.path.expanduser("~/.config/notion_token")
if os.environ.get("NOTION_TOKEN"):
    NOTION_TOKEN = os.environ["NOTION_TOKEN"]
elif os.path.exists(_LOCAL_SECRETS):
    NOTION_TOKEN = open(_LOCAL_SECRETS).read().strip()
else:
    raise RuntimeError(
        "NOTION_TOKEN 未設定，請設定環境變數或建立 ~/.config/notion_token"
    )
NOTION_VERSION = "2022-06-28"

# Database IDs
DB = {
    # 客戶名單
    "seafood_customers": "374f4149-a6aa-8135-b9e4-dbb0cc2c2e0d",  # 🐟 鑫海產客戶名單
    "wine_customers": "374f4149-a6aa-816f-ab2c-fcaad143f5b4",  # 🍷 鑫酒藏客戶名單
    # 銷售紀錄
    "seafood_sales": "374f4149-a6aa-8102-baf5-ffa959227731",  # 🐟 鑫海產銷售紀錄
    "wine_sales": "374f4149-a6aa-81ec-8aef-de88095d8b6b",  # 🍷 鑫酒藏銷售紀錄
    # 主頁面
    "crm_page": "358f4149-a6aa-8088-9e6d-f5361d05cd12",  # 🏢 主頁面
}

# 各品牌對應的客戶名單 DB key
CUSTOMER_DB = {
    "seafood": "seafood_customers",
    "wine": "wine_customers",
}

# 各品牌客戶名單的姓名欄位名
CUSTOMER_NAME_FIELD = {
    "seafood": "姓名",
    "wine": "客戶姓名",
}

BRAND_LABELS = {
    "seafood": "🐟 鑫海產",
    "wine": "🍷 鑫酒藏",
    "tea": "🍵 鑫茶坊",
}

BRAND_PREFIXES = {
    "seafood": "HSP",
    "wine": "WIN",
    "tea": "TEA",
}
