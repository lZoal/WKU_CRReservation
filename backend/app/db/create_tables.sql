-- 건물
CREATE TABLE building (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL
);

-- 강의실
CREATE TABLE room (
    id SERIAL PRIMARY KEY,
    building_id INT REFERENCES building(id),
    name VARCHAR(50) NOT NULL,
    floor INT,
    capacity INT,
    UNIQUE(building_id, name)
);

-- 시간표 정보 (수업)
CREATE TABLE room_timetable (
    id SERIAL PRIMARY KEY,
    room_id INT REFERENCES room(id),
    period INT NOT NULL,
    weekday INT NOT NULL,  -- 1=월 ~ 6=토
    raw_text TEXT
);

-- 예약 정보
CREATE TABLE reservation (
    id SERIAL PRIMARY KEY,
    room_id INT REFERENCES room(id),
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    user_name VARCHAR(50) NOT NULL
);
