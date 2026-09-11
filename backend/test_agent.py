from src.code_agent import llm
answer = llm.ask("read_file 함수를 고치면 어디까지 영향이 가?")
print("\n=== 에이전트 답변 ===")
print(answer)