// frontend/src/pages/RoomTimelinePage.js
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

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

  // 타임라인 + 수업/예약 정보 불러오기
  useEffect(() => {
    async function fetchTimeline() {
      setLoading(true);
      setReserveMessage("");
      try {
        const res = await fetch(
          `http://localhost:8000/rooms/${room_id}/timeline?date=${date}`
        );
        if (!res.ok) {
          throw new Error("타임라인 API 오류");
        }
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
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          room_id: Number(room_id),
          date: date,
          start: reserveForm.start,
          end: reserveForm.end,
          user: reserveForm.user,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        if (
          errData &&
          errData.detail &&
          errData.detail.error === "conflict_with_reservation"
        ) {
          const blk = errData.detail.reservation_block;
          setReserveMessage(
            `이미 예약된 시간과 겹칩니다. (${blk.start}~${blk.end}, ${blk.user})`
          );
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
    <div>
      <h2>강의실 {room_id} 시간표 / 예약</h2>

      {/* 날짜 선택 */}
      <div style={{ margin: "10px 0" }}>
        <label>
          날짜 선택:&nbsp;
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
      </div>

      {/* 타임라인 블록 표시 */}
      <div style={{ marginTop: "15px" }}>
        <h3>하루 타임라인 (09:00 ~ 18:00)</h3>
        {loading && <p>불러오는 중...</p>}

        {!loading && blocks.length === 0 && <p>일정이 없습니다.</p>}

        {!loading &&
          blocks.map((b) => (
            <div
              key={`${b.start}-${b.end}-${b.status}`}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "8px 10px",
                marginBottom: "6px",
                borderRadius: "6px",
                border: "1px solid #ddd",
                backgroundColor:
                  b.status === "free" ? "#e8f5e9" : "#ffebee",
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
      <div style={{ marginTop: "20px" }}>
        <h3>수업 시간표</h3>
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
      <div style={{ marginTop: "20px" }}>
        <h3>예약 목록</h3>
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

      {/* 예약 폼 */}
      <div style={{ marginTop: "20px" }}>
        <h3>새 예약 등록</h3>
        <form onSubmit={handleReserveSubmit}>
          <div style={{ marginBottom: "8px" }}>
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
          <div style={{ marginBottom: "8px" }}>
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
          <div style={{ marginBottom: "8px" }}>
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
              padding: "8px 16px",
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
          <p style={{ marginTop: "8px", color: "#c62828" }}>
            {reserveMessage}
          </p>
        )}
      </div>
    </div>
  );
}

export default RoomTimelinePage;
