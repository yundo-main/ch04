# ch04/d07 Canary Token 활용 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — API 키/시크릿 불필요.
#
# 빌드 컨텍스트 주의: ch04/shared 의 공용 모듈(local_llm.py, prompts.py,
# documents.json)을 함께 COPY 해야 하므로, 빌드 컨텍스트는 이 폴더가 아니라
# ch04/ 루트다. ch04/ 에서:
#   docker build -f d07/Dockerfile -t canary-token-demo .
FROM python:3.12-slim

WORKDIR /app

COPY shared/local_llm.py shared/prompts.py shared/documents.json ./
COPY d07/canary_mock.py d07/real_llm.py d07/canary_placement.py d07/response_canary_scanning.py d07/exfiltration_simulation.py ./

# 기본 실행: 세 예제를 순서대로 실행.
# 하나만 실행하려면: docker run <image> python response_canary_scanning.py
CMD ["sh", "-c", "python canary_placement.py && echo '========================================' && python response_canary_scanning.py && echo '========================================' && python exfiltration_simulation.py"]
