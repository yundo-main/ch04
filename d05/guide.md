# 문서 보안 등급 체계 설계 가이드

외부 API 키 없이 재현 가능한 문서 보안 등급(Classification) 실습 3건. ch04
"4-5. 문서 보안 등급 체계 설계" 강의안의 등급 부여 프로세스(A.3), 청크 상속
(A.4), 클리어런스 모델(B.1)을 코드로 재현한다.

`ch04/d04`(RAG 권한 필터링)가 "역할(role) 기반으로 문서를 걸러내는
로직 자체가 새는 지점"을 다뤘다면, 여기서는 **그 이전 단계 — 문서에 붙는
등급(classification) 자체가 잘못 매겨지거나 위조·하향되는 지점**을 다룬다.
필터링 로직이 완벽해도, 입력값인 등급 메타데이터가 신뢰할 수 없으면 소용없다.

## 등급 정의서 (Classification Policy)

체크리스트 "등급 정의서·예시" 항목. `documents.json`의 `classification` 값과
`doc_classification_mock.py`의 `Classification` 열거형은 이 정의를 그대로
코드로 옮긴 것이다.

### Public

- 전 사용자(비로그인 포함) 검색 가능
- 노출되어도 보안/사업 영향이 매우 낮음
- 예: 헬프센터, 공개 블로그, 공개 FAQ

### Internal

- 임직원 전용, 외부 공개용 아님
- 노출 시 관리상 불편은 있으나 치명도는 낮음
- 예: 사내 위키 일반, 온보딩 안내, 운영 체크리스트

### Confidential

- 필요 역할(need-to-know) + 접근 감사 로그 필수
- 노출 시 고객 피해, 계약 분쟁, 사업 손실 가능
- 예: 고객 사례, 계약 요약, 영업 파이프라인 메모

### Restricted

- 최소 인원만 접근, 별도 인덱스/서비스 계정 분리 검토 대상(B.2)
- 노출 즉시 악용 가능하거나 직접적 침해로 이어짐
- 예: M&A 자료, 급여, 의료 정보, 키 자료, 임원 보상 체계

### 등급 부여 규칙 (A.3 인제스트 게이트 매핑)

| 규칙 | 결과 등급 | 위반 시 인제스트 동작 |
| --- | --- | --- |
| 경로 `/public/` | Public | — |
| 부서 공유 드라이브 | Internal | — |
| `salary`, `ssn` 등 키워드 매치 | Restricted 후보(오너 확인 필요) | 오너 확인 전 quarantine |
| 법무 태그 | Confidential 이상 | — |
| classification 필드 없음 | (정의되지 않음) | **거부 또는 quarantine** — 예제 1 참고 |

### 클리어런스 대응표 (B.1)

| 사용자 clearance | 검색 가능 최대 등급 |
| --- | --- |
| L1 | Public |
| L2 | Internal |
| L3 | Confidential |
| L4 | Restricted |

### 재분류·파생물 규칙 (A.4)

- 청크는 문서 등급을 **상속**한다. 한 청크라도 상위 등급 요건(예: 주민번호
  포함)을 만족하면 그 청크만 **상향** 가능 — 하향은 금지.
- 요약·발췌 등 파생 산출물의 등급은 `max(원문 등급, 파생물 자체 산정 등급)`
  이어야 한다 — 예제 3 참고.
- 등급 하향(재분류)은 오너 승인 없이는 금지 — 예제 2 참고.

## 구성 파일

