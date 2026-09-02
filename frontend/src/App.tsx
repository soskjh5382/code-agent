// ============================================================
// App.tsx — 코드베이스 분석 에이전트 채팅 화면
// ============================================================
// 질문 + 지금까지의 대화 기록을 백엔드(/chat)에 보내고, 답을 말풍선으로 보여준다.
// 대화 기록을 함께 보내므로 이전 대화를 기억한다(맥락 유지).
// 스타일은 전부 App.css에 있다. 여기는 화면 구조와 로직만.
// ============================================================

import { useState } from "react";
import "./App.css";

// 백엔드 서버 주소. 지금은 로컬. (배포하면 이 주소를 바꾼다)
const API_URL = "http://127.0.0.1:8000/chat";

// 예시 질문 — 이 에이전트는 프로젝트 폴더 안 파일만 읽으므로
// 프로젝트 자체에 대한 질문이라야 잘 답한다.
const EXAMPLE_QUESTIONS = [
  "이 프로젝트에 어떤 파일들이 있어?",
  "이 프로젝트가 무슨 프로젝트인지 설명해줘",
  "API 키는 어디서 읽어와?",
  "server.py가 하는 일을 설명해줘",
];

// 말풍선 하나의 형태. role로 누가 보낸 건지 구분.
type Message = { role: "user" | "agent"; text: string };

export default function App() {
  // messages: 지금까지 오고 간 모든 말풍선 목록 (이게 곧 대화 기록이 된다)
  const [messages, setMessages] = useState<Message[]>([]);
  // input: 입력창에 지금 타이핑 중인 글자
  const [input, setInput] = useState("");
  // loading: 답변 기다리는 중인지
  const [loading, setLoading] = useState(false);

  // ── 질문을 백엔드로 보내는 함수 ──
  async function sendMessage() {
    const question = input.trim();
    if (!question || loading) return; // 빈 입력이거나 대기 중이면 무시

    // 백엔드로 보낼 "이전까지의 대화 기록"을 지금 시점의 messages로 확정.
    // (아래 setMessages는 화면 갱신용이라, 여기서 미리 값을 잡아둔다)
    const historyToSend = messages;

    // 1) 내 질문을 화면에 말풍선으로 추가
    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);

    try {
      // 2) 백엔드 /chat 에 POST. 이번 질문 + 지금까지의 대화 기록을 함께 보낸다.
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: question,
          history: historyToSend, // ← 대화 기록을 함께 보내 맥락 유지
        }),
      });

      // 3) 서버가 에러(503 등)를 주면, 안내 메시지를 말풍선으로.
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = err.detail || `오류가 발생했습니다 (${res.status})`;
        setMessages((prev) => [...prev, { role: "agent", text: detail }]);
        return;
      }

      // 4) 정상 응답이면 answer를 꺼내 말풍선으로 추가.
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "agent", text: data.answer }]);
    } catch {
      // 5) 네트워크 자체가 안 될 때 (백엔드 꺼짐 등)
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: "서버에 연결할 수 없습니다. 백엔드가 켜져 있는지 확인하세요." },
      ]);
    } finally {
      setLoading(false); // 성공/실패 상관없이 로딩 끔
    }
  }

  // ── 엔터로 전송 (Shift+Enter는 줄바꿈) ──
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
      <div className="app">
        <div className="container">
          {/* ── 헤더 ── */}
          <header className="hero">
            <p className="eyebrow">code agent</p>
            <h1 className="title">코드베이스에게 물어보세요</h1>
            <p className="subtitle">
              프로젝트 파일을 직접 읽어 근거로 답합니다. 없는 것은 지어내지 않고,
              필요한 파일을 스스로 찾아 읽습니다.
            </p>
          </header>

          {/* ── 말풍선 영역 ── */}
          <div className="messages">
            {/* 대화가 없으면 안내 문구 */}
            {messages.length === 0 && (
                <p className="empty-hint">아래 예시를 누르거나 직접 질문을 입력해보세요.</p>
            )}
            {/* messages를 하나씩 말풍선으로 그린다 (role에 따라 좌우/색 다름) */}
            {messages.map((m, i) => (
                <div key={i} className={`bubble ${m.role}`}>
                  {m.text}
                </div>
            ))}
            {/* 응답 대기 중 표시 */}
            {loading && <div className="bubble agent loading">생각 중…</div>}
          </div>

          {/* ── 예시 질문 칩 (항상 표시, 누르면 입력창에 채워짐) ── */}
          <div className="examples">
            {EXAMPLE_QUESTIONS.map((q, i) => (
                <button key={i} className="example-chip" onClick={() => setInput(q)}>
                  {q}
                </button>
            ))}
          </div>

          {/* ── 입력 영역 ── */}
          <div className="input-area">
          <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="질문을 입력하세요"
              rows={2}
          />
            <button onClick={sendMessage} disabled={loading}>
              보내기
            </button>
          </div>
        </div>
      </div>
  );
}