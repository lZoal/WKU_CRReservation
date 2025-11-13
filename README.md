DB설계 및 파일 설명

스키마 파일: create_tables.sql 파일은 DB 구조(4개 테이블: BUILDING, MAP_POINT, FLOOR, ROOM)를 담고 있습니다. 이 파일로 DB를 생성해야 합니다.
테스트 파일: db_test.py 파일은 Python 환경에서 DB 연결 상태와 데이터 개수를 확인하는 데 사용됩니다.

데이터 상태
BUILDING	완료	71개 건물 (ID 1~71)
MAP_POINT	완료	71개 건물의 임시 좌표 (터치 인식 기반)
FLOOR	완료	공학관/프라임관 10개 층 정보
ROOM	완료	공학관/프라임관 5개 층의 호실 및 시설 정보

총 데이터: 현재 71개 건물 데이터가 입력되어 있습니다.
내부 데이터: 공학관 및 프라임관 5개 층의 호실 정보가 FLOOR와 ROOM 테이블에 입력 완료되었습니다.

주의: MAP_POINT의 X/Y 좌표와 BUILDING.full_address는 임시 값이며, 최종 구현 시 실제 좌표로 업데이트가 필요합니다