| 파일 | 역할 | 강의안 매핑 |
|---|---|---|
| `documents.json` | **실습용 문서** — 위 등급 정의서에 따라 태깅된 샘플 문서 세트(Metadata Tagging 예시: classification/owner/allowed_roles/canary_token/tenant_id). 이 폴더 전용 로컬 복사본(d00-shared 공유 없음) — d06~d08도 같은 내용을 각자 로컬로 갖고 있다 | 용어: Metadata Tagging |
| `doc_classification_mock.py` | 공용 타입(`Classification`, `Clearance`, `Verdict`) + `load_sample_documents()`(정의서 대비 등급값 검증) | A.2, B.1 |
| `default_classification_missing.py` | 예제 1: 인제스트 시 등급 미지정 — 기본값 Public 취약점 | 시나리오 A, A.3 |
| `classification_spoofing.py` | 예제 2: 클라이언트 주장 등급 vs 서버 검증 등급 (등급 위조) | 시나리오 B, A.3 |
| `downgrade_on_summarization.py` | 예제 3: 요약본 하향 재분류 — 청크 상속 원칙 위반 | 시나리오 C, A.4 |
| `Dockerfile` | 의존성 없이 컨테이너에서 실행하기 위한 이미지 정의 (`d01~d04` 패턴) | — |
| `readme.md` | 사용자 작성 브리프 | — |

`documents.json`은 5개 문서로 4개 등급을 모두 예시하는 **정상 태깅 기준선**이다.
세 예제는 여기서 이미 올바르게 태깅된 문서(주로 Public)를 정상 케이스로 가져오고,
그 옆에 등급 처리 로직이 깨지는 지점을 재현할 결함 있는 문서 하나씩을 추가해
비교한다 — 예제 1의 `ma-draft-2025`(등급 미지정), 예제 2의 재색인 요청,
예제 3의 요약 파생물이 그것이다. 결함 문서를 포함한 조직 정보는 전부
가짜(더미) 값이다.

## 실행 방법

### 로컬 (venv)
```
python default_classification_missing.py
python classification_spoofing.py
python downgrade_on_summarization.py
```
각 스크립트 끝에 `assert` 기반 자동 검증이 포함되어 있어, 예외 없이 끝나면
예상대로 동작한 것이다.

### Docker

**빌드 컨텍스트**: `documents.json`은 이 폴더 로컬 파일이라 d05 자체는
d00-shared에 의존하지 않지만, 다른 dNN과 동일한 빌드 명령 패턴을 유지하기
위해 컨텍스트를 **`ch04/` 루트**로 맞췄다 — `cd ch04` 후 `-f d05/Dockerfile`로
빌드한다.

```
cd ch04
docker build -f d05/Dockerfile -t doc-classification-demo .
docker run --rm doc-classification-demo                                              # 세 예제 순차 실행
docker run --rm doc-classification-demo python default_classification_missing.py     # 예제 1만
docker run --rm doc-classification-demo python classification_spoofing.py            # 예제 2만
docker run --rm doc-classification-demo python downgrade_on_summarization.py         # 예제 3만
```

## 예제 1: 인제스트 시 등급 미지정 (기본값 Public 취약점)

- **배경**: 강의안 시나리오 A "업로드 API 기본 classification 누락 → 전부
  검색 가능" + A.3 인제스트 게이트("등급 미지정 → 임베딩 거부 또는
  quarantine").
- **취약 경로** (`vulnerable_ingest`): classification 필드가 없는 업로드를
  `Classification.PUBLIC`으로 기본 처리 → 등급 지정을 깜빡한 M&A 실사 초안이
  가장 낮은 clearance(L1) 사용자에게도 그대로 검색됨.
- **보안 경로** (`secure_ingest`): classification이 없으면 quarantine 상태로
  두어 검색 후보에서 제외 → 등급 지정 누락이 즉시 유출로 이어지지 않음.

## 예제 2: 클라이언트 주장 등급 vs 서버 검증 등급 (등급 위조)

- **배경**: 강의안 시나리오 B "클라이언트가 `classification=public`으로
  재색인 요청, 서버 오너 검증 없음".
- **취약 경로** (`vulnerable_reindex`): 재색인 요청에 실려온 classification
  값을 오너 승인 검증 없이 그대로 반영 → Restricted 실사 보고서가 요청자
  주장만으로 Public으로 하향됨.
- **보안 경로** (`secure_reindex`): 하향 요청은 `owner_approved` 플래그가
  없으면 거부하고 기존 등급을 유지 → 검증된 절차 없이는 등급이 낮아지지
  않음.

