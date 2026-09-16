# ch04/d05 문서 보안 등급 체계 설계 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — API 키/시크릿 불필요.
#
# 빌드 컨텍스트 주의: ch04/shared 의 공용 문서 세트(documents.json)를 함께
# COPY 해야 하므로, 빌드 컨텍스트는 이 폴더가 아니라 ch04/ 루트다. ch04/ 에서:
#   docker build -f d05/Dockerfile -t doc-classification-demo .
FROM python:3.12-slim

WORKDIR /app

COPY shared/documents.json ./
COPY d05/doc_classification_mock.py d05/default_classification_missing.py d05/classification_spoofing.py d05/downgrade_on_summarization.py ./

# 기본 실행: 세 예제를 순서대로 실행.
# 하나만 실행하려면: docker run <image> python classification_spoofing.py
CMD ["sh", "-c", "python default_classification_missing.py && echo '========================================' && python classification_spoofing.py && echo '========================================' && python downgrade_on_summarization.py"]
