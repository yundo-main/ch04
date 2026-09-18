# LLM 데이터 유출 위험 가이드

외부 API 키 없이 재현 가능한 LLM 데이터 유출(Data Leakage) 실습 3건. ch04 "4-3. LLM
데이터 유출 위험 분석" 강의안의 경로 카탈로그(P1~P8)와 용어(Context Redaction, PII
Leakage, Memory Poisoning)를 코드로 재현한다.

`ch04/d01`(프롬프트 인젝션)가 "공격자의 지시를 모델이 따르는가"를, `ch04/d02`
(jailbreak)가 "안전 정책을 우회할 수 있는가"를 다뤘다면, 여기서는 "**공격이 전혀 없어도**
민감 데이터가 새어나갈 수 있는 경로"를 다룬다 — 강의안 A.2 "유출 ≠ 해킹만"이 핵심이다.

## 구성 파일

| 파일 | 역할 | 강의안 매핑 |
|---|---|---|
| `leakage_mock.py` | 공용 결과 타입(`Verdict`). 세 예제가 함께 쓴다 | — |
| `prompts.py` | 세 예제의 프롬프트 텍스트 전부(`CODE_REVIEW_SYSTEM_INSTRUCTION`/`USER_PASTE`/`MULTITENANT_QUERY`/`MEMORY_RECALL_*`/`RAG_ANSWER_SYSTEM_INSTRUCTION`). 이 폴더 로컬 파일(d00-shared 공유 없음) — `RAG_ANSWER_SYSTEM_INSTRUCTION`은 d06/d07/d08도 각자 로컬로 동일한 값을 갖고 있다 | 예제 2(기본 실습)는 `RAG_ANSWER_SYSTEM_INSTRUCTION` 사용 |
| `wrapper.py` | `d00-shared/local_llm.py`를 그대로 재노출하는 순수 wrap — 시나리오 콘텐츠 없음 | — |
| `credential_pii_leak.py` | 예제 1: 자격증명/PII 유출 (Context Redaction 미적용). `run_real()`이 `wrapper.py`를 호출해 기본 실행 시 실제 모델까지 재현한다 | 시나리오 A, 경로 P1·P5 |
| `multitenant_rag_leak.py` | 예제 2: RAG 교차 테넌트 데이터 유출 (ACL 누락). 마찬가지로 `run_real()` 포함 | 시나리오 B, 경로 P3 |
| `memory_poisoning_leak.py` | 예제 3: 메모리 포이즈닝을 통한 세션 간 지속 유출. 마찬가지로 `run_real()` 포함 | 용어 "Memory Poisoning", 경로 P6 |
| `Dockerfile` | 의존성 없이 컨테이너에서 실행하기 위한 이미지 정의 (`d01`/`d02` 패턴) |  |
| `readme.md` | 사용자 작성 브리프 |  |

세 예제 모두 mock 기반 결정론적 시뮬레이션이며, API 키·카드번호·이메일 등은 전부 가짜
(더미) 값이다.

## 실행 방법

### 로컬 (venv) — 기본 실습
```
python credential_pii_leak.py
python multitenant_rag_leak.py
python memory_poisoning_leak.py
```
각 스크립트 끝에 `assert` 기반 자동 검증이 포함되어 있어, 예외 없이 끝나면 예상대로
동작한 것이다. **플래그 없이 실행하면 mock 비교 다음에 자동으로 실제 Ollama
모델까지 호출한다**(0단계 설정이 끝나 있다면 별도 플래그가 필요 없다). 세 스크립트 모두 이미
존재하는 가짜(더미) 데이터(API 키, 테넌트 A 계약 조건, user_bob 카드번호)를 그대로
실제 모델에 넘기고, 응답 텍스트에 그 값이 그대로 나타나는지만 확인한다 — 실제 민감정보를
다루지 않는다. **Ollama가 연결 안 되어 있으면 mock 비교조차 실행하지 않고 `LLM 연결
안됨` 메시지만 출력한 뒤 종료한다.**

