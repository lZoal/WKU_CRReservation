from __future__ import annotations
from datetime import date, datetime, time
from typing import List, Tuple, Dict, Optional

from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from db.db_connect import get_conn   # DB 연결 가져오기

app = FastAPI(title="Smart Campus API", version="1.0")

# ================================================================
# CORS 설정
# ================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# Pydantic Models
# ================================================================
class ReservationIn(BaseModel):
    room_id: int
    date: str
    start: str
    end: str
    user: str

    @field_validator("date")
    def _valid_date(cls, v):
        try:
            date.fromisoformat(v)
        except:
            raise ValueError("invalid date format (expected YYYY-MM-DD)")
        return v

    @field_validator("start", "end")
    def _valid_time(cls, v):
        parse_hhmm(v)
        return v

    @field_validator("end")
    def _check_order(cls, v, info):
        start = info.data.get("start")
        if start and parse_hhmm(start) >= parse_hhmm(v):
            raise ValueError("end must be after start")
        return v


class ReservationOut(BaseModel):
    message: str
    room_id: int
    date: str
    start: str
    end: str


class TimelineBlock(BaseModel):
    start: str
    end: str
    status: str   # "free" or "occupied"


# ================================================================
# 유틸
# ================================================================
def parse_hhmm(s: str) -> time:
    try:
        hh, mm = s.split(":")
        return time(int(hh), int(mm))
    except:
        raise HTTPException(400, f"Invalid time format: {s}")


def overlap(a_s, a_e, b_s, b_e):
    s1, e1 = parse_hhmm(a_s), parse_hhmm(a_e)
    s2, e2 = parse_hhmm(b_s), parse_hhmm(b_e)
    return not (e1 <= s2 or e2 <= s1)


def merge_blocks(blocks: List[Tuple[str, str]]):
    parsed = sorted([(parse_hhmm(s), parse_hhmm(e)) for s, e in blocks], key=lambda x: x[0])
    merged = []
    for s, e in parsed:
        if not merged or s > merged[-1][1]:
            merged.append((s, e))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
    return [(a.strftime("%H:%M"), b.strftime("%H:%M")) for a, b in merged]


# ================================================================
# DB Helper (building, room, timetable, reservation 조회)
# ================================================================
def db_get_buildings():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT code, name FROM building;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def db_get_rooms(building=None, floor=None, min_capacity=None):
    conn = get_conn()
    cur = conn.cursor()

    sql = "SELECT id, name, building_id, floor, capacity FROM room WHERE 1=1"
    params = []

    if building:
        sql += " AND building_id = (SELECT id FROM building WHERE code = %s)"
        params.append(building)

    if floor:
        sql += " AND floor = %s"
        params.append(floor)

    if min_capacity:
        sql += " AND capacity >= %s"
        params.append(min_capacity)

    cur.execute(sql, params)
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return rows


def db_get_timetable(room_id: int):
    conn = get_conn()
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


def db_get_reservations(room_id: int, date_str: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT start_time, end_time, user_name
        FROM reservation
        WHERE room_id = %s AND date = %s
        ORDER BY start_time
    """, (room_id, date_str))
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return rows


def db_insert_reservation(room_id, date_str, start, end, user):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reservation(room_id, date, start_time, end_time, user_name)
        VALUES (%s, %s, %s, %s, %s)
    """, (room_id, date_str, start, end, user))
    conn.commit()
    cur.close()
    conn.close()


# ================================================================
# API
# ================================================================
@app.get("/")
def root():
    return {"hello": "world"}


@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.now().isoformat()}


# --------------------------------------------------------------
# 건물 목록 (DB)
# --------------------------------------------------------------
@app.get("/buildings")
def list_buildings():
    data = db_get_buildings()
    return [{"code": code, "name": name} for code, name in data]


# --------------------------------------------------------------
# 강의실 목록 (DB)
# --------------------------------------------------------------
@app.get("/rooms")
def list_rooms(
    building: Optional[str] = Query(None),
    floor: Optional[int] = Query(None),
    min_capacity: Optional[int] = Query(None)
):
    rows = db_get_rooms(building, floor, min_capacity)
    result = []
    for row_id, name, b_id, f, cap in rows:
        result.append({
            "id": row_id,
            "name": name,
            "building_id": b_id,
            "floor": f,
            "capacity": cap
        })
    return result


# --------------------------------------------------------------
# 지금 빈 강의실
# --------------------------------------------------------------
@app.get("/rooms/free-now")
def free_now(building: Optional[str] = None, min_capacity: Optional[int] = None):
    rooms = db_get_rooms(building, None, min_capacity)

    now = datetime.now().time()
    today = date.today().isoformat()

    free = []

    for room_id, name, building_id, floor, cap in rooms:
        # 예약 확인
        reservations = db_get_reservations(room_id, today)

        is_busy = False
        for s, e, _ in reservations:
            if parse_hhmm(s) <= now < parse_hhmm(e):
                is_busy = True
                break

        if not is_busy:
            free.append({
                "id": room_id,
                "name": name,
                "floor": floor,
                "capacity": cap
            })

    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(free),
        "free_rooms": free,
    }


# --------------------------------------------------------------
# 하루 타임라인 (DB 기반)
# --------------------------------------------------------------
@app.get("/rooms/{room_id}/timeline")
def timeline(room_id: int, date_str: Optional[str] = None):
    if not date_str:
        date_str = date.today().isoformat()

    timetable = db_get_timetable(room_id)
    reservations = db_get_reservations(room_id, date_str)

    # 수업 + 예약 병합
    occupied = []

    for period, weekday, raw in timetable:
        # 실제 수업 시간을 정해두지 않았으므로 (09:00~18:00 표시용)
        # raw_text에는 정확한 시간이 없으므로 정해진 규칙이 필요함
        # 우선 데모로 period 기반 시간 설정: 1교시=09:00~10:00 같은 규칙
        start_h = 9 + (period - 1)
        s = f"{start_h:02d}:00"
        e = f"{start_h+1:02d}:00"
        occupied.append((s, e))

    for s, e, _user in reservations:
        occupied.append((s, e))

    merged = merge_blocks(occupied)

    # free/occupied 구간 계산
    result = []
    cursor = "09:00"
    WORK_END = "18:00"

    for s, e in merged:
        if parse_hhmm(cursor) < parse_hhmm(s):
            result.append(TimelineBlock(start=cursor, end=s, status="free"))
        result.append(TimelineBlock(start=s, end=e, status="occupied"))
        cursor = e

    if parse_hhmm(cursor) < parse_hhmm(WORK_END):
        result.append(TimelineBlock(start=cursor, end=WORK_END, status="free"))

    return {
        "room_id": room_id,
        "date": date_str,
        "blocks": [b.model_dump() for b in result]
    }


# --------------------------------------------------------------
# 예약 (DB 저장)
# --------------------------------------------------------------
@app.post("/rooms/reserve", response_model=ReservationOut)
def reserve(payload: ReservationIn):

    # 1) 예약 충돌 DB에서 확인
    reservations = db_get_reservations(payload.room_id, payload.date)

    for s, e, u in reservations:
        if overlap(payload.start, payload.end, s, e):
            raise HTTPException(409, detail={
                "error": "conflict_with_reservation",
                "reservation_block": {"start": s, "end": e, "user": u}
            })

    # 2) 저장
    db_insert_reservation(payload.room_id, payload.date, payload.start, payload.end, payload.user)

    return ReservationOut(
        message="reserved",
        room_id=payload.room_id,
        date=payload.date,
        start=payload.start,
        end=payload.end,
    )
