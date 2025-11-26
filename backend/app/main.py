from __future__ import annotations

from datetime import date, datetime, time
from typing import List, Tuple, Dict, Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from app.db.db_connect import get_conn


app = FastAPI(title="Smart Campus API", version="1.0")


# ---------------------------------------------------------------
# 교시 → 시간 매핑 (학교 시간표에 맞게 수정 가능)
# ---------------------------------------------------------------
PERIOD_TIME: Dict[int, Tuple[str, str]] = {
    1: ("09:00", "09:50"),
    2: ("10:00", "10:50"),
    3: ("11:00", "11:50"),
    4: ("12:00", "12:50"),
    5: ("13:00", "13:50"),
    6: ("14:00", "14:50"),
    7: ("15:00", "15:50"),
    8: ("16:00", "16:50"),
    9: ("17:00", "17:50"),
}


# ---------------------------------------------------------------
# 수업 원시 텍스트 → "과목명 (분반)" 으로 변환
# ---------------------------------------------------------------
def parse_class_text(raw_text: str) -> str:
    """
    CSV raw_text 예시:
      (학부) 자동차진동제어및실습
      379052 / 01분반
      장일도 / 19명

    → "자동차진동제어및실습 (01분반)"
    """
    if not raw_text:
        return ""

    lines = [line.strip() for line in str(raw_text).splitlines() if line.strip()]
    if not lines:
        return ""

    # 1줄: "(학부) 자동차진동제어및실습" → "(학부)" 제거
    title_line = lines[0].replace("(학부)", "").strip()

    # 2줄: "379052 / 01분반" 에서 "01분반"만 추출
    part = ""
    if len(lines) >= 2 and "/" in lines[1]:
        try:
            part = lines[1].split("/")[1].strip()
        except Exception:
            part = ""

    if part:
        return f"{title_line} ({part})"
    return title_line


def get_class_blocks_from_db(room_id: int, d: date) -> List[Tuple[str, str, str]]:
    """
    room_timetable 에서 해당 날짜(요일)의 수업을
    (start, end, raw_text) 리스트로 반환.
    연속 교시(1,2,3...)이면서 같은 수업(raw_text 동일)이면
    중간 10분 쉬는시간을 포함해서 한 덩어리로 합친다.
    """
    # weekday 인코딩: room_timetable.weekday 가 1=월 ~ 6=토 라고 가정
    weekday = d.weekday() + 1

    sql = """
        SELECT period, raw_text
        FROM room_timetable
        WHERE room_id = %s
          AND weekday = %s
          AND TRIM(COALESCE(raw_text, '')) <> ''
        ORDER BY period
    """

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, (room_id, weekday))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return []

    # period, start, end, text 로 변환
    tmp = []
    for period, raw_text in rows:
        if period in PERIOD_TIME:
            start_str, end_str = PERIOD_TIME[period]
            tmp.append((period, start_str, end_str, raw_text))

    if not tmp:
        return []

    # 연속 교시이면서 같은 과목(raw_text 같음)이면 하나로 merge
    merged: List[Tuple[str, str, str]] = []

    cur_period, cur_start, cur_end, cur_text = tmp[0]
    for period, start_str, end_str, text in tmp[1:]:
        if period == cur_period + 1 and text == cur_text:
            # 연속 교시 + 같은 과목 → 끝 시간만 늘림 (09:00~09:50 + 10:00~10:50 => 09:00~10:50)
            cur_end = end_str
            cur_period = period
        else:
            merged.append((cur_start, cur_end, cur_text))
            cur_period, cur_start, cur_end, cur_text = period, start_str, end_str, text

    # 마지막 덩어리 추가
    merged.append((cur_start, cur_end, cur_text))

    return merged


# ---------------------------------------------------------------
# CORS (React 개발 서버 허용)
# ---------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------
class ReservationIn(BaseModel):
    room_id: int
    date: str
    start: str
    end: str
    user: str

    @field_validator("date")
    def _valid_date(cls, v: str):
        try:
            date.fromisoformat(v)
        except Exception:
            raise ValueError("invalid date format (expected YYYY-MM-DD)")
        return v

    @field_validator("start", "end")
    def _valid_time(cls, v: str):
        parse_hhmm(v)
        return v

    @field_validator("end")
    def _check_order(cls, v: str, info):
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
    status: str  # "free" 또는 "occupied"
    label: Optional[str] = None  # occupied 인 경우 수업/예약 정보


