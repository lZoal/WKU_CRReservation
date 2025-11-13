-- 1. BUILDING 테이블 (건물 정보)
CREATE TABLE BUILDING (
    build_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    abbr VARCHAR(10),
    description TEXT,
    full_address VARCHAR(255) NOT NULL
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
    floor_number INT NOT NULL, 
    map_image_url VARCHAR(255)
);

-- 4. ROOM 테이블 (강의실/호실 정보 - 화장실, 계단 포함)
CREATE TABLE ROOM (
    room_id SERIAL PRIMARY KEY,
    floor_id INT NOT NULL REFERENCES FLOOR(floor_id),
    room_number VARCHAR(10) NOT NULL,
    capacity INT, 
    room_type VARCHAR(50)
);
CREATE INDEX idx_floor_building ON FLOOR (build_id);
CREATE INDEX idx_room_floor ON ROOM (floor_id);