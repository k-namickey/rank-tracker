import gspread
from google.oauth2.service_account import Credentials

SERVICE_ACCOUNT_FILE = "service_account.json"
SPREADSHEET_ID = "1cJd0AkbbV_8G6mQJQ0pn-Sib4ZuoMVT2ALuucilKt6k"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
sh = gc.open_by_key(SPREADSHEET_ID)

ws = sh.worksheet("master")
vals = ws.get_all_values()

print("===== master contents =====")
print(f"行数: {len(vals)}")
for i, row in enumerate(vals[:20], start=1):
    print(i, row)
