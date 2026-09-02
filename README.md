# 코드베이스 분석 에이전트 (Code Agent)

프로젝트 폴더의 파일을 **직접 읽어 근거로 답하는** AI 에이전트입니다.
질문을 던지면 에이전트가 스스로 필요한 파일을 찾고(`list_files`), 읽고(`read_file`), 검색해서(`search_code`) 종합해 답합니다. 답을 지어내지 않고, 실제 코드를 확인한 뒤 대답합니다.

일반적인 "챗봇"과 달리, LLM이 **어떤 도구를 언제 쓸지 스스로 판단**해 여러 단계를 거쳐 답을 만드는 **에이전트(agent)** 구조가 핵심입니다.

---

## 주요 특징

- **도구 기반 에이전트** — LLM이 상황에 맞는 도구를 스스로 골라 여러 번 호출하며 답을 찾아갑니다.
- **멀티스텝 추론** — "API 키는 어디서 읽어와?" 같은 질문에 대해 검색 → 파일 읽기 → 종합의 여러 단계를 자동으로 수행합니다.
- **대화 맥락 유지** — 이전 대화를 기억해 "방금 말한 것 중에…" 같은 이어지는 질문에 답합니다.
- **LLM provider 분기** — 설정값 하나로 Gemini / Claude / OpenAI를 전환할 수 있는 구조입니다. (기본값 Gemini)
- **안정화 처리** — 도구 호출 횟수 제한(무한루프 방지), 요청 한도 초과(429) 등 에러를 사용자에게 친절하게 안내합니다.
- **관측성** — 에이전트가 어떤 도구를 어떤 순서로 호출했는지 로그로 확인할 수 있습니다.

---

## 기술 스택

| 구분 | 사용 기술 |
|------|-----------|
| 백엔드 | Python, FastAPI, Uvicorn |
| 에이전트 / LLM | Google Gemini (기본), Claude · OpenAI 전환 가능 |
| 프론트엔드 | React, TypeScript, Vite |
| 패키지 관리 | uv (백엔드), npm (프론트엔드) |

---

## 아키텍처

```
[React 채팅 UI]  ──질문 + 대화기록──▶  [FastAPI /chat]
   frontend/                              backend/
                                             │
                                     [에이전트 (provider)]
                                             │
                         ┌───────────────────┼───────────────────┐
                    [read_file]         [list_files]         [search_code]
                     파일 읽기            폴더 목록             단어 검색
                                             │
                                          [LLM]  ← 도구를 언제 쓸지 판단
```

프론트엔드는 백엔드의 `/chat` API만 호출합니다. 백엔드는 LLM에게 도구 목록을 알려주고, LLM이 도구 호출을 요청하면 실제 함수를 실행해 결과를 다시 LLM에게 전달하는 **도구 호출 루프**를 돌립니다.

---

## 폴더 구조

```
code-agent/
├── backend/                  # FastAPI 백엔드 (에이전트)
│   ├── src/code_agent/
│   │   ├── server.py         # FastAPI 서버, /chat 엔드포인트
│   │   ├── llm.py            # server와 provider 사이 연결
│   │   ├── providers.py      # Gemini/Claude/OpenAI 구현 + 도구 루프
│   │   ├── tools.py          # 도구 함수(read_file, list_files, search_code)
│   │   └── config.py         # 설정(.env에서 키·모델·provider 로드)
│   ├── pyproject.toml
│   └── .env                  # API 키 등 (git에 올리지 않음)
│
└── frontend/                 # React 채팅 UI
    ├── src/
    │   ├── App.tsx           # 채팅 화면 + API 호출
    │   └── App.css           # 스타일
    └── package.json
```

---

## 로컬 실행 방법

백엔드와 프론트엔드를 **각각 별도 터미널**에서 실행합니다.

### 사전 준비

- Python 3.10 이상, [uv](https://docs.astral.sh/uv/) 설치
- Node.js (npm 포함) 설치
- Gemini API 키 ([Google AI Studio](https://aistudio.google.com)에서 무료 발급)

### 1. 저장소 받기

```bash
git clone <저장소 주소>
cd code-agent
```

### 2. 백엔드 실행 (터미널 1)

```bash
cd backend

# 의존성 설치
uv sync

# .env 파일을 만들고 아래 내용을 채운다
#   GEMINI_API_KEY=발급받은_키
#   (선택) GEMINI_MODEL=gemini-3.5-flash-lite
#   (선택) LLM_PROVIDER=gemini

# 서버 실행
uv run uvicorn code_agent.server:app --reload --app-dir src
```

서버가 `http://127.0.0.1:8000` 에서 실행됩니다.
API 문서는 `http://127.0.0.1:8000/docs` 에서 확인할 수 있습니다.

### 3. 프론트엔드 실행 (터미널 2)

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

프론트엔드가 `http://localhost:5173` 에서 실행됩니다. 브라우저로 접속하면 채팅 화면이 나타납니다.

> **참고:** 저장소를 새로 받으면 `.env`, `node_modules`, `.venv` 는 포함되지 않습니다.
> `.env`는 직접 만들어 API 키를 넣고, 의존성은 위의 `uv sync` / `npm install` 로 설치합니다.

---

## 환경 변수 (`backend/.env`)

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `GEMINI_API_KEY` | Gemini API 키 (필수) | — |
| `GEMINI_MODEL` | 사용할 Gemini 모델 | `gemini-3.5-flash-lite` |
| `LLM_PROVIDER` | 사용할 LLM (`gemini` / `claude` / `openai`) | `gemini` |
| `ANTHROPIC_API_KEY` | Claude 사용 시 필요 | — |
| `OPENAI_API_KEY` | OpenAI 사용 시 필요 | — |

`LLM_PROVIDER` 값만 바꾸면 다른 LLM으로 전환됩니다. (해당 provider의 API 키가 있어야 함)

---

## 사용 예시

이 에이전트는 프로젝트 폴더 안의 파일만 읽으므로, 프로젝트 자체에 대해 질문할 때 잘 동작합니다.

- "이 프로젝트에 어떤 파일들이 있어?"
- "이 프로젝트가 무슨 프로젝트인지 설명해줘"
- "API 키는 어디서 읽어와?"
- "server.py가 하는 일을 설명해줘"

---

## 라이선스

개인 학습·포트폴리오 목적으로 제작되었습니다.