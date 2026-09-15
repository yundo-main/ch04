# ch04/d01 프롬프트 인젝션 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — GEMINI_API_KEY 등 시크릿 불필요.
FROM python:3.12-slim

WORKDIR /app

COPY mock_llm.py real_llm.py prompts.py direct_injection.py indirect_injection.py documents.json ./

# 기본 실행: 두 예제를 순서대로 실행.
# 하나만 실행하려면: docker run <image> python direct_injection.py
CMD ["sh", "-c", "python direct_injection.py && echo '========================================' && python indirect_injection.py"]
