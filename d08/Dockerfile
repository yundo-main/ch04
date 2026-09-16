# ch04/d08 End-to-End 보안 통합 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — API 키/시크릿 불필요.
#
# 빌드 컨텍스트 주의: ch04/shared 의 공용 모듈(local_llm.py, prompts.py,
# documents.json)을 함께 COPY 해야 하므로, 빌드 컨텍스트는 이 폴더가 아니라
# ch04/ 루트다. ch04/ 에서:
#   docker build -f d08/Dockerfile -t e2e-security-demo .
FROM python:3.12-slim

WORKDIR /app

COPY shared/local_llm.py shared/prompts.py shared/documents.json ./
COPY d08/e2e_pipeline.py d08/real_llm.py d08/vulnerable_e2e.py d08/secure_e2e.py d08/gap_analysis.py ./

# 기본 실행: 세 Lab을 순서대로 실행.
# 하나만 실행하려면: docker run <image> python gap_analysis.py
CMD ["sh", "-c", "python vulnerable_e2e.py && echo '========================================' && python secure_e2e.py && echo '========================================' && python gap_analysis.py"]
