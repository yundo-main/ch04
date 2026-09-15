# ch04/d04-docker RAG 권한 필터링 설계 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — API 키/시크릿 불필요.
FROM python:3.12-slim

WORKDIR /app

COPY rag_acl_mock.py prefilter_vs_postfilter.py role_spoofing.py missing_metadata_policy.py ./

# 기본 실행: 세 예제를 순서대로 실행.
# 하나만 실행하려면: docker run <image> python prefilter_vs_postfilter.py
CMD ["sh", "-c", "python prefilter_vs_postfilter.py && echo '========================================' && python role_spoofing.py && echo '========================================' && python missing_metadata_policy.py"]
