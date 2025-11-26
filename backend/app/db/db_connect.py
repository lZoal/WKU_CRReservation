import psycopg2
from .db_config import DB_HOST, DB_NAME, DB_USER, DB_PASS

def get_conn():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception as e:
        print("❌ DB 연결 실패:", e)
        return None
