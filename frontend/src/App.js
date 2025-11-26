// src/App.js
import React, { useEffect, useState } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  useNavigate,
  useParams,
} from "react-router-dom";

import img1 from "./images/wkulogo.png";
import img2 from "./images/campus.png";
import "./App.css";
import "./index.css";

/* ---------------- Home : 메인 화면 (건물 목록) ---------------- */
function HomePage() {
  const [buildings, setBuildings] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    async function fetchBuildings() {
      setLoading(true);
      try {
        const res = await fetch("http://localhost:8000/buildings");
        if (!res.ok) throw new Error("API 오류");
        const data = await res.json();
        setBuildings(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchBuildings();
  }, []);

  return (
    <div style={{ textAlign: "left" }}>
      <h3>📌 건물 목록 (백엔드 연동)</h3>

      {loading && <p>불러오는 중...</p>}

      {!loading && buildings.length === 0 && <p>등록된 건물이 없습니다.</p>}

      {!loading && buildings.length > 0 && (
        <ul style={{ marginTop: "10px", paddingLeft: 0, listStyle: "none" }}>
          {buildings.map((b) => (
            <li
              key={b.id}
              style={{
                padding: "8px 10px",
                marginBottom: "6px",
                borderRadius: "6px",
                border: "1px solid #ddd",
                cursor: "pointer",
              }}
              onClick={() => navigate(`/rooms/${b.id}`)}
            >
              <b>{b.name}</b> ({b.code})
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ---------------- Rooms : 건물별 강의실 목록 ---------------- */
function RoomsPage() {
  const { building_id } = useParams();
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    async function fetchRooms() {
      setLoading(true);
      try {
        const res = await fetch(
          `http://localhost:8000/rooms?building_id=${building_id}`
        );
        if (!res.ok) throw new Error("API 오류");
        const data = await res.json();
        setRooms(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchRooms();
  }, [building_id]);

  return (
    <div style={{ textAlign: "left" }}>
      <h3>🏫 건물 ID {building_id} → 강의실 목록</h3>

      {loading && <p>불러오는 중...</p>}

      {!loading && rooms.length === 0 && <p>등록된 강의실이 없습니다.</p>}

      {!loading &&
        rooms.map((r) => (
          <div
            key={r.id}
            style={{
              padding: "10px",
              marginTop: "8px",
              borderRadius: "6px",
              border: "1px solid #bbb",
              cursor: "pointer",
            }}
            onClick={() => navigate(`/rooms/${r.id}/timeline`)}
          >
            <b>{r.name}</b>
            {r.floor !== null && r.floor !== 0 && ` / ${r.floor}층`}
            {" / "}
            정원 {r.capacity}명
          </div>
        ))}
    </div>
  );
}

/* ---------------- Timeline : 하루 시간표 + 수업/예약 + 예약등록 ---------------- */
function RoomTimelinePage() {
  const { room_id } = useParams();
  const [date, setDate] = useState(() => {
    const today = new Date();
    return today.toISOString().slice(0, 10); // YYYY-MM-DD
  });

  const [blocks, setBlocks] = useState([]);
  const [classes, setClasses] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(false);

  const [reserveForm, setReserveForm] = useState({
    start: "",
    end: "",
    user: "",
  });
  const [reserveMessage, setReserveMessage] = useState("");

  // 타임라인 / 수업 / 예약 불러오기
  useEffect(() => {
    async function fetchTimeline() {
      setLoading(true);
      setReserveMessage("");
      try {
        const res = await fetch(
          `http://localhost:8000/rooms/${room_id}/timeline?date=${date}`
        );
        if (!res.ok) throw new Error("타임라인 API 오류");

        const data = await res.json();
        setBlocks(data.blocks || []);
        setClasses(data.classes || []);
        setReservations(data.reservations || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchTimeline();
  }, [room_id, date]);

  const handleReserveChange = (e) => {
    const { name, value } = e.target;
    setReserveForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleReserveSubmit = async (e) => {
    e.preventDefault();
    setReserveMessage("");

    if (!reserveForm.start || !reserveForm.end || !reserveForm.user) {
      setReserveMessage("시작/종료 시간과 예약자 이름을 모두 입력하세요.");
      return;
    }

    try {
      const res = await fetch("http://localhost:8000/rooms/reserve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room_id: Number(room_id),
          date,
          start: reserveForm.start,
          end: reserveForm.end,
          user: reserveForm.user,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        if (errData && errData.detail) {
          if (errData.detail.error === "conflict_with_reservation") {
            const blk = errData.detail.reservation_block;
            setReserveMessage(
              `이미 예약된 시간과 겹칩니다. (${blk.start}~${blk.end}, ${blk.user})`
            );
          } else if (errData.detail.error === "conflict_with_class") {
            const blk = errData.detail.class_block;
            setReserveMessage(
              `수업 시간과 겹칩니다. (${blk.start}~${blk.end}, ${blk.label})`
            );
          } else {
            setReserveMessage("예약 중 오류가 발생했습니다.");
          }
        } else {
          setReserveMessage("예약 중 오류가 발생했습니다.");
        }
        return;
      }

      setReserveMessage("예약이 완료되었습니다.");
      setReserveForm({ start: "", end: "", user: "" });

      // 예약 성공 후 타임라인 다시 불러오기
      const tlRes = await fetch(
        `http://localhost:8000/rooms/${room_id}/timeline?date=${date}`
      );
      const tlData = await tlRes.json();
      setBlocks(tlData.blocks || []);
      setClasses(tlData.classes || []);
      setReservations(tlData.reservations || []);
    } catch (err) {
      console.error(err);
      setReserveMessage("예약 중 오류가 발생했습니다.");
    }
  };

  return (
    <div style={{ textAlign: "left" }}>
      <h3>강의실 {room_id} 시간표 / 예약</h3>

      {/* 날짜 선택 */}
      <div style={{ margin: "8px 0 12px" }}>
        <label>
          날짜 선택:&nbsp;
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
      </div>

      {/* 타임라인 */}
      <div style={{ marginTop: "8px" }}>
        <h4>하루 타임라인 (09:00 ~ 18:00)</h4>
        {loading && <p>불러오는 중...</p>}
        {!loading && blocks.length === 0 && <p>일정이 없습니다.</p>}

        {!loading &&
  blocks.map((b, idx) => (
    <div
      key={`${b.start}-${b.end}-${b.status}-${idx}`}
      style={{
        display: "flex",
        justifyContent: "space-between",
        padding: "6px 10px",
        marginBottom: "4px",
        borderRadius: "6px",
        border: "1px solid #ddd",
        backgroundColor:
          b.status === "free" ? "#e8f5e9" : "#ffebee",
        cursor: b.status === "free" ? "pointer" : "default",
      }}
      onClick={() => {
        // free 블록일 때만 자동 채우기
        if (b.status !== "free") return;

        setReserveForm((prev) => ({
          ...prev,
          start: b.start,
          end: b.end,
        }));
        setReserveMessage(
          `선택한 빈 시간 (${b.start} ~ ${b.end}) 으로 예약 시간이 설정되었습니다.`
        );
      }}
    >
      <span>
        {b.start} ~ {b.end}
      </span>
      <span>
        {b.status === "free" ? "비어 있음" : "수업/예약 있음"}
      </span>
    </div>
  ))}

      </div>

      {/* 수업 목록 */}
      <div style={{ marginTop: "16px" }}>
        <h4>수업 시간표</h4>
        {classes.length === 0 ? (
          <p>등록된 수업이 없습니다.</p>
        ) : (
          <ul style={{ paddingLeft: "18px" }}>
            {classes.map((c, idx) => (
              <li key={idx}>
                {c.start} ~ {c.end} : {c.label}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 예약 목록 */}
      <div style={{ marginTop: "16px" }}>
        <h4>예약 목록</h4>
        {reservations.length === 0 ? (
          <p>등록된 예약이 없습니다.</p>
        ) : (
          <ul style={{ paddingLeft: "18px" }}>
            {reservations.map((r, idx) => (
              <li key={idx}>
                {r.start} ~ {r.end} : {r.user}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 예약 입력 폼 */}
      <div style={{ marginTop: "16px" }}>
        <h4>새 예약 등록</h4>
        <form onSubmit={handleReserveSubmit}>
          <div style={{ marginBottom: "6px" }}>
            <label>
              시작 시간:&nbsp;
              <input
                type="time"
                name="start"
                value={reserveForm.start}
                onChange={handleReserveChange}
              />
            </label>
          </div>
          <div style={{ marginBottom: "6px" }}>
            <label>
              종료 시간:&nbsp;
              <input
                type="time"
                name="end"
                value={reserveForm.end}
                onChange={handleReserveChange}
              />
            </label>
          </div>
          <div style={{ marginBottom: "6px" }}>
            <label>
              예약자 이름:&nbsp;
              <input
                type="text"
                name="user"
                value={reserveForm.user}
                onChange={handleReserveChange}
              />
            </label>
          </div>
          <button
            type="submit"
            style={{
              padding: "6px 14px",
              borderRadius: "6px",
              border: "none",
              backgroundColor: "#42748d",
              color: "white",
              cursor: "pointer",
            }}
          >
            예약하기
          </button>
        </form>

        {reserveMessage && (
          <p style={{ marginTop: "6px", color: "#c62828" }}>{reserveMessage}</p>
        )}
      </div>
    </div>
  );
}

/* ---------------- 전체 레이아웃(App): 기존 디자인 유지 ---------------- */
function App() {
  return (
    <Router>
      <div className="App">
        {/* 상단 bar 그대로 사용 */}
        <div className="bar">
          <div className="left-section">
            <img className="img1" alt="" src={img1} />
            <span className="home">Home</span>
          </div>
          <div className="right-section">
            <button
              className="signup-btn"
              onClick={() => alert("SIGN UP 클릭!")}
            >
              SIGN UP
            </button>
            <button
              className="login-btn"
              onClick={() => alert("LOGIN 클릭!")}
            >
              LOG IN
            </button>
          </div>
        </div>

        {/* 캠퍼스 이미지 그대로 */}
        <img className="img2" alt="" src={img2} />

        {/* 여기 box 안에 라우팅된 내용이 들어감 */}
        <div className="box">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/rooms/:building_id" element={<RoomsPage />} />
            <Route path="/rooms/:room_id/timeline" element={<RoomTimelinePage />} />
          </Routes>
        </div>

        <footer className="bar1"></footer>
      </div>
    </Router>
  );
}

export default App;