이 예제가 예제 1보다 근본적인 이유: 예제 1은 "등급이 아예 없을 때"의 문제지만,
이 예제는 **이미 올바르게 매겨진 등급이 검증되지 않은 요청만으로 뒤집힌다**는
점에서 d04의 역할 위조(`role_spoofing.py`)와 같은 계열의 실패 패턴
(OWASP "Broken Access Control")이다.

## 예제 3: 요약본 하향 재분류 (청크 상속 원칙 위반)

- **배경**: 강의안 A.4 "청크 상속: 문서 등급이 기본이고, 청크는 상속 +
  상향만" + 시나리오 C "Restricted 원문을 Internal 요약으로 잘못 재분류".
- **취약 경로** (`vulnerable_summarize`): 요약 서비스가 산출물 등급을 원문
  등급과 무관하게 콘텐츠만 보고 재산정 → Restricted 임원 보상 문서의 요약이
  Internal로 낮아져 L2 사용자에게 노출.
- **보안 경로** (`secure_summarize`): 요약본 등급을
  `max(원문 등급, 서비스 추정값)`으로 강제 → 파생 산출물이라는 이유로 원문
  보다 낮은 등급이 될 수 없음.

## 보안 통제와 트레이드오프

| 통제 | 효과 | 비용/운영 부담 |
|---|---|---|
| 인제스트 게이트(등급 미지정 시 quarantine) | 등급 누락이 즉시 전체 공개로 이어지는 것을 차단 | 업로드 담당자 워크플로에 "보류함" 처리·알림 단계 추가 필요 |
| 하향 재색인 시 오너 승인 필수 | 요청 필드 위조만으로 등급이 낮아지는 것을 차단 | 승인 워크플로/감사 로그 관리 필요(강의안 B.4 재분류 감사) |
| 청크·파생물 등급 상속(상향만) | 요약·발췌본을 통한 우회 유출 차단 | 파생물이 원문보다 과도하게 높은 등급으로 묶여 검색 가용성이 낮아질 수 있음 |
| 재분류 감사 로그 | 등급 변경 이력 추적, 탐지·사후 대응 근거 확보 | 이 실습엔 미구현 — 강의안 체크리스트의 마지막 항목 |

우선순위: 예제 1(등급 미지정)이 가장 흔히 발생하는 운영 실수이고, 예제
2(위조)는 신뢰 경계 설계 결함, 예제 3(파생물 하향)은 그 다음 층위인 파이프라인
설계 디테일이다. 셋 다 고쳐야 "등급 체계가 있다"가 아니라 "등급 체계가 실제로
지켜진다"고 말할 수 있다.

## 잔여 위험

- **예제 1**: `secure_ingest()`의 quarantine은 등급 지정 누락 문서를 그저
  검색에서 빼는 것일 뿐, 담당자가 뒤늦게라도 등급을 지정하지 않으면 그
  문서는 영구히 검색 불가능한 상태로 남는다. 근본 해결은 업로드 폼에서
  classification을 필수 입력으로 강제하는 것이다.
- **예제 2**: 이 예제의 "오너 승인(`owner_approved`)"은 불리언 플래그로
  단순화했다. 실제로는 승인자 신원 검증, 승인 이력 서명, 승인 요청 자체의
  위조 방지까지 다뤄야 하며, 승인 워크플로가 공격받으면(예: 승인자 계정
  탈취) 이 방어도 무력화된다.
- **예제 3**: `max(원문, 추정값)` 강제는 "요약본이 원문보다 낮아지지 않는다"
  만 보장할 뿐, 요약 자체가 원문의 민감 정보를 얼마나 담고 있는지는 별도로
  검증하지 않는다 — 요약이 원문 내용을 그대로 인용하면 등급과 무관하게
  내용 유출 위험이 남는다(별도의 콘텐츠 기반 DLP 스캔 필요).
- 세 예제 모두 mock 기반 결정론적 시뮬레이션이다. 실제 벡터 DB(예: Chroma,
  Pinecone)의 메타데이터 필터 쿼리 문법과 인제스트 파이프라인의 동시성
  특성은 이보다 복잡하며, 실제 배포 전에는 대상 시스템 기준 침투 테스트가
  필요하다.
