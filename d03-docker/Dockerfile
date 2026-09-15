# ch04/d03-docker LLM 데이터 유출 위험 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — API 키/시크릿 불필요.
FROM python:3.12-slim

WORKDIR /app

COPY leakage_mock.py credential_pii_leak.py multitenant_rag_leak.py memory_poisoning_leak.py ./

# 기본 실행: 세 예제를 순서대로 실행.
# 하나만 실행하려면: docker run <image> python credential_pii_leak.py
CMD ["sh", "-c", "python credential_pii_leak.py && echo '========================================' && python multitenant_rag_leak.py && echo '========================================' && python memory_poisoning_leak.py"]
