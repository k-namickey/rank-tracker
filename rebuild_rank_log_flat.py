import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# ========================
# 設定
# ========================
SPREADSHEET_NAME = "エステショップ・リスト のコピー"
SOURCE_SHEET_NAME = "rank_flat_clean"
OUTPUT_CSV = "rank_log.csv"

# ========================
# 認証
# ========================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name(
    "service_account.json", scope
)
gc = gspread.authorize(creds)

# ========================
# シート取得
# ========================
sh = gc.open(SPREADSHEET_NAME)
ws = sh.worksheet(SOURCE_SHEET_NAME)

# ========================
# データ取得
# ========================
rows = ws.get_all_values()
header = rows[0]
data = rows[1:]

df = pd.DataFrame(data, columns=header)

# ========================
# CSV 出力
# ========================
df.to_csv(OUTPUT_CSV, index=False)

print("OK:", OUTPUT_CSV, "を生成しました")

