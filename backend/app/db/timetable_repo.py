from .db_connect import get_conn

def insert_timetable(room_id, period, weekday, raw_text):
    conn = get_conn()
    if not conn: return
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO room_timetable(room_id, period, weekday, raw_text)
        VALUES (%s, %s, %s, %s)
    """, (room_id, period, weekday, raw_text))
    conn.commit()
    cur.close()
    conn.close()

def get_timetable(room_id):
    conn = get_conn()
    if not conn: return []
    cur = conn.cursor()
    cur.execute("""
        SELECT period, weekday, raw_text
        FROM room_timetable
        WHERE room_id = %s
        ORDER BY weekday, period
    """, (room_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows