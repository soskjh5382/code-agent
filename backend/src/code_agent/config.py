# ============================================================
# config.py  —  프로젝트의 모든 설정값을 모아두는 곳
# ============================================================
# API 키, 모델 이름, 쓸 provider 등 "바뀔 수 있는 값"을 여기서만 관리한다.
# 값이 바뀌어도 이 파일(또는 .env)만 고치면 되게 한다.
# ============================================================

import os
from dotenv import load_dotenv

# .env 파일을 읽어 환경변수로 등록 (import될 때 한 번 실행)
load_dotenv()

# --- Gemini (지금 쓰는 것, 무료) ---
# .env의 GEMINI_API_KEY 값을 가져온다.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 키가 없으면 서버 시작 시 바로 알려주고 멈춘다.
if not GEMINI_API_KEY:
    raise SystemExit("GEMINI_API_KEY가 없습니다. .env 파일을 확인하세요.")

# 모델 이름. .env에 GEMINI_MODEL이 있으면 그 값, 없으면 기본값.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

# --- 어떤 LLM provider를 쓸지 고르는 값 ---
# 이 값 하나로 사용할 LLM이 바뀐다: "gemini" / "claude" / "openai"
# .env에 LLM_PROVIDER가 있으면 그 값, 없으면 기본값 "gemini".
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")

# --- Claude(Anthropic) 설정 ---
# 지금은 키가 없어도 됨. 나중에 .env에 ANTHROPIC_API_KEY를 넣으면 작동.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5")

# --- OpenAI 설정 ---
# 마찬가지로 나중에 .env에 OPENAI_API_KEY를 넣으면 작동.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")