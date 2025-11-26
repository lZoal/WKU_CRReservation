import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

function BuildingsPage() {
  const [buildings, setBuildings] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetch("http://localhost:8000/buildings")
      .then((res) => res.json())
      .then((data) => setBuildings(data));
  }, []);

  return (
    <div style={{ padding: "20px" }}>
      <h2>🏫 건물 목록</h2>

      {buildings.map((b) => (
        <div
          key={b.id}
          style={{
            padding: "15px",
            marginTop: "10px",
            border: "1px solid #ddd",
            borderRadius: "8px",
            cursor: "pointer",
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
