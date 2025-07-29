# scripts/check_tw_holiday.py

from workalendar.asia import Taiwan
from datetime import date

cal = Taiwan()
today = date.today()
is_holiday = not cal.is_working_day(today)

print("是否為假日：", is_holiday)
if is_holiday:
    print("::set-output name=is_holiday::true")
else:
    print("::set-output name=is_holiday::false")