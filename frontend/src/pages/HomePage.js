// src/pages/HomePage.js
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import img1 from "../images/wkulogo.png";
import img2 from "../images/campus.png";

function HomePage() {
  const [buildings, setBuildings] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetch("http://localhost:8000/buildings")
      .then((res) => res.json())
      .then((data) => setBuildings(data))
      .catch((err) => console.error("건물 목록 불러오기 실패:", err));
  }, []);

  return (
    <div className="App">
      {/* 상단 바 (기존 디자인 유지) */}
      <div className="bar">
        <div className="left-section">
          <img className="img1" alt="wku logo" src={img1} />
          <span className="home">Home</span>
        </div>
        <div className="right-section">
          <button className="signup-btn" onClick={() => alert("SIGN UP 클릭!")}>
            SIGN UP
          </button>
          <button className="login-btn" onClick={() => alert("LOG IN 클릭!")}>
            LOG IN
          </button>
        </div>
      </div>

      {/* 메인 이미지 */}
      <img className="img2" alt="campus" src={img2} />

      {/* 박스 안에 건물 목록 표시 */}
      <div className="box" style={{ padding: "20px", textAlign: "left" }}>
        <h3>📌 건물 목록 (백엔드 데이터)</h3>

        {buildings.length === 0 ? (
          <p>불러오는 중...</p>
        ) : (
          <ul style={{ lineHeight: "1.8em", listStyle: "none", paddingLeft: 0 }}>
            {buildings.map((b) => (
              <li
                key={b.id}
                style={{ cursor: "pointer", marginBottom: "8px" }}
                onClick={() => navigate(`/rooms/${b.id}`)}
              >
                ✅ {b.name} ({b.code})
              </li>
            ))}
          </ul>
        )}
      </div>

      <footer className="bar1"></footer>
    </div>
  );
}

export default HomePage;
