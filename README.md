# 실행 요약
uv venv
uv pip install -r requirements.txt



# 실행 명령어 예시

uv run python -m smartcampus_crawler.crawler `
  --room_kw 302 `
  --room_select "공학관 - 302강의실" `
  --out_csv ".\output\room_302.csv" `
  --no-headles