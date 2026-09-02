# ============================================================
# providers.py  —  여러 LLM(Gemini/Claude/OpenAI)을 갈아끼우는 층
# ============================================================
# "어떤 회사의 LLM을 쓸지"를 담당한다.
# 에이전트 로직(도구 루프)은 어떤 LLM을 쓰든 똑같아야 하므로,
# 회사마다 다른 "API 호출 방식"만 여기에 격리한다.
#
# ★ 어떤 provider를 쓸지 고르는 법:
#    .env 에서 LLM_PROVIDER 값을 바꾸면 된다.
#      LLM_PROVIDER=gemini   → Gemini (지금 기본값, 무료)
#      LLM_PROVIDER=claude   → Claude (ANTHROPIC_API_KEY 필요)
#      LLM_PROVIDER=openai   → OpenAI (OPENAI_API_KEY 필요)
#
# ★ 대화 맥락 유지:
#    각 ask()는 history(지금까지의 대화 기록)를 함께 받아,
#    LLM에게 이전 대화를 먼저 알려준 뒤 새 질문을 보낸다.
# ============================================================

from . import config
from . import tools


# --- 우리 에이전트 전용 에러 타입 (모든 provider 공통) ---
class AgentError(Exception):
    pass


# --- 공통 규격(인터페이스) ---
# 모든 provider는 "ask(질문, 대화기록) → 답변 문자열" 모양을 따른다.
class LLMProvider:
    def ask(self, message: str, history=None) -> str:
        raise NotImplementedError("provider가 ask()를 구현해야 합니다.")


# 세 provider가 공통으로 쓰는 시스템 프롬프트(역할 지시문).
SYSTEM_INSTRUCTION = (
    "너는 코드베이스를 분석하는 도우미다. "
    "파일 이름을 모를 때는 list_files로 폴더를 둘러보고, "
    "특정 단어가 어디 있는지 찾을 때는 search_code를 쓰고, "
    "파일 내용을 확인할 때는 read_file을 써라. "
    "추측하지 말고 도구로 실제 확인한 뒤 답해라."
)


# ============================================================
# Gemini 구현체  (지금 실제로 쓰는 것, 무료)
# ============================================================
class GeminiProvider(LLMProvider):
    def __init__(self):
        from google import genai
        self._client = genai.Client(api_key=config.GEMINI_API_KEY)

    def ask(self, message: str, history=None) -> str:
        from google.genai import types, errors

        # Gemini가 쓸 수 있는 도구들.
        available_tools = [tools.read_file, tools.list_files, tools.search_code]

        chat = self._client.chats.create(
            model=config.GEMINI_MODEL,
            config=types.GenerateContentConfig(
                tools=available_tools,
                system_instruction=SYSTEM_INSTRUCTION,
                # 무한루프 방지: 도구 왕복 최대 5번
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    maximum_remote_calls=5
                ),
            ),
            # ── 이전 대화 기록을 세션에 미리 채워넣는다(맥락 유지) ──
            # history: [(role, text), ...] 형태.
            # Gemini는 역할을 "user"/"model"로 쓰므로 agent → model 로 변환.
            history=[
                types.Content(
                    role="user" if role == "user" else "model",
                    parts=[types.Part(text=text)],
                )
                for role, text in (history or [])
            ],
        )

        try:
            response = chat.send_message(message)
            # 답이 비어있으면(무거운 질문이라 도구만 쓰다 멈춘 경우 등) 안내로 대체
            if not response.text:
                return "답을 정리하지 못했어요. 좀 더 구체적으로 질문해 주시겠어요?"
            return response.text
        except errors.ClientError as e:
            if e.code == 429:
                raise AgentError(
                    "지금 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요. "
                    "(무료 티어 일일 한도 초과일 수 있습니다.)"
                )
            raise AgentError(f"요청 처리 중 문제가 발생했습니다: {e.message}")
        except Exception as e:
            raise AgentError(f"알 수 없는 오류가 발생했습니다: {e}")


