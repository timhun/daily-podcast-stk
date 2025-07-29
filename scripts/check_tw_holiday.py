# scripts/check_tw_holiday.py

from workalendar.asia import Taiwan
from datetime import date
import os

cal = Taiwan()
today = date.today()
is_holiday = not cal.is_working_day(today)

print("是否為假日：", is_holiday)

# 正確寫入到 GitHub Actions 的 output
output_path = os.environ.get("GITHUB_OUTPUT")
if output_path:
    with open(output_path, "a") as f:
        f.write(f"is_holiday={'true' if is_holiday else 'false'}\n")