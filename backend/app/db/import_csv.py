import os
import pandas as pd
import math
from app.db.db_connect import get_conn

# CSV 파일들이 있는 디렉토리
CSV_DIR = r"C:\Users\dlaeh\WKU_CRReservation\backend\output\PRIME_building"

# 요일 매핑
day_map = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}


# -----------------------------------------------------------
# Building 생성 or 가져오기
# -----------------------------------------------------------
def get_or_create_building(building_name: str):
    conn = get_conn()
    cur = conn.cursor()

    # 외국어 building code 자동 생성
    building_code = building_name.replace("관", "").upper()

    # 1) 이미 있는지 확인
    cur.execute("SELECT id FROM building WHERE name = %s", (building_name,))
    row = cur.fetchone()

    if row:
        building_id = row[0]
    else:
        # 2) 없다면 생성
        cur.execute(
            "INSERT INTO building (code, name) VALUES (%s, %s) RETURNING id",
            (building_code, building_name)
        )
        building_id = cur.fetchone()[0]
        conn.commit()

    cur.close()
    conn.close()
    return building_id


# -----------------------------------------------------------
# Room 생성 or 가져오기
# -----------------------------------------------------------
def get_or_create_room(room_name: str, building_id: int):
    conn = get_conn()
    cur = conn.cursor()

    # 1) 기존 room 있는지 확인
    cur.execute("SELECT id FROM room WHERE name = %s AND building_id = %s",
                (room_name, building_id))
    row = cur.fetchone()

    if row:
        room_id = row[0]
    else:
        # 기본 floor, capacity는 0으로 설정
        cur.execute(
            "INSERT INTO room (building_id, name, floor, capacity) VALUES (%s, %s, %s, %s) RETURNING id",
            (building_id, room_name, 0, 0)
        )
        room_id = cur.fetchone()[0]
        conn.commit()

    cur.close()
    conn.close()
    return room_id


# -----------------------------------------------------------
# room_timetable 삽입
# -----------------------------------------------------------
def insert_timetable(room_id, period, weekday, raw_text):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO room_timetable (room_id, period, weekday, raw_text)
        VALUES (%s, %s, %s, %s)
    """, (room_id, period, weekday, raw_text))
    conn.commit()
    cur.close()
    conn.close()


# -----------------------------------------------------------
# CSV 하나 처리
# -----------------------------------------------------------
def import_csv_file(csv_path: str):
    print(f"[처리중] {csv_path}")

    # 파일명에서 building + room 추출
    filename = os.path.basename(csv_path)
    room_full_name = filename.replace(".csv", "")

    # 예: "프라임관 - 101대강의실"
    if " - " in room_full_name:
        building_name, room_name = room_full_name.split(" - ", 1)
    else:
        print(f"⚠ 파일명 형식 오류: {filename} (스킵)")
        return

    # 1) Building 자동 생성
    building_id = get_or_create_building(building_name)

    # 2) Room 자동 생성
    room_id = get_or_create_room(room_name, building_id)

    # 3) CSV 읽기
    df = pd.read_csv(csv_path)

    # 4) 시간표 삽입
    for _, row in df.iterrows():
        if str(row["col_1"]).strip() == "" or str(row["col_1"]).lower() == "nan":
            continue

        period = int(row["col_1"])

        for col_idx, weekday in day_map.items():
            cell = row[f"col_{col_idx}"]
            if str(cell).strip() in ("", "nan"):
                continue

            insert_timetable(room_id, period, weekday, str(cell))

    print(f"[완료] {room_full_name}")


# -----------------------------------------------------------
# 전체 CSV 처리
# -----------------------------------------------------------
def import_all_csv():
    print("\n=== CSV Import 시작 ===\n")

    for file in os.listdir(CSV_DIR):
        if file.lower().endswith(".csv"):
            path = os.path.join(CSV_DIR, file)
            import_csv_file(path)

    print("\n=== 모든 CSV 처리 완료! ===")


# 메인 실행
if __name__ == "__main__":
    import_all_csv()
