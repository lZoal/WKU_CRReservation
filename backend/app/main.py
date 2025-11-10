from __future__ import annotations
from datetime import date, datetime, time
from typing import List, Tuple, Dict, Optional

from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Smart Campus API", version="0.3.0")

# CORS: 리액트 개발 서버 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ────────────────────────────── 목업 데이터 ──────────────────────────────
# 건물 → 층
BUILDINGS: Dict[str, List[int]] = {
    "ENG": [1, 2, 3],
    "LIB": [3, 4, 5],
}

# 강의실 목록
ROOMS: List[Dict] = [
    {"id": 1, "name": "B101", "building": "ENG", "floor": 1, "capacity": 40, "occupied": False},
    {"id": 2, "name": "B202", "building": "ENG", "floor": 2, "capacity": 30, "occupied": True},
    {"id": 3, "name": "A303", "building": "LIB", "floor": 3, "capacity": 20, "occupied": False},
]

# 요일 키
WEEK = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# 수업 스케줄(점유)
SCHEDULES: Dict[int, Dict[str, List[Tuple[str, str]]]] = {
    1: {"mon": [("09:00", "10:30")], "wed": [("13:00", "14:30")]},
    2: {"tue": [("10:00", "12:00")], "thu": [("15:00", "16:00")]},
    3: {"fri": [("11:00", "12:00")]},
}

# 예약 저장소 (메모리)
# room_id -> "YYYY-MM-DD" -> [(start, end, user)]
RESERVATIONS: Dict[int, Dict[str, List[Tuple[str, str, str]]]] = {}

# ────────────────────────────── 모델 ──────────────────────────────
class ReservationIn(BaseModel):
    room_id: int
    date: str = Field(..., description="YYYY-MM-DD")
    start: str = Field(..., description="HH:MM")
    end: str = Field(..., description="HH:MM")
    user: str

    @field_validator("date")
    @classmethod
    def _date_valid(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except Exception:
            raise ValueError("invalid date format, expected YYYY-MM-DD")
        return v

    @field_validator("start", "end")
    @classmethod
    def _time_valid(cls, v: str) -> str:
        _ = parse_hhmm(v)
        return v

    @field_validator("end")
    @classmethod
    def _start_before_end(cls, v: str, info):
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
    status: str  # "occupied" | "free"

# ────────────────────────────── 유틸 ──────────────────────────────
def weekday_key(d: date) -> str:
    return WEEK[d.weekday()]


def parse_hhmm(s: str) -> time:
    try:
        hh, mm = s.split(":")
        return time(int(hh), int(mm))
    except Exception:
        raise HTTPException(400, f"invalid time format: {s} (expected HH:MM)")


def overlap(a_s: str, a_e: str, b_s: str, b_e: str) -> bool:
    s1, e1, s2, e2 = parse_hhmm(a_s), parse_hhmm(a_e), parse_hhmm(b_s), parse_hhmm(b_e)
    return not (e1 <= s2 or e2 <= s1)


def merge_blocks(blocks: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """겹치거나 맞닿는 구간 병합 (HH:MM 문자열 리스트)"""
    segs = sorted([(parse_hhmm(s), parse_hhmm(e)) for s, e in blocks], key=lambda x: x[0])
    merged: List[Tuple[time, time]] = []
    for s, e in segs:
        if not merged or s > merged[-1][1]:
            merged.append((s, e))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
    return [(m[0].strftime("%H:%M"), m[1].strftime("%H:%M")) for m in merged]


def busy_at(room_id: int, d: date, t: time) -> bool:
    """해당 시각(t)에 점유 중인지 (수업/예약 포함)"""
    wk = weekday_key(d)
    tstr = t.strftime("%H:%M")
    # 수업
    for s, e in SCHEDULES.get(room_id, {}).get(wk, []):
        if parse_hhmm(s) <= t < parse_hhmm(e):
            return True
    # 예약
    for s, e, _ in RESERVATIONS.get(room_id, {}).get(d.isoformat(), []):
        if parse_hhmm(s) <= t < parse_hhmm(e):
            return True
    return False

# ────────────────────────────── 기본 ──────────────────────────────
@app.get("/")
def root():
    return {"hello": "world"}


@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.now().isoformat()}

# ────────────────────────────── 건물 / 방 목록 ──────────────────────────────
@app.get("/buildings")
def list_buildings():
    """메인 지도/건물 선택용"""
    return [{"code": code, "floors": floors} for code, floors in BUILDINGS.items()]


@app.get("/rooms")
def list_rooms(
    building: Optional[str] = Query(None),
    floor: Optional[int] = Query(None, ge=1),
    only_free: bool = Query(False),
    min_capacity: Optional[int] = Query(None, ge=1),
):
    """층별 배치도/목록용 (주의: only_free=True 는 정적 occupied 플래그만 반영)"""
    items = ROOMS
    if building:
        items = [r for r in items if r["building"] == building]
    if floor is not None:
        items = [r for r in items if r["floor"] == floor]
    if min_capacity:
        items = [r for r in items if r["capacity"] >= min_capacity]
    if only_free:
        items = [r for r in items if not r["occupied"]]
    return items

# ────────────────────────────── 지금 빈 강의실 ──────────────────────────────
@app.get("/rooms/free-now", summary="Get free rooms (with filters)")
def free_now(
    building: Optional[str] = Query(None, description="건물 코드 예: ENG, LIB"),
    min_capacity: Optional[int] = Query(None, ge=1, description="최소 인원"),
):
    today = date.today()
    now_t = datetime.now().time()

    # 1차 필터 (정적 속성)
    candidates = ROOMS
    if building:
        candidates = [r for r in candidates if r["building"] == building]
    if min_capacity:
        candidates = [r for r in candidates if r["capacity"] >= min_capacity]

    # 2차 필터 (실제 점유 상태 반영: 수업+예약)
    free = [r for r in candidates if not busy_at(r["id"], today, now_t)]

    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(free),
        "free_rooms": free,
    }