# ============================================================
# Claude 구현체  (Anthropic)
# ★ 쓰려면: .env에  ANTHROPIC_API_KEY=...  추가하고  LLM_PROVIDER=claude 로 변경
# ============================================================
class ClaudeProvider(LLMProvider):
    def __init__(self):
        import anthropic
        self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

        # Claude에게 넘길 도구 "설명서"(JSON 스키마).
        # Gemini는 함수를 그냥 넘기면 됐지만, Claude는 이렇게 직접 적어줘야 한다.
        self._tool_specs = [
            {
                "name": "read_file",
                "description": "지정한 경로의 파일 내용을 읽어서 돌려준다.",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "읽을 파일 경로"}},
                    "required": ["path"],
                },
            },
            {
                "name": "list_files",
                "description": "지정한 폴더 안의 파일/폴더 목록을 돌려준다.",
                "input_schema": {
                    "type": "object",
                    "properties": {"directory": {"type": "string", "description": "볼 폴더 경로"}},
                },
            },
            {
                "name": "search_code",
                "description": "모든 텍스트 파일에서 특정 단어를 검색한다.",
                "input_schema": {
                    "type": "object",
                    "properties": {"keyword": {"type": "string", "description": "찾을 단어"}},
                    "required": ["keyword"],
                },
            },
        ]
        # 도구 이름 → 실제 파이썬 함수 연결표.
        self._tool_funcs = {
            "read_file": tools.read_file,
            "list_files": tools.list_files,
            "search_code": tools.search_code,
        }

    def ask(self, message: str, history=None) -> str:
        import anthropic

        # 대화 기록을 Claude 형식으로 변환해서 먼저 채운다(맥락 유지).
        # Claude는 역할을 "user"/"assistant"로 쓴다.
        messages = []
        for role, text in (history or []):
            messages.append({
                "role": "user" if role == "user" else "assistant",
                "content": text,
            })
        # 이번 질문을 맨 뒤에 추가.
        messages.append({"role": "user", "content": message})

        try:
            # 무한루프 방지: 최대 5번까지만 도구 왕복
            for _ in range(5):
                response = self._client.messages.create(
                    model=config.CLAUDE_MODEL,
                    max_tokens=1024,
                    system=SYSTEM_INSTRUCTION,
                    tools=self._tool_specs,
                    messages=messages,
                )

                # 도구를 쓰지 않고 그냥 답했으면 → 텍스트 돌려주고 끝.
                if response.stop_reason != "tool_use":
                    texts = [b.text for b in response.content if b.type == "text"]
                    return "\n".join(texts) or "답을 정리하지 못했어요."

                # 도구 요청이 있으면 → 실제로 실행해서 결과를 돌려준다.
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        func = self._tool_funcs[block.name]
                        result = func(**block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "user", "content": tool_results})

            return "답을 정리하지 못했어요. 좀 더 구체적으로 질문해 주시겠어요?"

        except anthropic.RateLimitError:
            raise AgentError("지금 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
        except Exception as e:
            raise AgentError(f"Claude 처리 중 오류가 발생했습니다: {e}")


# ============================================================
# OpenAI 구현체
# ★ 쓰려면: .env에  OPENAI_API_KEY=...  추가하고  LLM_PROVIDER=openai 로 변경
# ============================================================
class OpenAIProvider(LLMProvider):
    def __init__(self):
        from openai import OpenAI
        self._client = OpenAI(api_key=config.OPENAI_API_KEY)

        # OpenAI에게 넘길 도구 "설명서"(형식이 또 조금 다르다).
        self._tool_specs = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "지정한 경로의 파일 내용을 읽어서 돌려준다.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "지정한 폴더 안의 파일/폴더 목록을 돌려준다.",
                    "parameters": {
                        "type": "object",
                        "properties": {"directory": {"type": "string"}},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_code",
                    "description": "모든 텍스트 파일에서 특정 단어를 검색한다.",
                    "parameters": {
                        "type": "object",
                        "properties": {"keyword": {"type": "string"}},
                        "required": ["keyword"],
                    },
                },
            },
        ]
        self._tool_funcs = {
            "read_file": tools.read_file,
            "list_files": tools.list_files,
            "search_code": tools.search_code,
        }

    def ask(self, message: str, history=None) -> str:
        import json
        from openai import OpenAIError

        # 시스템 지시 + 이전 대화 기록 + 이번 질문 순서로 채운다(맥락 유지).
        # OpenAI는 역할을 "user"/"assistant"로 쓴다.
        messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
        for role, text in (history or []):
            messages.append({
                "role": "user" if role == "user" else "assistant",
                "content": text,
            })
        messages.append({"role": "user", "content": message})

        try:
            # 무한루프 방지: 최대 5번까지만 도구 왕복
            for _ in range(5):
                response = self._client.chat.completions.create(
                    model=config.OPENAI_MODEL,
                    messages=messages,
                    tools=self._tool_specs,
                )
                msg = response.choices[0].message

                # 도구 호출 요청이 없으면 → 그냥 답한 것. 텍스트 돌려주고 끝.
                if not msg.tool_calls:
                    return msg.content or "답을 정리하지 못했어요."

                # 도구 호출 요청이 있으면 → 실제로 실행.
                messages.append(msg)
                for call in msg.tool_calls:
                    func = self._tool_funcs[call.function.name]
                    args = json.loads(call.function.arguments)  # 인자는 JSON 문자열로 옴
                    result = func(**args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    })

            return "답을 정리하지 못했어요. 좀 더 구체적으로 질문해 주시겠어요?"

        except OpenAIError as e:
            raise AgentError(f"OpenAI 처리 중 오류가 발생했습니다: {e}")
        except Exception as e:
            raise AgentError(f"알 수 없는 오류가 발생했습니다: {e}")


# ============================================================
# 설정을 보고 알맞은 provider를 골라 돌려준다
# ============================================================
_provider_instance = None


def get_provider() -> LLMProvider:
    """config.LLM_PROVIDER 값에 맞는 provider를 돌려준다 (한 번 만들어 재사용)."""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    name = config.LLM_PROVIDER.lower()
    if name == "gemini":
        _provider_instance = GeminiProvider()
    elif name == "claude":
        _provider_instance = ClaudeProvider()
    elif name == "openai":
        _provider_instance = OpenAIProvider()
    else:
        raise AgentError(f"알 수 없는 provider입니다: {config.LLM_PROVIDER}")

    return _provider_instance