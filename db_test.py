import psycopg2

# ⚠️ DB 접속 정보: 본인의 PostgreSQL 설정에 맞게 반드시 수정해야 합니다.
DB_HOST = "localhost"   
DB_NAME = "wku_map_system" 
DB_USER = "postgres"    
DB_PASS = "thdckdrb" # ⬅️ 이 부분을 실제 비밀번호로 수정하세요!

def connect_db():
    """DB에 연결하고 연결 객체를 반환합니다."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        print("✅ PostgreSQL DB 연결 성공!")
        return conn
    except Exception as e:
        print(f"❌ DB 연결 실패! 비밀번호, 사용자 이름, DB 이름 등을 확인하세요.\n오류: {e}")
        return None

def fetch_data(conn, table_name):
    """지정된 테이블에서 데이터를 가져와 개수를 확인합니다."""
    if conn is None:
        return

    cur = conn.cursor()
    sql = f"SELECT COUNT(*) FROM {table_name};" # 간단히 개수만 확인하도록 수정
    cur.execute(sql)
    
    rows = cur.fetchone()
    print(f"\n--- {table_name} 데이터 확인 ---")
    print(f"총 {rows[0]}개의 행이 DB에서 검색되었습니다.")
    
    cur.close()

# 메인 실행 로직
conn = connect_db()
if conn:
    fetch_data(conn, "building")
    fetch_data(conn, "map_point")
    fetch_data(conn, "floor")
    fetch_data(conn, "room") # 모든 테이블을 확인합니다.
    
    conn.close()
    print("\n✅ DB 연결 종료.")