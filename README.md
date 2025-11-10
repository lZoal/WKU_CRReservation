# 실행 요약
uv venv
uv pip install -r requirements.txt



# crawler 실행 명령어 예시

uv run python -m smartcampus_crawler.crawler `
  --room_kw 302 `
  --room_select "공학관 - 302강의실" `
  --out_csv ".\output\room_302.csv" `
  --no-headles




  # Smart Campus API (v0.3.0)

FastAPI 기반 **스마트 캠퍼스 강의실 관리 데모 API**  
(빈 강의실 조회, 일정 확인, 예약 기능 포함)

---

## 🚀 실행 방법 (Windows)
```bat
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

## docs

http://localhost:8000/docs