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