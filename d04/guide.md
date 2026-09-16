# RAG 권한 필터링 설계 가이드

외부 API 키 없이 재현 가능한 RAG 권한 필터링(Authorization Filtering) 실습 3건. ch04
"4-4. RAG 권한 필터링 설계" 강의안의 필터 삽입 위치(A.2), 인증 컨텍스트(B.2), 실패
모드(B.3)를 코드로 재현한다.

`ch04/d03`(데이터 유출)가 "ACL이 아예 없을 때 무슨 일이 생기는가"를 다뤘다면,
여기서는 **ACL을 "어떻게" 적용하느냐에 따라 그 설계 자체가 새는 지점**을 다룬다 — ACL
필터링 로직이 있어도, 어디에 놓느냐/무엇을 신뢰하느냐/누락을 어떻게 처리하느냐에 따라
여전히 뚫릴 수 있다.

## 구성 파일

| 파일 | 역할 | 강의안 매핑 |
|---|---|---|
| `rag_acl_mock.py` | 공용 결과 타입(`Verdict`). 세 예제가 함께 쓴다 | — |
| `prefilter_vs_postfilter.py` | 예제 1: Pre-filter vs Post-filter — 존재 여부 사이드채널 유출 | A.2, 경고 박스 |
| `role_spoofing.py` | 예제 2: 클라이언트 주장 role vs 서버 검증 role | B.2, 시나리오 B |
| `missing_metadata_policy.py` | 예제 3: ACL 메타데이터 누락 — Fail-open vs Fail-closed | B.3, 시나리오 A |
| `Dockerfile` | 의존성 없이 컨테이너에서 실행하기 위한 이미지 정의 (`d01~d03` 패턴) |  |
| `readme.md` | 사용자 작성 브리프 |  |

세 예제 모두 mock 기반 결정론적 시뮬레이션이며, 문서 내용·역할·조직 정보는 전부 가짜
(더미) 값이다.

## 실행 방법

### 로컬 (venv)
```
python prefilter_vs_postfilter.py
python role_spoofing.py
python missing_metadata_policy.py
```
각 스크립트 끝에 `assert` 기반 자동 검증이 포함되어 있어, 예외 없이 끝나면 예상대로
동작한 것이다.

### Docker
```
docker build -t rag-acl-filtering-demo .
docker run --rm rag-acl-filtering-demo                                     # 세 예제 순차 실행
docker run --rm rag-acl-filtering-demo python prefilter_vs_postfilter.py   # 예제 1만
docker run --rm rag-acl-filtering-demo python role_spoofing.py             # 예제 2만
docker run --rm rag-acl-filtering-demo python missing_metadata_policy.py   # 예제 3만
```

## 예제 1: Pre-filter vs Post-filter (존재 여부 사이드채널 유출)

- **배경**: 강의안 경고 박스 — "Post-filter만 쓰면 거절 전 점수나 타이밍으로 존재 여부가
  샐 수 있다." `d03`의 예제 2(교차 테넌트)와 다른 지점: 거기서는 문서 **내용**이
  그대로 노출됐지만, 여기서는 내용은 안 보여줘도 "그런 문서가 존재하고 지금 질문과 관련
  있다"는 **메타 정보**가 새어나간다.
- **취약 경로** (`vulnerable_post_filter_search`): 전체 코퍼스에서 검색부터 하고 권한
  체크는 나중에 함 → 거절 메시지 자체("관련도 높은 문서가 있으나 접근 권한이 없습니다")가
  비공개 문서의 존재를 노출
- **보안 경로** (`secure_pre_filter_search`): 검색 전에 role로 코퍼스를 먼저 제한 →
  비공개 문서는 애초에 검색 후보에 없어서 존재 여부조차 드러나지 않음

## 예제 2: 클라이언트 주장 role vs 서버 검증 role (역할 위조)

- **배경**: 강의안 시나리오 B "프론트 역할 토글" — "클라이언트가 보낸 `role=admin` 쿼리
  파라미터를 신뢰하지 않는다."
- **취약 경로** (`vulnerable_authorize`): 요청 필드 `claimed_role`을 그대로 필터에 사용 →
  실제로는 guest인 사용자가 요청 바디에 `role=admin`만 적어 보내도 관리자 전용 문서 노출
