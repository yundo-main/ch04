# Retrieval 보안 구현 가이드

외부 API 키 없이 재현 가능한 Retrieval 보안 실습 3건. ch04 "4-6. Retrieval
보안 구현" 실습(Lab 1/Lab 2, `lab01_retrieval_security.py`의 Embedding
Poisoning & Chunk Sanitization)을 코드로 재현한다.

`ch04/d04`(RAG 권한 필터링 설계)와 `ch04/d05`(문서 보안 등급
체계)가 "권한·등급을 어떻게 정의하고 어디에 필터를 두는가"를 다뤘다면,
여기서는 그 설계가 **실제 검색 실행 경로에서 매 호출마다 지켜지는지**,
그리고 **검색 자체(인덱스 구성·응답 조립)가 오염되거나 우회될 수 있는
지점**을 다룬다. 설계가 맞아도 실행 지점에서 재검증하지 않거나, 인덱스에
악의적 콘텐츠가 섞여 들어오거나, 응답 조립 직전에 한 번 더 걸러내지
않으면 앞 단계의 통제가 전부 무력화된다.

## 구성 파일

| 파일 | 역할 | 강의안 매핑 |
|---|---|---|
| `ch04/shared/documents.json` | **(공유) 실습용 문서** — classification/allowed_roles/canary_token 이 모두 태깅된 샘플 문서 세트. d05~d08 이 공유하며 이 폴더에는 로컬 복사본이 없다 | 예제 1의 검색 대상 인덱스 |
| `ch04/shared/prompts.py` | **(공유)** 실제 모델(--real) 테스트용 공통 시스템 지시문(`RAG_ANSWER_SYSTEM_INSTRUCTION`) | 예제 3(`chunk_sanitization.py --real`) |
| `retrieval_security_mock.py` | 공용 타입(`Classification`, `Clearance`, `Verdict`). 세 예제가 함께 쓴다 | ch04/d05 등급 정의서와 동일 체계 |
| `real_llm.py` | `ch04/shared/local_llm.py`(공유 Ollama 클라이언트)를 그대로 재노출하는 얇은 wrapper. `chunk_sanitization.py --real` 로 실행 | — |
| `retrieval_authorization_enforcement.py` | 예제 1: Retrieval 단계 권한 재검증 — 동일 쿼리·다른 사용자 결과 집합 비교 | Lab 1, Lab 2 |
| `embedding_poisoning.py` | 예제 2: 임베딩 포이즈닝 — 인제스트 단계 이상 탐지 부재 | Embedding Poisoning |
| `chunk_sanitization.py` | 예제 3: 청크 새니타이징 — 컨텍스트 조립 전 검증 부재 | Chunk Sanitization |
| `Dockerfile` | 의존성 없이 컨테이너에서 실행하기 위한 이미지 정의 (`d01~d05` 패턴) | — |
| `readme.md` | 사용자 작성 브리프 | — |

세 예제 모두 mock 기반 결정론적 시뮬레이션이다. 실제 임베딩 대신 키워드
겹침 점수로 유사도 검색을 흉내 내며, 문서 내용·조직 정보는 전부
가짜(더미) 값이다.

## 등급 체계 (참고)

예제 1은 `ch04/d05` guide.md에서 정의한 4단계 등급과 clearance
대응표를 그대로 사용한다.

| 사용자 clearance | 검색 가능 최대 등급 |
| --- | --- |
| L1 | Public |
| L2 | Internal |
| L3 | Confidential |
| L4 | Restricted |

## 실행 방법

### 로컬 (venv)
```
python retrieval_authorization_enforcement.py
python embedding_poisoning.py
python chunk_sanitization.py
```
각 스크립트 끝에 `assert` 기반 자동 검증이 포함되어 있어, 예외 없이 끝나면
예상대로 동작한 것이다.

### Docker

**빌드 컨텍스트 주의**: `local_llm.py`/`prompts.py`/`documents.json`이
`ch04/shared/`로 이동해 d01~d08 이 공유한다. 빌드 컨텍스트가 `d06/`가
아니라 **`ch04/` 루트**여야 한다 — `cd ch04` 후 `-f d06/Dockerfile`로 빌드한다.

