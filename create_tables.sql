-- 기존의 모든 테이블(ROOM, FLOOR 등)을 삭제하고 2개 테이블로 새로 시작
DROP TABLE IF EXISTS ROOM, FLOOR, MAP_POINT, BUILDING CASCADE;

-- 1. BUILDING 테이블 (건물 정보)
CREATE TABLE BUILDING (
    build_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    abbr VARCHAR(10),
    description TEXT,
    full_address VARCHAR(255) NOT NULL -- 내비게이션 목적지 (임시로 건물명 입력)
);

-- 2. MAP_POINT 테이블 (지도 좌표 및 터치 정보)
CREATE TABLE MAP_POINT (
    point_id SERIAL PRIMARY KEY,
    build_id INT NOT NULL REFERENCES BUILDING(build_id),
    map_name VARCHAR(50) NOT NULL DEFAULT 'WKU Campus Map',
    x_coord INT NOT NULL, -- 지도 이미지 상의 X 좌표
    y_coord INT NOT NULL -- 지도 이미지 상의 Y 좌표
);

CREATE UNIQUE INDEX idx_building_point ON MAP_POINT (build_id);

-- 3. FLOOR 테이블 (건물의 층 정보)
CREATE TABLE FLOOR (
    floor_id SERIAL PRIMARY KEY,
    build_id INT NOT NULL REFERENCES BUILDING(build_id),
    floor_number INT NOT NULL, -- 층수 (예: 1, 2, 3). 지하층은 0, 옥상은 6 등으로 설정 가능
    map_image_url VARCHAR(255) -- 층별 도면 이미지 URL (선택 사항)
);

-- 4. ROOM 테이블 (강의실/호실 정보 - 화장실, 계단 포함)
CREATE TABLE ROOM (
    room_id SERIAL PRIMARY KEY,
    floor_id INT NOT NULL REFERENCES FLOOR(floor_id),
    room_number VARCHAR(10) NOT NULL, -- 호실 번호 (예: 101호, W.C)
    capacity INT, -- 수용 인원 (화장실, 계단 등은 NULL 또는 0)
    room_type VARCHAR(50) -- 강의실, 실험실, 연구실, 화장실, 계단 등
);

-- 인덱스 추가 (새로 추가된 테이블의 빠른 검색을 위해)
CREATE INDEX idx_floor_building ON FLOOR (build_id);
CREATE INDEX idx_room_floor ON ROOM (floor_id);