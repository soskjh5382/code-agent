# ============================================================
# tools.py  —  에이전트의 "손발" (도구 모음)
# ============================================================
# 이 파일은 에이전트가 실제로 "행동"할 때 쓰는 도구들을 모아둔 곳이다.
# Gemini(뇌)는 판단만 하고, 실제 파일을 읽거나 검색하는 건 여기 함수들이 한다.
# 도구 = 그냥 평범한 파이썬 함수. 특별한 것 없다.
#
# 함수 위의 설명문(docstring)과 타입 힌트(path: str)가 중요하다.
# → Gemini SDK가 이걸 읽어서 "이 도구는 이런 일을 하는구나"를 파악한다.
# → 즉, docstring은 "Gemini에게 주는 사용설명서"다.
# ============================================================

import logging
from pathlib import Path   # 파일/폴더 경로를 안전하게 다루는 표준 도구

# --- 로그 설정 ---
# 도구가 호출될 때마다 터미널에 "🔧 어떤 도구가 불렸는지"를 찍는다.
# 이걸 켜두면 에이전트가 속으로 무슨 도구를 어떤 순서로 썼는지 눈으로 볼 수 있다 (관측성).
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent.tools")

# --- 기준 폴더 ---
# 에이전트가 접근할 수 있는 "루트 폴더". 서버를 실행한 위치(= 프로젝트 루트)가 된다.
# 이 폴더를 기준으로 삼아, 이 밖의 엉뚱한 파일은 못 건드리게 막는다 (안전장치).
BASE_DIR = Path(".").resolve()


def read_file(path: str) -> str:
    """지정한 경로의 파일 내용을 읽어서 문자열로 돌려준다.

    파일 안에 뭐가 적혀 있는지 알아야 하는 질문에 쓰는 도구.

    Args:
        path: 읽을 파일의 경로 (예: "src/code_agent/server.py")
    """
    # 이 도구가 호출됐다는 걸 터미널에 기록 (관측용)
    logger.info(f"🔧 read_file(path={path!r})")

    # 기준 폴더를 기준으로 실제 경로를 계산한다.
    target = (BASE_DIR / path).resolve()

    # [안전장치] 기준 폴더 바깥으로 벗어나는 경로는 거부한다.
    # (예: "../../어딘가/비밀파일" 같은 접근을 차단)
    if BASE_DIR not in target.parents and target != BASE_DIR:
        return f"[거부됨] 기준 폴더 밖의 파일은 읽을 수 없습니다: {path}"

    # 파일이 없으면 에러로 죽지 않고, 안내 문자열을 돌려준다.
    # → 에이전트가 이 메시지를 보고 "아 없구나" 하고 다시 판단할 수 있게.
    if not target.exists() or not target.is_file():
        return f"[없음] 파일을 찾을 수 없습니다: {path}"

    # 파일을 읽는다. 너무 길면 앞 5000자만 (Gemini에게 과하게 많이 안 넘기려고).
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > 5000:
        text = text[:5000] + "\n...(생략됨)"
    return text


def list_files(directory: str = ".") -> str:
    """지정한 폴더 안의 파일과 하위 폴더 목록을 돌려준다.

    "이 프로젝트에 무슨 파일이 있지?"처럼, 파일 이름을 모를 때
    먼저 폴더를 둘러보는 용도. 여기서 파악한 뒤 read_file로 읽으면 된다.

    Args:
        directory: 목록을 볼 폴더 경로. 기본값 "."는 기준 폴더 전체를 뜻함.
    """
    logger.info(f"🔧 list_files(directory={directory!r})")

    target = (BASE_DIR / directory).resolve()

    # [안전장치] read_file과 같은 원리 — 기준 폴더 밖은 거부.
    if BASE_DIR not in target.parents and target != BASE_DIR:
        return f"[거부됨] 기준 폴더 밖은 볼 수 없습니다: {directory}"

    if not target.exists() or not target.is_dir():
        return f"[없음] 폴더를 찾을 수 없습니다: {directory}"

    # 폴더 안 항목들을 하나씩 훑어서 목록을 만든다.
    entries = []
    for item in sorted(target.iterdir()):
        # 숨김 파일/폴더(.venv, .git 등)와 캐시 폴더는 노이즈라 건너뛴다.
        if item.name.startswith(".") or item.name == "__pycache__":
            continue
        # 폴더면 이름 뒤에 "/"를 붙여서 파일과 구분되게 표시.
        mark = "/" if item.is_dir() else ""
        entries.append(item.name + mark)

    if not entries:
        return f"({directory} 폴더는 비어있음)"

    # 목록을 줄바꿈으로 이어서 하나의 문자열로 돌려준다.
    return "\n".join(entries)


def search_code(keyword: str) -> str:
    """기준 폴더 안의 모든 텍스트 파일에서 특정 단어를 검색한다.

    "이 함수/변수/문자열이 어느 파일에 있지?"를 찾을 때 쓰는 도구.
    결과는 '파일경로:줄번호: 해당 줄 내용' 형태로 돌려준다.
    (지금은 단순 텍스트 검색. 나중에 이걸 의미 기반 검색으로 바꾸면 RAG가 된다.)

    Args:
        keyword: 찾을 단어나 문자열 (예: "GEMINI_API_KEY")
    """
    logger.info(f"🔧 search_code(keyword={keyword!r})")

    results = []  # 찾은 결과를 담을 리스트

    # 기준 폴더 아래 모든 파일을 재귀적으로(하위 폴더까지) 훑는다.
    for path in BASE_DIR.rglob("*"):
        # 폴더 자체는 검색 대상이 아니니 건너뛴다.
        if path.is_dir():
            continue
        # 숨김/캐시 경로(.venv, .git, __pycache__ 등)는 노이즈라 제외.
        parts = path.parts
        if any(p.startswith(".") or p == "__pycache__" for p in parts):
            continue

        # 텍스트로 못 읽는 파일(이미지 등)은 조용히 건너뛴다.
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue

        # 파일을 한 줄씩 보면서, keyword가 들어있는 줄을 기록한다.
        for line_no, line in enumerate(text.splitlines(), start=1):
            if keyword in line:
                # 보기 편하게 기준 폴더 기준의 상대 경로로 표시.
                rel = path.relative_to(BASE_DIR)
                results.append(f"{rel}:{line_no}: {line.strip()}")

    if not results:
        return f"'{keyword}'를 찾지 못했습니다."

    # 결과가 너무 많으면 앞 30개만 (Gemini에게 과하게 넘기지 않으려고).
    if len(results) > 30:
        results = results[:30] + ["...(더 있음)"]

    return "\n".join(results)