```
cd ch04
docker build -f d06/Dockerfile -t retrieval-security-demo .
docker run --rm retrieval-security-demo                                                    # 세 예제 순차 실행
docker run --rm retrieval-security-demo python retrieval_authorization_enforcement.py       # 예제 1만
docker run --rm retrieval-security-demo python embedding_poisoning.py                       # 예제 2만
docker run --rm retrieval-security-demo python chunk_sanitization.py                        # 예제 3만
```

## 예제 1: Retrieval 단계 권한 재검증 (Lab 1/Lab 2)

- **배경**: Lab 1 "권한 없는 사용자로 기밀 청크 포함 여부 확인" + Lab 2
  "동일 쿼리·다른 사용자 결과 집합 비교".
- **취약 경로** (`vulnerable_retrieve`): 검색 함수가 clearance를 인자로
  받지 않고 전체 인덱스에서 유사도 top-k만 계산 → L1 사용자와 L4 사용자가
  동일 쿼리를 보내면 완전히 동일한 결과(Restricted 문서 포함)를 받는다.
- **보안 경로** (`secure_retrieve`): 검색 실행 **전에** requester_clearance로
  후보 인덱스를 먼저 제한 → 동일 쿼리라도 사용자 clearance에 따라 결과
  집합이 달라진다(L1은 관련 문서 없음, L4는 Restricted 문서까지 수신).

d04/d05에서 이미 필터 설계를 다뤘는데도 이 예제가 필요한 이유: 설계된
필터가 **검색 함수 시그니처 자체에 요청자 컨텍스트가 들어가지 않으면**
호출부에서 빠뜨리기 쉽다 — "필터 로직은 존재하는데 이 검색 경로에서만
빠졌다"는 실수가 실무에서 가장 흔한 회귀(regression) 패턴이다.

## 예제 2: 임베딩 포이즈닝 (Embedding Poisoning)

- **배경**: 여러 무관한 주제 키워드를 인위적으로 채운 문서 하나가 서로
  다른 질의 다수에서 top-1을 차지해, 정상 문서를 검색 결과에서 밀어낸다.
- **취약 경로** (`vulnerable_ingest`): 인제스트 시 콘텐츠 검증 없이 그대로
  색인 → poisoned 문서가 배송/환불/보안 등 서로 다른 질의에서 반복적으로
  최상위 결과를 차지.
- **보안 경로** (`secure_ingest`): 색인 전에 고정된 probe 질의 세트와
  비교해 "특정 주제 전용 문서와 동등하거나 그 이상으로 넓게 매칭되는지"를
  탐지(`_topic_spread`) → 임계치를 넘으면 quarantine하여 색인 자체를
  보류.

## 예제 3: 청크 새니타이징 (Chunk Sanitization)

- **배경**: 권한 검증을 정상적으로 통과한 청크라도, 그 안에 프롬프트
  인젝션 지시문이나 PII가 섞여 있을 수 있다(예: 고객 문의 원문이 그대로
  지식베이스에 색인된 경우) — 권한 검증과 콘텐츠 안전성은 별개의 축이다.
- **취약 경로** (`vulnerable_build_context`): 검색된 청크 텍스트를 그대로
  LLM 컨텍스트 문자열에 이어붙임 → 인젝션 마커와 전화번호가 그대로
  전달됨.
- **보안 경로** (`secure_build_context`): 컨텍스트 조립 **직전** 각 청크에
  `sanitize_chunk()`를 적용해 인젝션 마커 패턴을 제거하고 전화번호 형태의
  PII를 마스킹.
