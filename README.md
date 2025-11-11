
🏫 Smart Campus API (v0.3.0)

FastAPI 기반 스마트 캠퍼스 강의실 관리 데모 시스템
(빈 강의실 조회 · 일정 확인 · 예약 · 크롤러 CSV 주입)


⚙️ 1. 환경 준비
🧩 uv 가상환경 생성
cd WKU_CRReservation
uv venv
uv pip install -r backend/requirements.txt


이미 .venv가 있다면 이 단계 생략 가능

🌱 2. .env 파일 생성

.env.example 파일을 복사해서 .env를 만들어야 합니다.

# Windows PowerShell
Copy-Item .\env.example .env
# macOS/Linux
cp env.example .env


이후 .env 파일을 열고 아래 값들을 채워주세요 👇
BASE_URL	로그인 페이지 URL	https://intra.wku.ac.kr/SWupis/V005/login.jsp
TIMETABLE_URL	로그인 후 접근 가능한 “강의실 시간표” 직접 링크	https://intra.wku.ac.kr/SWupis/V005/lectureRoomTimetable.jsp
PORTAL_ID	원광대학교 포털 ID	wku20231234
PORTAL_PW	포털 비밀번호	password123!
HEADLESS	브라우저 표시 여부 (true = 숨김 / false = 표시)	false
🕷️ 3. 크롤러 실행
▶️ 강의실 시간표 수집 (예: 공학관 302호)

backend 폴더로 이동 후 실행

cd backend

uv run python -m smartcampus_crawler.crawler `
  --room_kw 302 `
  --room_select "공학관 - 302강의실" `
  --out_csv ".\smartcampus_crawler\room_302.csv" `
  --no-headless


루트에서 실행하려면 PYTHONPATH 지정 필요:

cd WKU_CRReservation
$env:PYTHONPATH="backend"
uv run python -m smartcampus_crawler.crawler --room_kw 302 --room_select "공학관 - 302강의실" --out_csv ".\backend\smartcampus_crawler\room_302.csv" --no-headless


실행 후 smartcampus_crawler/room_302.csv 파일이 생성됩니다.
이 CSV는 FastAPI API의 /admin/schedules/import-room-grid 엔드포인트로 주입되어
실제 시간표 정보로 반영됩니다.

🚀 4. FastAPI 서버 실행
# 루트에서 실행
uv run python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000


서버가 실행되면 Swagger 문서로 확인 가능
👉 http://localhost:8000/docs

📚 주요 API 엔드포인트
구분	경로	설명
헬스체크	/ , /healthz	서버 상태 확인
건물 목록	/buildings	건물 코드 및 층 리스트
강의실 목록	/rooms	필터링된 강의실 리스트
지금 빈 강의실	/rooms/free-now	현재 시각 기준 빈 강의실 조회
하루 타임라인	/rooms/{room_id}/timeline	특정 강의실의 일정 블록 조회
예약	/rooms/reserve	예약 요청(충돌 검사 포함)
CSV 주입	/admin/schedules/import-room-grid	크롤러 CSV를 시스템에 반영
🧪 cURL 테스트 예시
# 건물 목록
curl http://localhost:8000/buildings

# ENG 건물의 빈 방 (최소정원 20)
curl "http://localhost:8000/rooms/free-now?building=ENG&min_capacity=20"

# 1번 방 오늘 타임라인
curl "http://localhost:8000/rooms/1/timeline"

# 예약 요청
curl -X POST "http://localhost:8000/rooms/reserve" \
  -H "Content-Type: application/json" \
  -d '{"room_id":1,"date":"2025-11-11","start":"15:00","end":"16:00","user":"홍길동"}'

🧭 5. 디버깅 (VSCode)

1️⃣ CTRL + SHIFT + P → Python: Select Interpreter
→ .venv\Scripts\python.exe 선택
2️⃣ .vscode/launch.json 생성:

{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "🕷️ SmartCampus Crawler (debug)",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/backend/smartcampus_crawler/crawler.py",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend"
      },
      "args": [
        "--room_kw", "302",
        "--room_select", "공학관 - 302강의실",
        "--out_csv", "${workspaceFolder}/backend/smartcampus_crawler/room_302.csv",
        "--no-headless"
      ]
    },
    {
      "name": "🚀 FastAPI (Uvicorn)",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "backend.app.main:app",
        "--reload",
        "--host", "127.0.0.1",
        "--port", "8000"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend"
      },
      "console": "integratedTerminal"
    }
  ]
}


이제 F5 누르면 크롤러 또는 API를 디버그 모드로 단계별 실행 가능.

🧩 참고사항

.env 파일은 로그인 정보가 포함되므로 절대 외부 저장소에 올리지 마세요.

FastAPI의 예약 저장소는 메모리 기반입니다 → 서버 재시작 시 초기화됨.

실제 운영 시 PostgreSQL 같은 DB 연동 필요.

근무시간(09~18시) 기준은 main.py 내 상수 수정으로 확장 가능.

크롤러 동작 시 로그인 실패/버튼 미작동 시 error_*.png 스크린샷 자동 저장.

💬 실행 요약
# 1) 환경설정
cp env.example .env

# 2) 패키지 설치
uv pip install -r backend/requirements.txt

# 3) 크롤러 실행
cd backend
uv run python -m smartcampus_crawler.crawler --room_kw 302 --room_select "공학관 - 302강의실" --out_csv ".\smartcampus_crawler\room_302.csv" --no-headless

# 4) FastAPI 실행
uv run python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000