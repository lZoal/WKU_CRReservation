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
