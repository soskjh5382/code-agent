# ============================================================
# llm.py  —  server와 provider 사이의 얇은 연결고리
# ============================================================
# 실제 LLM 호출 로직은 providers.py에 있다.
# 이 파일은 "설정에 맞는 provider를 골라, 대화 기록과 함께 ask()를 불러주는" 역할만 한다.
# ============================================================

from . import providers

# 다른 파일들이 llm.AgentError 로 접근하던 걸 그대로 쓰게 연결.
AgentError = providers.AgentError


def ask(message: str, history=None) -> str:
    """설정된 provider를 골라, 대화 기록과 함께 질문을 넘긴다."""
    provider = providers.get_provider()
    # history가 없으면(첫 질문) 빈 리스트로 넘긴다.
    return provider.ask(message, history or [])