# ---------------------------------------------------------------
# Utils
# ---------------------------------------------------------------
def parse_hhmm(s) -> time:
    """"HH:MM" 문자열 또는 time 객체를 time 으로 변환"""
    if isinstance(s, time):
        return s
    s = str(s)
    try:
        hh, mm = s[:5].split(":")
        return time(int(hh), int(mm))
    except Exception:
        raise HTTPException(400, f"Invalid time format: {s}")


def overlap(a_s, a_e, b_s, b_e) -> bool:
    """[a_s, a_e) 와 [b_s, b_e) 가 겹치는지 여부"""
    s1, e1 = parse_hhmm(a_s), parse_hhmm(a_e)
    s2, e2 = parse_hhmm(b_s), parse_hhmm(b_e)
    return not (e1 <= s2 or e2 <= s1)


def merge_blocks(blocks: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """(start, end) 문자열 리스트를 받아 겹치거나 맞닿는 구간 병합"""
    parsed = sorted(
        [(parse_hhmm(s), parse_hhmm(e)) for s, e in blocks],
        key=lambda x: x[0],
    )
    merged: List[Tuple[time, time]] = []
    for s, e in parsed:
        if not merged or s > merged[-1][1]:
            merged.append((s, e))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
    return [(a.strftime("%H:%M"), b.strftime("%H:%M")) for a, b in merged]


# ---------------------------------------------------------------
# DB Helpers
# ---------------------------------------------------------------
def db_get_buildings():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, code, name FROM building ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def db_get_rooms(building_id=None, floor=None, min_capacity=None):
    conn = get_conn()
    cur = conn.cursor()

    sql = "SELECT id, building_id, name, floor, capacity FROM room WHERE 1=1"
    params: List = []

    if building_id is not None:
        sql += " AND building_id = %s"
        params.append(building_id)

    if floor is not None:
        sql += " AND floor = %s"
        params.append(floor)

    if min_capacity is not None:
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
    cur.execute(
        """
        SELECT period, weekday, raw_text
        FROM room_timetable
        WHERE room_id = %s
        ORDER BY weekday, period
        """,
        (room_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def db_get_reservations(room_id: int, date_str: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT start_time, end_time, user_name
        FROM reservation
        WHERE room_id = %s AND date = %s
        ORDER BY start_time
        """,
        (room_id, date_str),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def db_insert_reservation(room_id, date_str, start, end, user):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reservation (room_id, date, start_time, end_time, user_name)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (room_id, date_str, start, end, user),
    )
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------
# API
# ---------------------------------------------------------------
@app.get("/")
def root():
    return {"hello": "world"}


@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.now().isoformat()}


# ----------------- 건물 목록 ---------------------
@app.get("/buildings")
def list_buildings():
    rows = db_get_buildings()
    return [
        {"id": bid, "code": code, "name": name}
        for bid, code, name in rows
    ]


# ----------------- 강의실 목록 ---------------------
@app.get("/rooms")
def list_rooms(
    building_id: Optional[int] = Query(None),
    floor: Optional[int] = Query(None),
    min_capacity: Optional[int] = Query(None),
):
    rows = db_get_rooms(building_id, floor, min_capacity)
    return [
        {"id": rid, "building_id": bid, "name": name, "floor": fl, "capacity": cap}
        for rid, bid, name, fl, cap in rows
    ]


# ----------------- 원시 시간표 확인용 ---------------------
@app.get("/rooms/{room_id}/raw-timetable")
def raw_timetable(room_id: int):
    """
    room_timetable 테이블에 들어있는 원본 데이터 그대로 보기
    (요일/교시/텍스트)
    """
    rows = db_get_timetable(room_id)
    return [
        {
            "period": period,
            "weekday": weekday,
            "raw_text": raw_text,
        }
        for period, weekday, raw_text in rows
    ]


# ----------------- 지금 빈 강의실 ---------------------
@app.get("/rooms/free-now")
def free_now(
    building_id: Optional[int] = Query(None),
    min_capacity: Optional[int] = Query(None),
):
    rooms = db_get_rooms(building_id, None, min_capacity)

    now_t = datetime.now().time()
    today = date.today()
    today_str = today.isoformat()

    free_list = []

    for rid, bid, name, fl, cap in rooms:
        busy = False

        # 1) 수업 시간 체크 (DB)
        for s, e, _label in get_class_blocks_from_db(rid, today):
            if parse_hhmm(s) <= now_t < parse_hhmm(e):
                busy = True
                break

        # 2) 예약 시간 체크
        if not busy:
            reservations = db_get_reservations(rid, today_str)
            for s, e, _user in reservations:
                s_t = parse_hhmm(s)
                e_t = parse_hhmm(e)
                if s_t <= now_t < e_t:
                    busy = True
                    break

        if not busy:
            free_list.append(
                {
                    "id": rid,
                    "building_id": bid,
                    "name": name,
                    "floor": fl,
                    "capacity": cap,
                }
            )

    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(free_list),
        "free_rooms": free_list,
    }


# ----------------- 하루 타임라인 ---------------------
@app.get("/rooms/{room_id}/timeline")
def timeline(
    room_id: int,
    date_str: Optional[str] = Query(None, alias="date"),
):
    if not date_str:
        date_str = date.today().isoformat()

    target_date = date.fromisoformat(date_str)

    # 1) 이 날짜의 수업 (시간 + 과목명)
    class_blocks = get_class_blocks_from_db(room_id, target_date)
    # [(start, end, label), ...]

    classes_out = [
        {"start": s, "end": e, "label": label}
        for (s, e, label) in class_blocks
    ]

    # 2) 이 날짜의 예약
    reservations = db_get_reservations(room_id, date_str)
    reservations_out = []
    occupied_intervals: List[Tuple[str, str]] = []

    # 수업 시간은 무조건 occupied
    for s, e, label in class_blocks:
        occupied_intervals.append((s, e))

    # 예약도 occupied에 포함 + 상세 정보는 별도 배열
    for s, e, user in reservations:
        s_str = parse_hhmm(s).strftime("%H:%M")
        e_str = parse_hhmm(e).strftime("%H:%M")
        occupied_intervals.append((s_str, e_str))
        reservations_out.append({"start": s_str, "end": e_str, "user": user})

    # 겹치는 구간 병합 (수업 + 예약 전체)
    merged = merge_blocks(occupied_intervals)

    WORK_START = "09:00"
    WORK_END = "18:00"

    blocks: List[TimelineBlock] = []
    cursor = WORK_START

    for s, e in merged:
        # 빈 시간
        if parse_hhmm(cursor) < parse_hhmm(s):
            blocks.append(TimelineBlock(start=cursor, end=s, status="free"))

        # 점유 시간
        blocks.append(TimelineBlock(start=s, end=e, status="occupied"))
        cursor = e

    if parse_hhmm(cursor) < parse_hhmm(WORK_END):
        blocks.append(TimelineBlock(start=cursor, end=WORK_END, status="free"))

    return {
        "room_id": room_id,
        "date": date_str,
        "blocks": [b.model_dump() for b in blocks],
        "classes": classes_out,
        "reservations": reservations_out,
    }


# ----------------- 예약 (DB 저장) ---------------------
@app.post("/rooms/reserve", response_model=ReservationOut)
def reserve(payload: ReservationIn):
    """
    - 해당 room / date 의 기존 수업 및 예약과 겹치는지 검사
    - 겹치면 409 + 적절한 에러코드 반환
    """
    # 1) 수업과 겹치는지 확인
    target_date = date.fromisoformat(payload.date)
    class_blocks = get_class_blocks_from_db(payload.room_id, target_date)

    for cs, ce, label in class_blocks:
        if overlap(payload.start, payload.end, cs, ce):
            raise HTTPException(
                409,
                detail={
                    "error": "conflict_with_class",
                    "class_block": {
                        "start": cs,
                        "end": ce,
                        "label": label,
                    },
                },
            )

    # 2) 기존 예약과 겹치는지 확인
    reservations = db_get_reservations(payload.room_id, payload.date)

    for rs, re, user in reservations:
        if overlap(payload.start, payload.end, rs, re):
            raise HTTPException(
                409,
                detail={
                    "error": "conflict_with_reservation",
                    "reservation_block": {
                        "start": parse_hhmm(rs).strftime("%H:%M"),
                        "end": parse_hhmm(re).strftime("%H:%M"),
                        "user": user,
                    },
                },
            )

    # 3) 문제 없으면 INSERT
    db_insert_reservation(
        payload.room_id,
        payload.date,
        payload.start,
        payload.end,
        payload.user,
    )

    return ReservationOut(
        message="reserved",
        room_id=payload.room_id,
        date=payload.date,
        start=payload.start,
        end=payload.end,
    )
