# test_connection.py
# 목적: Gemini API에 실제로 연결되는지 확인하는 최소 테스트.
#      여기까지 성공하면 0단계(환경 세팅) 완료.

import os                          # 환경변수를 읽기 위한 표준 라이브러리
from dotenv import load_dotenv     # .env 파일 내용을 환경변수로 불러오는 도구
from google import genai           # Gemini 공식 SDK

# 1) .env 파일을 읽어서 그 안의 값들을 환경변수로 등록한다.
#    이걸 호출해야 아래 os.environ에서 GEMINI_API_KEY를 찾을 수 있다.
load_dotenv()

# 2) 환경변수에서 API 키를 꺼낸다.
#    코드에 키를 직접 쓰지 않고 .env에서 불러오는 게 핵심(보안).
api_key = os.environ.get("GEMINI_API_KEY")

# 3) 키가 없으면 바로 알려주고 종료 (흔한 실수를 빨리 잡기 위함).
if not api_key:
    raise SystemExit("GEMINI_API_KEY가 없습니다. .env 파일을 확인하세요.")

# 4) Gemini 클라이언트 생성. 이 client 객체로 모든 요청을 보낸다.
client = genai.Client(api_key=api_key)

# 5) 실제로 한 번 호출해본다.
#    model: 무료 티어에서 넉넉한 Flash 계열을 사용 (개발용으로 적합).
#    contents: 모델에게 보낼 메시지(프롬프트).
response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="한 문장으로 자기소개 해줘.",
)

# 6) 응답 텍스트를 출력. 여기서 답이 찍히면 연결 성공.
print("=== Gemini 응답 ===")
print(response.text)