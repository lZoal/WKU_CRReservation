import pandas as pd
import math
from .timetable_repo import insert_timetable
from .db_connect import get_conn

# 🔥 강의실 ID 직접 입력
ROOM_ID = 1   # 나중에 자동화해줄 수 있음
CSV_PATH = "room_302.csv"

day_map = {2:1, 3:2, 4:3, 5:4, 6:5, 7:6}

def import_csv():
    df = pd.read_csv(CSV_PATH)

    for _, row in df.iterrows():
        if (isinstance(row["col_1"], float) and math.isnan(row["col_1"])) or row["col_1"] == "":
            continue

        period = int(row["col_1"])

        for col_idx, weekday in day_map.items():
            cell = row[f"col_{col_idx}"]

            if isinstance(cell, float) and math.isnan(cell):
                continue
            if str(cell).strip() == "":
                continue

            insert_timetable(ROOM_ID, period, weekday, str(cell))

    print("✅ CSV → PostgreSQL 업로드 완료!")

if __name__ == "__main__":
    import_csv()
