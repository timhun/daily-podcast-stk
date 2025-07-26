import requests
from datetime import datetime, timedelta

def test_twse_taiex_api(start_date_str, end_date_str):
    """
    測試 TWSE TAIEX API 指定日期範圍內每日資料回傳狀況。
    
    參數：
    - start_date_str, end_date_str：字串，格式 'YYYY-MM-DD'
    """
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    session = requests.Session()
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={date_str}&type=ALLBUT0999"
        try:
            resp = session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            stat = data.get("stat", "N/A")
            data_list = data.get("data", [])
            if stat != "OK":
                print(f"{current_date} - API狀態非OK: stat={stat}")
            elif not data_list:
                print(f"{current_date} - 無資料，stat={stat}")
            else:
                # 找出是否有 TAIEX 指數數據
                taiex_rows = [row for row in data_list if isinstance(row, list) and len(row) > 0 and row[0].strip() == "發行量加權股價指數"]
                if taiex_rows:
                    print(f"{current_date} - 有資料，包含 {len(taiex_rows)} 筆 TAIEX 指數資料")
                else:
                    print(f"{current_date} - 有資料但無 TAIEX 指數資料，stat={stat}")
        except Exception as e:
            print(f"{current_date} - 請求失敗: {e}")
        current_date += timedelta(days=1)

if __name__ == "__main__":
    # 範例測試日期範圍，可自行調整
    test_twse_taiex_api("2025-07-10", "2025-07-25")