# ────────────────────────────── 하루 타임라인 ──────────────────────────────
@app.get("/rooms/{room_id}/timeline")
def timeline(room_id: int, date_str: Optional[str] = Query(None, alias="date")):
    """
    달력/상세 일정용
    - occupied: 수업/예약
    - free: 09:00~18:00 기준 빈 시간(데모 계산)
    """
    room = next((r for r in ROOMS if r["id"] == room_id), None)
    if not room:
        raise HTTPException(404, "room not found")

    try:
        d = date.fromisoformat(date_str) if date_str else date.today()
    except Exception:
        raise HTTPException(400, "invalid date (expected YYYY-MM-DD)")

    wk = weekday_key(d)

    # 점유 모으기
    occupied: List[Tuple[str, str]] = []
    occupied += SCHEDULES.get(room_id, {}).get(wk, [])
    occupied += [(s, e) for (s, e, _u) in RESERVATIONS.get(room_id, {}).get(d.isoformat(), [])]

    # 겹침 병합
    occ_merged = merge_blocks(occupied)

    # 근무시간 기준 free 산출
    WORK_S, WORK_E = "09:00", "18:00"
    cursor = WORK_S
    blocks: List[TimelineBlock] = []

    for s, e in occ_merged:
        if parse_hhmm(cursor) < parse_hhmm(s):
            blocks.append(TimelineBlock(start=cursor, end=s, status="free"))
        blocks.append(TimelineBlock(start=s, end=e, status="occupied"))
        # cursor 는 더 뒤쪽으로 이동
        cursor = max(cursor, e, key=lambda x: parse_hhmm(x))

    if parse_hhmm(cursor) < parse_hhmm(WORK_E):
        blocks.append(TimelineBlock(start=cursor, end=WORK_E, status="free"))

    # 보기 좋게 정렬 (free 먼저 나오도록 가벼운 정렬 규칙 유지)
    blocks.sort(key=lambda b: (b.start, b.status != "free"))

    return {"room_id": room_id, "date": d.isoformat(), "blocks": [b.model_dump() for b in blocks]}

# ────────────────────────────── 예약 (데모) ──────────────────────────────
@app.post("/rooms/reserve", response_model=ReservationOut)
def reserve(payload: ReservationIn = Body(..., example={
    "room_id": 1,
    "date": "2025-11-10",
    "start": "15:00",
    "end": "16:00",
    "user": "정다은"
})):
    room = next((r for r in ROOMS if r["id"] == payload.room_id), None)
    if not room:
        raise HTTPException(404, "room not found")

    wk = weekday_key(date.fromisoformat(payload.date))

    # 수업 충돌
    for cs, ce in SCHEDULES.get(payload.room_id, {}).get(wk, []):
        if overlap(payload.start, payload.end, cs, ce):
            raise HTTPException(409, detail={
                "error": "conflict_with_class",
                "class_block": {"start": cs, "end": ce}
            })

    # 예약 충돌
    day_res = RESERVATIONS.setdefault(payload.room_id, {}).setdefault(payload.date, [])
    for rs, re, u in day_res:
        if overlap(payload.start, payload.end, rs, re):
            raise HTTPException(409, detail={
                "error": "conflict_with_reservation",
                "reservation_block": {"start": rs, "end": re, "user": u}
            })

    # 저장
    day_res.append((payload.start, payload.end, payload.user))

    return ReservationOut(
        message="reserved",
        room_id=payload.room_id,
        date=payload.date,
        start=payload.start,
        end=payload.end,
    )

# ────────────────────────────── 주의/한계 (운영 시 고려사항) ──────────────────────────────
# - 현재 예약 저장은 메모리 기반이라 멀티 프로세스/배포 환경에서 공유되지 않습니다.
# - 실제 운영에선 DB(예: PostgreSQL)와 트랜잭션/락, 고유 제약을 통해 중복 예약 방지 필요.
# - 학사 달력/공휴일, 야간/주말 시간대는 별도 설정으로 확장하세요.