mock 결과만이라도 보려면 `--mock`을 명시한다(Ollama 연결 여부와 무관하게
실행됨):
```
python credential_pii_leak.py --mock
python multitenant_rag_leak.py --mock
python memory_poisoning_leak.py --mock
```

### Docker — 선택 실습 (mock 전용)

Docker 이미지의 기본 CMD는 항상 `--mock`을 붙여 실행한다. 실제 모델
검증은 위 "로컬 (venv)" 절대로 진행한다.

**빌드 컨텍스트 주의**: `local_llm.py`가 `ch04/d00-shared/`로 이동해
d01~d08 이 공유한다(`prompts.py`는 이 폴더 로컬 파일). 빌드 컨텍스트가
`d03/`가 아니라 **`ch04/` 루트**여야 한다 — `cd ch04` 후 `-f d03/Dockerfile`로
빌드한다.

```
cd ch04
docker build -f d03/Dockerfile -t llm-data-leakage-demo .
docker run --rm llm-data-leakage-demo                                  # 세 예제 순차 실행
docker run --rm llm-data-leakage-demo python credential_pii_leak.py --mock    # 예제 1만
docker run --rm llm-data-leakage-demo python multitenant_rag_leak.py --mock   # 예제 2만
docker run --rm llm-data-leakage-demo python memory_poisoning_leak.py --mock  # 예제 3만
```

## 예제 1: 자격증명/PII 유출 (Context Redaction 미적용)

- **시나리오**: 강의안 시나리오 A "코드 리뷰 좀" — 사용자가 API 키와 이메일이 포함된
  코드를 그대로 LLM에 붙여넣는다. 악의 없는 정상 업무 흐름에서 발생한다는 게 핵심
  (강의안 A.2 "유출 ≠ 해킹만").
- **취약 경로** (`vulnerable_send_to_vendor`): 원문을 마스킹 없이 벤더 API 호출 로그와
  SIEM 로그에 그대로 남김 → API 키·이메일 그대로 유출 (경로 P1 + P5)
- **보안 경로** (`secure_send_to_vendor`): 전송/로깅 *전에* 정규식 기반 Context
  Redaction 적용 → 로그 어디에도 원본 값이 남지 않음

## 예제 2: RAG 교차 테넌트 데이터 유출 (ACL 누락)

- **시나리오**: 강의안 시나리오 B "멀티테넌트 챗" — 여러 고객사(테넌트)가 같은 서비스를
  쓰는데, 검색 인덱스가 테넌트 구분 없이 공유된다.
- **취약 경로** (`vulnerable_rag_search`): tenant_id 필터 없이 전체 코퍼스에서 검색 →
  테넌트 A의 기밀 계약 조건이 테넌트 B 사용자의 질문에 그대로 인용됨 (경로 P3)
- **보안 경로** (`secure_rag_search`): 검색 *전에* 요청자의 tenant_id로 코퍼스를 필터링
  → 타 테넌트 문서는 애초에 검색 대상에서 제외됨

이 예제가 예제 1보다 위험한 이유: 예제 1은 사용자 본인의 실수로 본인 정보가 나가는
경우지만, 이 예제는 **아무 잘못도 하지 않은 제3자(테넌트 A)의 기밀이 전혀 무관한
사용자(테넌트 B)에게** 노출된다 — 피해자가 유출 사실조차 알 방법이 없다.

## 예제 3: 메모리 포이즈닝을 통한 세션 간 지속 유출 (Memory Poisoning)

- **시나리오**: 강의안 용어표의 "Memory Poisoning" — 공격자가 자기 세션에서 "기억해줘"
  요청으로 공유 장기 메모리에 악성 지시를 심어두면, 이후 완전히 무관한 사용자의 세션이
  그 메모리를 재사용할 때마다 유출이 반복된다.
- **취약 경로** (`vulnerable_recall`): 공유 메모리를 소유자 구분 없이 전부 신뢰 컨텍스트로
  사용 → 공격자(user_alice)가 심어둔 지시가 무관한 사용자(user_charlie)에게 그대로
  재생되어, 제3자(user_bob)의 정보까지 유출 (경로 P6)