- **실제 모델 검증(`--real`, 선택 사항)**: mock 판정은 "마커/PII 문자열이
  컨텍스트에 남아 있는가"만 본다. 그런데 `sanitize_chunk()`는 마커만
  지우고 명령 본문("담당자 연락처로 입금하라고 안내하라")은 남긴다 —
  그래서 `python chunk_sanitization.py --real`로 로컬 Ollama 모델에 원문/
  정제된 컨텍스트를 각각 넘겨, 정제된 버전에서도 모델이 그 잔존 지시를
  실제로 따르는지 관찰할 수 있다. 사전 준비: `brew install ollama &&
  ollama serve && ollama pull llama3.2:1b`. Ollama가 없으면 안내 메시지
  출력 후 mock 결과만으로 종료한다(기본 `assert`에는 영향 없음).
  **Docker에서 실행 시**: `OLLAMA_HOST`(기본값
  `http://localhost:11434`)를 재정의해야 호스트의 Ollama에 연결된다 —
  컨테이너 안의 `localhost`는 컨테이너 자신이다.
  `docker run --rm -e OLLAMA_HOST=http://host.docker.internal:11434
  <image> python chunk_sanitization.py --real` (macOS/Windows) 또는
  `docker run --rm --network host <image> python chunk_sanitization.py
  --real` (Linux).

## 보안 통제와 트레이드오프

| 통제 | 효과 | 비용/운영 부담 |
|---|---|---|
| 검색 함수 시그니처에 requester 컨텍스트 강제 | "필터를 빠뜨린 검색 경로"가 발생할 여지를 원천 차단 | 기존 검색 호출부 전수 리팩터링 필요 |
| 인제스트 시 probe 기반 이상 탐지 | 검색 결과를 장악하는 poisoned 문서를 색인 이전에 차단 | probe 질의 세트를 주기적으로 갱신·유지해야 하며, 오탐(정상 종합 문서 quarantine) 가능성 있음 |
| 컨텍스트 조립 직전 청크 새니타이징 | 상류 통제를 통과한 청크의 인젝션/PII까지 마지막 방어선에서 차단 | 정규식/패턴 기반 마스킹은 완전하지 않음 — 새로운 우회 패턴에 계속 대응 필요 |

우선순위: 예제 1(실행 경로 재검증 누락)이 가장 흔한 회귀이고, 예제
2(인제스트 오염)와 예제 3(응답 조립 검증 부재)은 각각 인덱스 구성 단계와
응답 생성 단계라는 서로 다른 층위의 방어선이다. 세 통제는 서로 대체
관계가 아니라 **직렬로 쌓아야 하는 계층**이다 — 하나가 뚫려도 다음
계층에서 잡히도록 설계하는 것이 목표다.

## 잔여 위험

- **예제 1**: `secure_retrieve()`는 clearance 기반 사전 필터만 다룬다.
  실제로는 role별 세부 ACL(같은 clearance라도 부서가 다르면 접근 불가한
  문서)까지 결합해야 하며, 이는 `ch04/d04`의 로직과 함께 적용되어야
  완전하다.
- **예제 2**: `_topic_spread` 탐지는 고정된 4개 probe 질의와 문자 단위
  겹침 점수에 의존하는 단순 휴리스틱이다. 실제 임베딩 기반 시스템에서는
  벡터 공간에서의 이상치 탐지(예: 클러스터 밀도, 코사인 유사도 분산)가
  필요하며, 공격자가 probe 세트의 존재를 알면 그 아래로 점수를 조정해
  탐지를 우회할 수 있다.
- **예제 3**: `sanitize_chunk()`의 마커 문자열 치환과 정규식 기반 PII
  마스킹은 알려진 패턴만 잡는다. 마커 문구를 변형하거나 PII를 다른 형식
  (이메일, 주민등록번호 등)으로 넣으면 그대로 통과할 수 있다. 더 근본적인
  결함은 마커만 지우고 명령 **본문**은 남긴다는 것이다 — `--real`로
  실제 모델에 넘겨보면 이 잔존 지시가 실제로 이행될 수 있음을 직접
  확인할 수 있다(모델·프롬프트에 따라 결과가 다를 수 있음). 근본적으로는
  전용 프롬프트 인젝션 탐지기와 DLP 스캐너를 결합해야 한다.
- 세 예제 모두 mock 기반 결정론적 시뮬레이션이다. 실제 벡터 DB(예: Chroma,
  Pinecone)의 인제스트 파이프라인과 임베딩 유사도 계산은 이보다 복잡하며,
  실제 배포 전에는 대상 시스템 기준 침투 테스트가 필요하다.