- **보안 경로** (`secure_authorize`): `claimed_role`은 무시하고 서버 세션 스토어(로그인
  시점에 검증된 토큰)에서 실제 role을 조회 → 클라이언트 주장과 무관하게 실제 권한만 적용

이 예제가 예제 1보다 근본적인 이유: 예제 1은 "필터가 있는데 어디 놓느냐"의 문제지만, 이
예제는 **필터에 넣는 입력값 자체가 신뢰할 수 없는 소스**라서, 필터 로직이 아무리 정교해도
소용없다 — OWASP의 "Broken Access Control"(신뢰할 수 없는 클라이언트 입력에 인가를
위임)에 해당하는 고전적이지만 여전히 흔한 실패 패턴이다.

## 예제 3: ACL 메타데이터 누락 (Fail-open vs Fail-closed)

- **배경**: 강의안 B.3 "메타 누락 시 기본 공개 → 대규모 유출" + 시나리오 A "메타 없이
  전 직원 인덱스". 마이그레이션 때 일부 레거시 문서에 ACL 태깅을 깜빡한 경우.
- **취약 경로** (`vulnerable_retrieve`, fail-open): ACL 메타데이터가 없는 문서를 "제한
  없음(공개)"으로 기본 처리 → 태깅을 깜빡한 인사평가 문서가 아무 role에게나 노출
- **보안 경로** (`secure_retrieve`, fail-closed): ACL 메타데이터가 없으면 "가장
  제한적(비공개)"으로 기본 처리해서 검색 후보에서 제외 → 태깅 누락이 유출로 이어지지 않음

## 완화(보안) 통제와 트레이드오프

| 통제 | 효과 | 비용/운영 부담 |
|---|---|---|
| Pre-filter (검색 전 권한 범위 제한) | 존재 여부 사이드채널까지 차단 | 벡터 DB가 메타데이터 기반 pre-filter 쿼리를 지원해야 함(강의안 A.3 "메타 필수") |
| 서버 측 role 조회(클라이언트 입력 무시) | role 위조를 원천 차단 | 세션/토큰 스토어 관리 필요, 토큰 검증·만료·폐기 로직 추가 |
| Fail-closed(메타 누락 시 기본 차단) | 태깅 누락이 대규모 유출로 번지는 것을 막음 | 원래 공개용이었던 문서까지 덩달아 숨겨질 수 있음(가용성 희생) — 근본 해결은 색인 시점 ACL 필수화 |
| 검색 감사 로그(거부/허용 이벤트 기록) | 탐지·사후 대응 근거 확보 | 이 실습엔 미구현 — 강의안 체크리스트의 마지막 항목 |

우선순위: 예제 2(신뢰할 수 없는 입력)가 가장 근본적인 실패이고, 예제 1(필터 위치)과
예제 3(기본값 정책)은 그 다음 층위의 설계 디테일이다. 셋 다 고쳐야 "필터가 있다"가 아니라
"필터가 실제로 작동한다"고 말할 수 있다.

## 잔여 위험

- **예제 1**: `secure_pre_filter_search()`도 완벽하지 않다 — role 목록 자체가 너무
  세분화되면(예: 부서별 수백 개 role) pre-filter 쿼리가 복잡해지고 성능이 나빠질 수
  있다. 강의안 A.2의 "Hybrid(권장)" 방식처럼 pre-filter + post-filter 재검증을 함께
  두는 게 현실적인 절충안이다.
- **예제 2**: 이 예제의 "서버 세션 스토어"는 dict로 단순화했다. 실제로는 토큰 서명
  검증, 만료, 폐기(revocation) 목록까지 다뤄야 하고, 세션 스토어 자체가 공격받으면
  (세션 고정, 토큰 탈취 등) 이 방어도 무력화된다.
- **예제 3**: fail-closed는 "안전하지만 가용성을 희생"하는 임시방편이다. 태깅이 누락된
  진짜 공개 문서까지 숨겨버리는 부작용이 있다 — 근본 해결은 색인 파이프라인에서 ACL
  필드를 필수(NOT NULL)로 강제하고, 누락 시 색인 자체를 거부하는 것이다.
- 세 예제 모두 mock 기반 결정론적 시뮬레이션이다. 실제 벡터 DB(예: Chroma, Pinecone)의
  pre-filter 쿼리 문법과 성능 특성은 이보다 복잡하며, 실제 배포 전에는 대상 시스템 기준
  침투 테스트가 필요하다.
