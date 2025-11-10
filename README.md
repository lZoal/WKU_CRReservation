아래 그대로 `README.md`에 붙여 쓰면 돼. (uv 기준 + Windows venv 대안 포함, step-by-step 압축)

# Smart Campus API (v0.3.0)

FastAPI 기반 **스마트 캠퍼스 강의실 관리 데모**
(빈 강의실 조회 · 일정 확인 · 예약 · 크롤러 CSV 주입)

---

## ✨ 주요 기능

* **건물/강의실 목록**: 건물 코드·층·수용인원 필터
* **지금 빈 강의실**: 수업+예약 반영해 실시간 빈 강의실 반환
* **하루 타임라인**: 09:00~18:00 기준 free/occupied 블록
* **예약(충돌 검사)**: 수업/기존 예약과 겹치면 409
* **크롤러 연동**: `room_302.csv` 등 그리드형 CSV → API 스케줄로 주입

---

## 🗂 프로젝트 구조(요약)

```
WKU_CRReservation/
├─ .venv/                         # (권장) 루트 단일 가상환경
├─ backend/
│  └─ app/
│     ├─ api/, services/, db/     # FastAPI 코드
│     └─ main.py                  # 앱 진입점 (app.main:app)
├─ smartcampus_crawler/           # 크롤러
│  ├─ crawler.py, login_probe.py
│  ├─ site_selectors.py
│  └─ room_302.csv                # 크롤링 결과(예시)
└─ frontend/                      # 프런트엔드(선택)
```

---

## ⚙️ 빠른 실행

### 1) uv 환경(권장)

```powershell
cd WKU_CRReservation
uv venv
uv pip install -r requirements.txt
# API 실행 (루트에서)
uv run python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Windows 표준 venv(대안)

```bat
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### 📚 API 문서

* Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
* ReDoc : [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🕷️ 크롤러 실행 예시

```powershell
uv run python -m smartcampus_crawler.crawler `
  --room_kw 302 `
  --room_select "공학관 - 302강의실" `
  --out_csv ".\smartcampus_crawler\room_302.csv" `
  --no-headless
```

> CSV는 **열: `col_1, 월, 화, 수, 목, 금, 토`** 형태(교시×요일 그리드).
> API가 이 CSV를 읽어 `SCHEDULES`로 변환/주입한다.

---

## 🔗 CSV → API 주입(통합 플로우)

1. **서버 실행**
   `uv run python -m uvicorn backend.app.main:app --reload`

2. **CSV 업로드/주입**

   * Swagger → `POST /admin/schedules/import-room-grid` 실행
     (기본 경로: `smartcampus_crawler/room_302.csv`, 기본 방: `B302`)

3. **동작 확인**

   * `GET /rooms` : 방 추가 확인
   * `GET /rooms/{id}/timeline?date=YYYY-MM-DD` : 수업 블록 확인
   * `GET /rooms/free-now?building=ENG&min_capacity=20` : 빈 강의실 확인

---

## 🔌 엔드포인트 요약

### 헬스체크

* `GET /` → `{ "hello": "world" }`
* `GET /healthz` → `{ "ok": true, "ts": "<ISO8601>" }`

### 건물/강의실

* `GET /buildings`
* `GET /rooms?building=ENG&floor=2&min_capacity=30&only_free=false`
  `only_free=true` 는 정적 플래그만 반영(실점유 아님)

### 지금 빈 강의실

* `GET /rooms/free-now?building=ENG&min_capacity=20`
  수업+예약 반영해 현재 시각 기준 빈 강의실 반환

### 하루 타임라인(09~18시)

* `GET /rooms/{room_id}/timeline?date=YYYY-MM-DD`
  `free/occupied` 블록 배열 반환

### 예약(충돌 검사)

* `POST /rooms/reserve`

```json
{
  "room_id": 1,
  "date": "2025-11-10",
  "start": "15:00",
  "end": "16:00",
  "user": "홍길동"
}
```

* 성공: 200 `{"message":"reserved", ...}`
* 충돌: 409 `conflict_with_class | conflict_with_reservation`

### (관리) CSV 주입

* `POST /admin/schedules/import-room-grid`

  * params: `csv_rel_path`, `room_name`, `building`, `floor`, `capacity`
  * 기본값: `smartcampus_crawler/room_302.csv`, `B302`, `ENG`, `3`, `40`

---

## 🧪 cURL 스니펫

```bash
# 건물
curl http://localhost:8000/buildings
# 빈 방(ENG, 정원>=20)
curl "http://localhost:8000/rooms/free-now?building=ENG&min_capacity=20"
# 1번 방 타임라인(오늘)
curl "http://localhost:8000/rooms/1/timeline"
# 예약
curl -X POST "http://localhost:8000/rooms/reserve" \
 -H "Content-Type: application/json" \
 -d '{"room_id":1,"date":"2025-11-10","start":"15:00","end":"16:00","user":"홍길동"}'
```

---

## 🛠️ 트러블슈팅(자주 나오는 문제)

* **`program not found: uvicorn`**
  → `uv pip install "uvicorn[standard]"` 후
  → `uv run python -m uvicorn backend.app.main:app --reload ...`

* **`VIRTUAL_ENV ... does not match ...` 경고**
  → 가상환경 하나만 사용(루트 `.venv` 유지, `backend/.venv` 제거).
  → 항상 루트에서 `uv run ...` 실행.

* **CSV 인코딩/경로 문제**
  → `smartcampus_crawler/room_302.csv` 위치/utf-8 확인.
  → 경로 바꾸려면 `POST /admin/schedules/import-room-grid`의 `csv_rel_path` 인자 사용.

* **409 충돌**
  → 정상 동작. 응답의 `detail`에 겹친 블록(start/end)이 담김.

---

## 📌 참고

* 데모는 **메모리 저장소**를 사용 → 서버 재시작 시 예약/로드된 스케줄 초기화
* 운영 시 DB(PostgreSQL 등) + 트랜잭션/유니크 제약으로 전환 필요
* 업무시간(09~18)은 데모 상수. 학사/야간/공휴일은 설정 확장

---

## 🧭 개발 메모

* 프런트(CRA/Vite)에서 개발 시 `http://localhost:8000`로 프록시 설정 권장
* 크롤러는 별도 실행 가능:

  ```powershell
  uv run python smartcampus_crawler/main.py
  ```

  실행 후 CSV를 다시 `import-room-grid`로 주입

---
