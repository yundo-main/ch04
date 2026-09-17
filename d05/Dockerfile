# ch04/d05 문서 보안 등급 체계 설계 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — API 키/시크릿 불필요.
#
# 빌드 컨텍스트: ch04/ 루트(다른 dNN과 동일한 빌드 명령 패턴 유지). ch04/ 에서:
#   docker build -f d05/Dockerfile -t doc-classification-demo .
FROM python:3.12-slim

WORKDIR /app

COPY d05/documents.json d05/doc_classification_mock.py d05/default_classification_missing.py d05/classification_spoofing.py d05/downgrade_on_summarization.py ./

# 기본 실행: 세 예제를 순서대로 실행.
# 하나만 실행하려면: docker run <image> python classification_spoofing.py
CMD ["sh", "-c", "python default_classification_missing.py && echo '========================================' && python classification_spoofing.py && echo '========================================' && python downgrade_on_summarization.py"]
