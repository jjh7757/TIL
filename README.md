# AI Agent 엔지니어 부트캠프 TIL

AI Agent 엔지니어 부트캠프에서 배운 내용을 정리하는 저장소입니다.

## 학습 타임라인 (날짜 → 문서)

각 문서를 처음 커밋한 날짜 기준입니다.

| 날짜 | 다룬 문서 |
|------|-----------|
| 2026-07-23 | [Git 명령어 정리](github실습/Git명령어정리.md), [MD 문법 사용 예시 모음](github실습/MarkDownTest.md), [기준선 작성](프로그램방법론/기준선작성.md) |
| 2026-07-24 | [AI와 함께 찾은 나의 강점](Claude실습/나의강점.md) |
| 2026-07-26 | [AI 리터러시 & LLM 애플리케이션 입문](CS지식/LLM_APP입문.md), [프로젝트를 바라보는 방법](프로그램방법론/프로젝트를바라보는방법.md), [기준선 작성 참고](프로그램방법론/기준선작성참고.md), [프로젝트 도구](프로그램방법론/프로젝트도구.md) |
| 2026-07-27 | [n8n](n8n실습/n8n.md), [프롬프트 엔지니어링](CS지식/프롬프트엔지니어링.md), [구글 폼 3개 입력받으면 이메일 보내기](n8n실습/구글폼3개입력받으면이메일보내기.md) |
| 2026-07-28 | [Claude 기본](Claude실습/claude기본.md), [커밋 잘 쓰는 법](github실습/commit잘쓰는법.md), [게임만들기 — Maze Relay](Claude실습/게임만들기/README.md) |
| 2026-07-29 | [API 실습 — 간단 사주 보기](Claude실습/api실습/사주프로그램/사주보기.md), [API 기초](CS지식/API기초.md) |
| 2026-07-30 | [내 자동화 봇 소개](n8n실습/내자동화봇소개.md), [AI Agent란 — 서비스 구조와 실행 환경](CS지식/AIAgent구조.md) |
| 2026-07-31 | [URL 구조](CS지식/URL구조.md), [HTTP 기초](CS지식/HTTP기초.md), [HTTP 상태 코드](CS지식/HTTP상태코드.md) |
| 2026-08-01 | [금융투자봇 — KIS 모의투자 연동 텔레그램 AI 에이전트](n8n실습/금융투자봇/README.md), [아침 자동화 봇 커스터마이징](n8n실습/내자동화봇커스터마이징.md), [미니프로젝트 아이디어 초안](프로그램방법론/미니프로젝트아이디어초안.md) |
| 2026-08-02 | [한국투자증권 Open API 연동 가이드](n8n실습/금융투자봇/KIS_API_연동가이드.md) |
| 2026-08-03 | [소프트웨어 종류](CS지식/소프트웨어종류.md), [컴퓨터 구조](CS지식/컴퓨터구조.md), [웹 서비스 구조](CS지식/웹서비스구조.md), [맛집 추천 서비스 기준선](vercel실습/맛집추천서비스/맛집추천서비스기준선.md), [DB 설계](vercel실습/맛집추천서비스/맛집추천서비스DB설계.md), [화면 설계](vercel실습/맛집추천서비스/맛집추천서비스화면설계.md), [구현 정리](vercel실습/맛집추천서비스/맛집추천서비스구현.md) |
| 2026-08-04 | [웹 디자인 기초](CS지식/웹디자인기초.md), [맛집 추천 서비스 구현 정리 업데이트](vercel실습/맛집추천서비스/맛집추천서비스구현.md) — 디자인 시스템 적용, 네이버/Gemini API 위치 기반 추천 추가, [KIS 모의투자 텔레그램 에이전트 기획서](KIS-Agent-Notes/01_Baseline/01_project_statement.md) — 기준선~실행계획 17개 문서 (KIS-Agent-Notes), [RSS 기초](CS지식/RSS기초.md) |
| 2026-08-05 | [고객VOC분석Agent — VOC 자동 분류·긴급 알림 파이프라인](n8n실습/고객VOC분석Agent/README.md) — Google Form 접수부터 Gemini 분류·중복 방지·검증 안전판·Discord 긴급 알림까지 무인 파이프라인 미니프로젝트 |
| 2026-08-06 | [금융뉴스브리핑Agent — 금융 뉴스 자동 브리핑 시스템](n8n실습/금융뉴스브리핑Agent/README.md) — RSS 수집·중복 차단·금융 키워드 필터·본문 추출·Gemini 요약/중요도 분류를 거쳐 매일 아침 디스코드로 브리핑하는 자동화 미니프로젝트 |
| 2026-08-08 | [왜샀어(WhyBuy) — 근거를 남겨야 완료되는 모의투자 서비스](vercel실습/왜샀어/왜샀어구현.md) — KIS 모의투자 API로 실제 매수·매도 주문을 내되 판단 근거를 강제하는 Next.js 웹 서비스. 초당 1건 레이트리밋 해결, 지정가 주문 도입에 따른 상태 모델 재설계, AI 해석 안전장치, 공유 모의계좌의 자본시장법상 리스크 검토까지 정리 |
| 2026-08-10 | [왜샀어 발표자료](vercel실습/왜샀어/왜샀어_발표.pptx) — 왜샀어(WhyBuy) 프로젝트 발표용 pptx |
| 2026-08-11 | [파이썬 기초](CS지식/파이썬기초/README.md) — 변수·자료형·연산자·입출력·조건문·리스트·반복문 7개 주제 정리 |
| 2026-08-12 | [Docker로 n8n 셀프호스팅하고 Telegram 웹훅 연동하기](n8n실습/Docker로n8n셀프호스팅하기.md) — Windows Home + WSL2 + Docker Desktop 설치 트러블슈팅, ngrok으로 로컬 웹훅 공개, ngrok vs Cloudflare Tunnel 비교, [컨테이너 기반 배포 기초](CS지식/컨테이너배포기초.md) — 이미지·레지스트리·배포 대상(Cloud Run/K8s/VM/PaaS)·Docker Compose 개념 정리, [왜샀어 Docker 배포 전환 기획서](https://github.com/jjh7757/whybuy/blob/master/KIS-Web-Agent-Notes/08_Deploy/01_docker_migration.md) — 서버리스에서 상주 프로세스로 옮겨 KIS 레이트리밋 큐 단일성·체결 확인 스케줄러 한계를 해소하는 이관 계획 (whybuy 저장소) |
| 2026-08-13 | [파이썬 기초](CS지식/파이썬기초/README.md) 문자열·집합과 튜플·딕셔너리·함수·모듈 5개 주제 추가 — 문자열 포매팅과 메서드, 집합 연산과 튜플, 딕셔너리 키-밸류 조작, 함수의 구조와 내장함수, math·random·collections·itertools 표준 모듈 |
| 2026-08-14 | [왜샀어 Docker 배포 전환 작업 로그](vercel실습/왜샀어/Docker배포전환.md) — Vercel에서 네이버클라우드 Micro Server(Docker 셀프호스팅)로 옮기는 실제 작업 기록 시작. 서버 업체 재선정(오라클 홈 리전 이슈로 네이버클라우드 전환), SSH·sshd 트러블슈팅, 스왑·Docker·ufw 구성, 도메인 연결과 Caddy HTTPS 발급, OAuth 리다이렉트 URI 등록까지 |
| 2026-08-15 | [왜샀어 Docker 배포 전환 작업 로그](vercel실습/왜샀어/Docker배포전환.md) 이어서 진행 — 리버스 프록시 뒤에서 로그인 리다이렉트가 컨테이너 자체 hostname으로 새던 버그 추적·수정(Next.js standalone origin 이슈), 반복 재빌드 중 디스크 풀·SSH 연결 불안정 트러블슈팅, 로컬 Docker Desktop 복구. 로그인·조회·레이트리밋·분봉차트·재시작 내구성 검증(T2~T5, T7) 통과, whybuy 저장소에 Docker 배포 코드 반영 |
| 2026-08-16 | [다크패턴 스캐너 — 쇼핑몰 다크패턴 자동 진단 프로토타입](다크패턴스캐너/README.md) — 카운트다운 리셋 탐지(A/B/C 세 조건 재방문 비교)와 체크아웃 단계별 총액 추적을 Playwright로 구현, 정답을 아는 fixture 6종으로 자체 검증(8/8 통과, 오탐 0건). 경쟁 제품(Shopify StoreHQ, 카페24 Sentio5)이 관리자 API 설정값만 보는 것과 달리 실제 렌더링·상호작용을 검증하는 것이 차별점 |
| 2026-08-17 | [다크패턴 스캐너 — 실사이트 검증 및 보류](다크패턴스캐너/README.md) — 무신사·카페24 쇼케이스 브랜드(오롤리데이·쿤달) 등 실사이트 4곳에 스캐너를 돌려 실제 버그 4개(캐러셀 오탐·타이밍, select 직후 클릭 경합, open shadow DOM 위젯 사각지대)를 찾아 고쳤으나 다크패턴은 4연속 미발견. 표본이 "다크패턴이 없을 법한 곳"에 편중된 한계와 "셀러가 이 스캔에 돈을 낼 것인가"라는 미검증 수요 문제를 정리해 프로젝트 보류 결정 ([기획서](다크패턴스캐너/기획서.md) 9장) |
| 2026-08-18 | [파이썬 기초 — 스코프](CS지식/파이썬기초/13_스코프.md) — 함수 내부/외부 변수 접근 범위, LEGB 규칙(Local·Enclosed·Global·Built-in), enclosed 스코프와 중첩 함수, `global` 키워드로 외부 값을 바꾸는 예외 상황과 실무에서 지양해야 하는 이유, 파이썬은 if/for에 block scope가 없다는 점 정리, [알고리즘](CS지식/알고리즘/README.md) — 2차원 배열 인덱싱과 참조 함정, 델타 탐색으로 상하좌우 이웃 확인, 회문 판별 네 가지 방법(슬라이싱·반복·절반 비교·투 포인터), 카운팅·버블·선택 정렬 정리 |
| 2026-08-19 | [파이썬 기초 — 예외 처리](CS지식/파이썬기초/14_예외처리.md) — try/except 기본 구조, 특정·다중 예외 처리, `as`로 예외 객체 참조, else/finally, raise로 예외 강제 발생, 사용자 정의 예외 클래스, [알고리즘 — 큐와 스택](CS지식/알고리즘/05_큐와스택.md) — `collections.deque`가 list보다 양끝 삽입/삭제에 유리한 이유, 올바른 괄호(스택으로 여러 종류 괄호 짝 검사), 다리를 지나는 트럭(큐로 다리 위 상태 시뮬레이션), [알고리즘 — 나선형 배열](CS지식/알고리즘/06_나선형배열.md) — 방향 벡터를 순환시켜 시계방향 나선을 채우고, 범위 이탈과 중복 방문을 함께 체크하는 방법, [requests로 API 호출하기](CS지식/requests실습.md) — GET/POST/PATCH/PUT/DELETE 실습, params·headers 옵션, Timeout·HTTPError·RequestException 예외 처리 |

## 목차

### Claude실습
- [Claude 기본](Claude실습/claude기본.md) — Chat / Cowork / Code 비교
- [AI와 함께 찾은 나의 강점](Claude실습/나의강점.md) — AI와의 대화로 정리한 나의 강점 3가지
- [게임만들기 — Maze Relay](Claude실습/게임만들기/README.md) — 도트 던전 미로 탈출 게임. 플레이어끼리 Supabase로 메시지를 릴레이하며 죽일지 살릴지 판정하는 비동기 멀티플레이 구조 (원본: [maze-relay](https://github.com/jjh7757/maze-relay))
- [API 실습 — 간단 사주 보기](Claude실습/api실습/사주프로그램/사주보기.md) — 브라우저에서 Gemini API를 직접 호출해 사주를 해석해주는 프론트엔드 실습

### Github 실습
- [Git 명령어 정리](github실습/Git명령어정리.md) — Git 기본 사용 흐름
- [커밋 잘 쓰는 법](github실습/commit잘쓰는법.md)
- [MD 문법 사용 예시 모음](github실습/MarkDownTest.md)

### n8n 실습
- [n8n](n8n실습/n8n.md) — 노코드 자동화 툴 소개
- [구글 폼 3개 입력받으면 이메일 보내기](n8n실습/구글폼3개입력받으면이메일보내기.md)
- [내 자동화 봇 소개](n8n실습/내자동화봇소개.md) — 사주·날씨 기반 오늘의 운세 디스코드 봇
- [금융투자봇 — KIS 모의투자 연동 텔레그램 AI 에이전트](n8n실습/금융투자봇/README.md) — 한국투자증권 모의투자 API를 tool로 쓰는 AI Agent 투자 어드바이저 봇 (금융권 포트폴리오용)
- [한국투자증권 Open API 연동 가이드](n8n실습/금융투자봇/KIS_API_연동가이드.md) — n8n HTTP Request 노드로 KIS 모의투자 API(토큰 발급, 시세·잔고·거래내역 조회) 연동하는 설정값 정리
- [아침 자동화 봇 커스터마이징](n8n실습/내자동화봇커스터마이징.md) — 사주·날씨·맛집 추천 기능을 추가한 봇 커스터마이징
- [고객VOC분석Agent — VOC 자동 분류·긴급 알림 파이프라인](n8n실습/고객VOC분석Agent/README.md) — Google Form 접수 → 중복 방지 → Gemini 분류 → 검증 안전판 → 시트 저장 → Discord 긴급 알림까지 무인 자동화한 미니프로젝트
- [금융뉴스브리핑Agent — 금융 뉴스 자동 브리핑 시스템](n8n실습/금융뉴스브리핑Agent/README.md) — 매일 08:30 RSS 3개 매체 수집 → 중복 차단 → 금융 키워드 필터 → 본문 추출 → Gemini 요약·중요도 분류 → Discord 브리핑 발송까지 무인 자동화한 미니프로젝트
- [Docker로 n8n 셀프호스팅하고 Telegram 웹훅 연동하기](n8n실습/Docker로n8n셀프호스팅하기.md) — Windows Home(WSL2 필수) 환경에서 Docker Desktop 설치 트러블슈팅, n8n 컨테이너 실행, ngrok으로 로컬 웹훅을 공개해 Telegram Trigger 연동

### 프로그램 방법론
- [프로젝트를 바라보는 방법](프로그램방법론/프로젝트를바라보는방법.md) — 프로젝트/프로덕트/운영 구분, WBS, 마일스톤
- [기준선 작성](프로그램방법론/기준선작성.md) — v0.1~v1.0 버전별 프로젝트 기준선(목적·도메인·데이터·이벤트·아키텍처·MVP·완료 기준) 12개 항목
- [기준선 작성 참고](프로그램방법론/기준선작성참고.md) — 도메인·데이터·이벤트·네이밍 컨벤션·아키텍처·방법론(Waterfall/Agile)·MVP 개념 정리
- [프로젝트 도구](프로그램방법론/프로젝트도구.md) — Obsidian, Notion, Jira, GitHub 역할 구분
- [미니프로젝트 아이디어 초안](프로그램방법론/미니프로젝트아이디어초안.md) — 금융투자봇을 리스크 경고·알림·리포트 기능으로 확장한 최종 아이디어

### Vercel 실습
- [맛집 추천 서비스 기준선](vercel실습/맛집추천서비스/맛집추천서비스기준선.md) — 예산 기반 맛집 추천 미니프로젝트 기준선 v0.1
- [맛집 추천 서비스 DB 설계](vercel실습/맛집추천서비스/맛집추천서비스DB설계.md) — `restaurants` 단일 테이블 설계, RLS 정책, 예산 필터링 쿼리
- [맛집 추천 서비스 화면 설계](vercel실습/맛집추천서비스/맛집추천서비스화면설계.md) — 목록/상세/등록 화면 흐름과 DB 필드 매핑
- [맛집 추천 서비스 구현 정리](vercel실습/맛집추천서비스/맛집추천서비스구현.md) — 화면 5개 스크린샷과 구현 내용 정리, 무드보드 기반 디자인 시스템·네이버 지역 검색(NCP)/Gemini API 위치 기반 추천 업데이트 포함 (구현 저장소: [jjh7757/bitebudget](https://github.com/jjh7757/bitebudget))
- [왜샀어(WhyBuy) — 기획과 구현 정리](vercel실습/왜샀어/왜샀어구현.md) — KIS 모의투자 API로 실제 매수·매도 주문을 내되 근거를 강제하는 서비스. 텔레그램 봇([KIS-Agent-Notes](KIS-Agent-Notes/01_Baseline/01_project_statement.md))에서 웹 폼으로 피벗한 배경, KIS 레이트리밋(EGW00201) 해결, 지정가 주문 도입에 따른 주문 상태 모델 재설계, AI 안전장치, 공유 모의계좌의 자본시장법상 리스크 검토 (구현 저장소: [jjh7757/whybuy](https://github.com/jjh7757/whybuy))

### 다크패턴스캐너 (보류)
- [다크패턴 스캐너 — 쇼핑몰 다크패턴 자동 진단 프로토타입](다크패턴스캐너/README.md) — 카운트다운 리셋 탐지·체크아웃 단계별 총액 추적을 Playwright로 구현, fixture 6종 자체 검증(8/8) 후 실사이트 4곳 검증까지 마쳤으나 다크패턴 미발견으로 보류. [기획서](다크패턴스캐너/기획서.md)에 시장 근거·경쟁 조사·실사이트 검증 결과·보류 사유 전부 정리

### KIS-Agent-Notes (KIS 모의투자 텔레그램 에이전트 기획)
[금융투자봇](n8n실습/금융투자봇/README.md) 아이디어를 5일 개인 프로젝트로 구체화한 기획서. [기준선 작성](프로그램방법론/기준선작성.md)의 12개 항목 템플릿을 그대로 적용해 기준선부터 실행계획까지 정리.

- **01_Baseline** — [프로젝트 한 문장](KIS-Agent-Notes/01_Baseline/01_project_statement.md)(성공 기준을 "수익"이 아닌 "판단 근거 설명 가능"으로 잡은 이유, 확인한 사실 7개·미검증 가정 5개), [프로젝트 기준선](KIS-Agent-Notes/01_Baseline/02_project_baseline.md)(목적·도메인·데이터·이벤트·아키텍처·범위·완료 기준 12개 항목)
- **02_Domain** — [도메인 요소](KIS-Agent-Notes/02_Domain/01_domain_elements.md), [사용자 역할](KIS-Agent-Notes/02_Domain/02_user_roles.md), [정상·예외 업무 흐름](KIS-Agent-Notes/02_Domain/03_workflow.md)(정상 흐름 4개·예외 흐름 11개)
- **03_Data_Event** — [데이터 구조 초안](KIS-Agent-Notes/03_Data_Event/01_data_structure.md), [데이터 소스](KIS-Agent-Notes/03_Data_Event/02_data_sources.md), [이벤트 카탈로그](KIS-Agent-Notes/03_Data_Event/03_event_catalog.md)(과거형 snake_case 도메인 이벤트 7개), [용어와 네이밍 컨벤션](KIS-Agent-Notes/03_Data_Event/04_naming_convention.md)
- **04_Architecture** — [데이터 흐름](KIS-Agent-Notes/04_Architecture/01_data_flow.md), [아키텍처](KIS-Agent-Notes/04_Architecture/02_architecture.md)(텔레그램 → n8n 메인 워크플로우 + 서브 워크플로우 4개 → KIS 모의투자 Open API, 비용 낮은 순 검증)
- **05_Scope** — [MVP 범위와 기능 우선순위](KIS-Agent-Notes/05_Scope/01_mvp_scope.md), [완료 기준과 체크리스트](KIS-Agent-Notes/05_Scope/02_definition_of_done.md)
- **06_WBS** — [WBS — 개발 작업 분해](KIS-Agent-Notes/06_WBS/01_wbs.md), [5일 마일스톤과 위험](KIS-Agent-Notes/06_WBS/02_milestones.md)(2026-08-05~09 개발, 08-10 발표)
- **07_GitHub** — [GitHub README 초안](KIS-Agent-Notes/07_GitHub/01_readme_draft.md), [2분 발표자료 초안](KIS-Agent-Notes/07_GitHub/02_presentation.md)

### CS지식
- [AI 리터러시 & LLM 애플리케이션 입문](CS지식/LLM_APP입문.md)
- [프롬프트 엔지니어링](CS지식/프롬프트엔지니어링.md) — 좋은 프롬프트 4요소, 하네스/컨텍스트 엔지니어링, Claude Code 스킬 추가하는 방법, CoT·ReAct·Tree-of-Thought
- [URL 구조](CS지식/URL구조.md) — scheme/authority/path/query/fragment 등 URL 구성 요소 정리
- [HTTP 기초](CS지식/HTTP기초.md) — 요청/응답 구조, 메서드, 상태 코드, 무상태 특징 정리
- [HTTP 상태 코드](CS지식/HTTP상태코드.md) — 1XX~5XX 분류와 리다이렉션 개념 정리
- [API 기초](CS지식/API기초.md) — API 개념, REST API, API 키/인증 정리
- [AI Agent란 — 서비스 구조와 실행 환경](CS지식/AIAgent구조.md) — Client/Agent/Server/DB/Cloud 구조와 클라우드가 필요한 이유
- [소프트웨어 종류](CS지식/소프트웨어종류.md) — 웹/모바일/데스크탑 분류와 FE·BE, Android·iOS, 크로스플랫폼(Flutter, React Native) 정리
- [컴퓨터 구조](CS지식/컴퓨터구조.md) — CPU·MB·RAM·SSD/HDD 하드웨어 구성과 프로그램·프로세스·스레드 관계 정리
- [웹 서비스 구조](CS지식/웹서비스구조.md) — Client-Server(FE/BE) 구조, HTTP(요청/응답)와 API 통신 정리
- [웹 디자인 기초](CS지식/웹디자인기초.md) — 화면 설계 전 방향을 잡는 무드보드(Pinterest 활용법·AI로 디자인 시스템/프로토타입 뽑는 프롬프트 예시 포함), 미디어 쿼리·뷰포트 기반 반응형 웹과 모바일 퍼스트 전략 비교
- [RSS 기초](CS지식/RSS기초.md) — RSS 동작 방식과 예시 구조, 알고리즘 없이 구독하는 장점, 웹훅과의 pull/push 차이
- [파이썬 기초](CS지식/파이썬기초/README.md) — 변수·자료형·연산자·입출력·조건문·리스트·반복문·문자열·집합과 튜플·딕셔너리·함수·모듈·스코프·예외 처리 14개 주제 정리
- [컨테이너 기반 배포 기초](CS지식/컨테이너배포기초.md) — 컨테이너 vs VM, Dockerfile·이미지·레지스트리 흐름, 배포 대상(관리형 컨테이너 서비스/쿠버네티스/VM/PaaS) 비교, Docker Compose
- [알고리즘](CS지식/알고리즘/README.md) — 2차원 배열과 참조 함정, 델타 탐색으로 상하좌우 이웃 확인, 회문 판별 네 가지 방법, 카운팅·버블·선택 정렬, 큐와 스택(deque), 나선형 배열 6개 주제 정리
- [requests로 API 호출하기](CS지식/requests실습.md) — GET/POST/PATCH/PUT/DELETE 메서드별 사용법, params·headers 옵션, Timeout·HTTPError 예외 처리