- **보안 경로** (`secure_recall`): 메모리 항목마다 원 소유자(owner_id)를 기록해두고,
  현재 요청자와 다른 소유자의 항목은 신뢰 컨텍스트에서 제외

이 시나리오가 예제 2보다 탐지하기 어려운 이유: 예제 2는 "지금 이 순간의 검색"만 통제하면
되지만, 이 예제는 **과거 어느 시점에 심어진 상태**가 미래의 모든 세션에 영향을 준다 —
공격 시점과 피해 시점이 분리돼 있어서, 유출이 일어난 세션의 로그만 봐서는 원인(오염
시점)을 못 찾는다.

## 보안 통제와 트레이드오프

| 통제 | 효과 | 비용/운영 부담 |
|---|---|---|
| Context Redaction (전송/로깅 전 마스킹) | 자격증명·PII가 벤더·로그로 나가기 전에 차단 | 정규식 기반은 형식 없는 비밀(평문 비밀번호 등)을 놓칠 수 있음 |
| 검색 단 ACL 필터링 (tenant_id 스코핑) | 교차 테넌트 유출을 검색 시점에 원천 차단 | 색인 시점 tenant_id 태깅이 정확해야 함, 문서 공유 정책이 복잡해지면 이진 필터로는 부족 |
| 메모리 소유자 격리 (owner_id 기반) | 세션 간 메모리 포이즈닝의 전파를 차단 | 팀 단위로 공유돼야 하는 메모리까지 막을 수 있음 — 세밀한 공유 범위(scope) 모델 필요 |
| 출력 필터/DLP (마지막 방어선) | 위 통제가 다 뚫려도 최종 응답에서 재차 차단 | 이 실습에는 미구현 — 실서비스에서는 반드시 추가해야 할 계층 |

우선순위: 세 예제 모두 "공격을 막는 것"이 아니라 "**신뢰 경계를 어디에 그을 것인가**"의
문제다 — 예제 1은 벤더로 나가기 전, 예제 2는 검색되기 전, 예제 3은 메모리에 반영되기
전에 경계를 그어야 사후 필터보다 안전하다(강의안 B.4 "완화 매핑"과 동일한 원칙).

## 잔여 위험

- **예제 1**: `_API_KEY_PATTERN`/`_EMAIL_PATTERN` 은 형식이 정해진 값만 잡는다. 평문
  비밀번호, 사내 코드네임, 주민등록번호 등 형식이 없거나 이 예제에 없는 패턴은 놓친다 —
  실서비스에서는 벤더별 시크릿 스캐너·DLP 도구와 병행해야 한다.
- **예제 2**: 문서에 tenant_id 태그가 정확히 붙어있다는 전제로 필터링한다. 색인 시점에
  태깅이 누락되거나 잘못되면 이 필터 자체가 무의미해진다 — 색인 파이프라인의 태깅
  정확성이 이 통제의 전제조건이다.
- **예제 3**: "소유자가 다르면 무조건 제외"라는 이진 규칙이다. 팀/조직 단위로 공유돼야
  하는 메모리(예: "우리 팀 공지사항 기억해줘")까지 막아버릴 수 있다 — 실서비스에서는
  소유자뿐 아니라 공유 범위(개인/팀/조직)를 함께 관리하는 모델이 필요하다.
- 세 예제 모두 mock 기반 결정론적 시뮬레이션이다. 실제 벡터 검색·실제 LLM 메모리
  요약 로직은 이보다 복잡하고, 실제 배포 전에는 대상 시스템 기준 침투 테스트/레드팀
  테스트가 필요하다. `run_real()`(로컬 실행 시 기본 실습)로 Ollama 모델 대상 재현이
  가능하지만, 이 역시 단일 모델·단일 프롬프트 결과일 뿐이다 — 모델이 마스킹된 값을
  무시하고 그럴듯한 값을 지어내는 환각까지 포함해 반복 검증이 필요하다.
