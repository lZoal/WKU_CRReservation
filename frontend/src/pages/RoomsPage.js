// frontend/src/pages/RoomsPage.js
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

function RoomsPage() {
  const { building_id } = useParams();
  const navigate = useNavigate();
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchRooms() {
      setLoading(true);
      try {
        const res = await fetch(
          `http://localhost:8000/rooms?building_id=${building_id}`
        );
        if (!res.ok) {
          throw new Error("API 오류");
        }
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
    <div>
      <h2>🏫 건물 ID {building_id} → 강의실 목록</h2>

      {loading && <p>불러오는 중...</p>}

      {!loading && rooms.length === 0 && (
        <p>등록된 강의실이 없습니다.</p>
      )}

      {!loading &&
        rooms.map((r) => (
          <div
            key={r.id}
            style={{
              padding: "12px",
              marginTop: "10px",
              border: "1px solid #bbb",
              borderRadius: "6px",
              cursor: "pointer",
              textAlign: "left",
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

export default RoomsPage;
