// frontend/src/pages/BuildingsPage.js
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

function BuildingsPage() {
  const [buildings, setBuildings] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    async function fetchBuildings() {
      setLoading(true);
      try {
        const res = await fetch("http://localhost:8000/buildings");
        if (!res.ok) {
          throw new Error("API 오류");
        }
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
    <div>
      <h2>🏫 건물 목록</h2>

      {loading && <p>불러오는 중...</p>}

      {!loading && buildings.length === 0 && (
        <p>등록된 건물이 없습니다.</p>
      )}

      {!loading &&
        buildings.map((b) => (
          <div
            key={b.id}
            style={{
              padding: "15px",
              marginTop: "10px",
              border: "1px solid #ddd",
              borderRadius: "8px",
              cursor: "pointer",
              textAlign: "left",
            }}
            onClick={() => navigate(`/rooms/${b.id}`)}
          >
            <b>{b.name}</b> ({b.code})
          </div>
        ))}
    </div>
  );
}

export default BuildingsPage;
