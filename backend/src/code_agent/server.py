# ============================================================
# server.py  —  웹 API 서버 (바깥 세상과의 창구)
# ============================================================
# 질문 + 지금까지의 대화 기록을 받아 llm.ask()에 넘기고, 답을 돌려준다.
# React 프론트(다른 주소)에서 호출할 수 있게 CORS도 허용한다.
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware   # CORS 허용용
from pydantic import BaseModel
from . import llm

app = FastAPI()

# --- CORS 설정 ---
# 프론트(다른 주소)에서 이 서버로 요청하는 걸 허용한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 대화 기록 한 줄의 형태 (누가 무슨 말을 했는지).
# role: "user"(사용자) 또는 "agent"(에이전트)
class HistoryItem(BaseModel):
    role: str
    text: str


# 요청 본문: 이번 질문(message) + 지금까지의 대화 기록(history)
class ChatRequest(BaseModel):
    message: str
    # 첫 질문 땐 기록이 없으니 기본값을 빈 리스트로.
    history: list[HistoryItem] = []


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    try:
        # 대화 기록을 (role, text) 튜플 목록으로 바꿔서 넘긴다.
        history = [(h.role, h.text) for h in req.history]
        answer = llm.ask(req.message, history)
        return {"answer": answer}
    except llm.AgentError as e:
        # 우리가 정리한 에러 → 503 + 친절한 메시지
        raise HTTPException(status_code=503, detail=str(e))