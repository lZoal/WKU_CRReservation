// src/pages/TimelinePage.js
import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";

function formatToday() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function TimelinePage() {
  const { roomId } = useParams();
  const [dateStr, setDateStr] = useState(formatToday());
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(false);

  // 날짜나 roomId 바뀔 때마다 타임라인 불러오기
  useEffect(() => {
    if (!roomId || !dateStr) return;

    setLoading(true);
    fetch(`http://localhost:8000/rooms/${roomId}/timeline?date=${dateStr}`)
      .then((res) => res.json())
      .then((data) => {
        setTimeline(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("타임라인 불러오기 실패:", err);
        setLoading(false);
      });
  }, [roomId, dateStr]);

  return (
    <div style={{ padding: "20px" }}>
      <h2>📅 강의실 {roomId} 일정</h2>
      <p>
        <Link to="/">← 홈</Link>
      </p>

      <div style={{ marginBottom: "10px" }}>
        <label>
          날짜 선택:{" "}
          <input
            type="date"
            value={dateStr}
            onChange={(e) => setDateStr(e.target.value)}
          />
        </label>
      </div>

      {loading && <p>불러오는 중...</p>}

      {!loading && !timeline && <p>데이터가 없습니다.</p>}

      {!loading && timeline && (
        <>
          {/* 1) 타임라인 블록 (free / occupied) */}
          <h3>⏱ 시간대별 상태</h3>
          {timeline.blocks.length === 0 ? (
            <p>일정이 없습니다.</p>
          ) : (
            <ul style={{ listStyle: "none", paddingLeft: 0 }}>
              {timeline.blocks.map((b, idx) => (
                <li
                  key={idx}
                  style={{
                    margin: "6px 0",
                    padding: "4px 8px",
                    borderRadius: "4px",
                    backgroundColor:
                      b.status === "occupied" ? "#ffdddd" : "#ddffdd",
                  }}
                >
                  {b.start} ~ {b.end} —{" "}
                  {b.status === "occupied" ? "수업/예약" : "빈 시간"}
                </li>
              ))}
            </ul>
          )}

          {/* 2) 오늘 수업 목록 (백엔드 classes 필드 이용) */}
          <h3>📚 오늘 수업 목록</h3>
          {timeline.classes && timeline.classes.length > 0 ? (
            <ul>
              {timeline.classes.map((c, idx) => (
                <li key={idx}>
                  {c.start} ~ {c.end} : {c.label}
                </li>
              ))}
            </ul>
          ) : (
            <p>등록된 수업이 없습니다.</p>
          )}

          {/* 3) 예약 목록 (백엔드 reservations 필드 이용) */}
          <h3>📝 예약 목록</h3>
          {timeline.reservations && timeline.reservations.length > 0 ? (
            <ul>
              {timeline.reservations.map((r, idx) => (
                <li key={idx}>
                  {r.start} ~ {r.end} : {r.user}
                </li>
              ))}
            </ul>
          ) : (
            <p>예약이 없습니다.</p>
          )}
        </>
      )}
    </div>
  );
}

export default TimelinePage;
