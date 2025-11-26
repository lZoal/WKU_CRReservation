-- building table
CREATE TABLE building (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL
);

-- room table
CREATE TABLE room (
    id SERIAL PRIMARY KEY,
    building_id INT REFERENCES building(id),
    name VARCHAR(50) NOT NULL,
    floor INT,
    capacity INT,
    UNIQUE(building_id, name)
);

-- timetable (class schedule)
CREATE TABLE room_timetable (
    id SERIAL PRIMARY KEY,
    room_id INT REFERENCES room(id),
    period INT NOT NULL,
    weekday INT NOT NULL,  -- 1=Mon ~ 6=Sat
    raw_text TEXT
);

-- reservation table
CREATE TABLE reservation (
    id SERIAL PRIMARY KEY,
    room_id INT REFERENCES room(id),
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    user_name VARCHAR(50) NOT NULL
);
