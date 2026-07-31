# AI Agent 엔지니어 부트캠프 TIL

AI Agent 엔지니어 부트캠프에서 배운 내용을 정리하는 저장소입니다.

## 학습 타임라인 (날짜 → 문서)

각 문서를 처음 커밋한 날짜 기준입니다.

| 날짜 | 다룬 문서 |
|------|-----------|
| 2026-07-23 | [Git 명령어 정리](github실습/Git명령어정리.md), [MD 문법 사용 예시 모음](github실습/MarkDownTest.md), [기준선 작성](프로그램방법론/기준선작성.md) |
| 2026-07-24 | [AI와 함께 찾은 나의 강점](Claude실습/나의강점.md) |
| 2026-07-26 | [AI 리터러시 & LLM 애플리케이션 입문](LLM과AI_Agent이해/LLM_APP입문.md), [프로젝트를 바라보는 방법](프로그램방법론/프로젝트를바라보는방법.md), [기준선 작성 참고](프로그램방법론/기준선작성참고.md), [프로젝트 도구](프로그램방법론/프로젝트도구.md) |
| 2026-07-27 | [n8n](LLM과AI_Agent이해/n8n.md), [프롬프트 엔지니어링](LLM과AI_Agent이해/프롬프트엔지니어링.md), [구글 폼 3개 입력받으면 이메일 보내기](n8n실습/구글폼3개입력받으면이메일보내기.md) |
| 2026-07-28 | [Claude 기본](Claude실습/claude기본.md), [커밋 잘 쓰는 법](github실습/commit잘쓰는법.md), [게임만들기 — Maze Relay](Claude실습/게임만들기/README.md) |
| 2026-07-29 | [API 실습 — 간단 사주 보기](Claude실습/api실습/사주프로그램/사주보기.md), [API 기초](CS지식/API기초.md) |
| 2026-07-30 | [내 자동화 봇 소개](n8n실습/내자동화봇소개.md), [AI Agent란 — 서비스 구조와 실행 환경](CS지식/AIAgent구조.md) |
| 2026-07-31 | [URL 구조](CS지식/URL구조.md), [HTTP 기초](CS지식/HTTP기초.md), [HTTP 상태 코드](CS지식/HTTP상태코드.md) |

## 목차

### Claude실습
- [Claude 기본](Claude실습/claude기본.md) — Chat / Cowork / Code 비교
- [AI와 함께 찾은 나의 강점](Claude실습/나의강점.md) — AI와의 대화로 정리한 나의 강점 3가지
- [게임만들기 — Maze Relay](Claude실습/게임만들기/README.md) — 도트 던전 미로 탈출 게임. 플레이어끼리 Supabase로 메시지를 릴레이하며 죽일지 살릴지 판정하는 비동기 멀티플레이 구조 (원본: [maze-relay](https://github.com/jjh7757/maze-relay))
- [API 실습 — 간단 사주 보기](Claude실습/api실습/사주프로그램/사주보기.md) — 브라우저에서 Gemini API를 직접 호출해 사주를 해석해주는 프론트엔드 실습

### LLM과 AI Agent 이해
- [AI 리터러시 & LLM 애플리케이션 입문](LLM과AI_Agent이해/LLM_APP입문.md)
- [프롬프트 엔지니어링](LLM과AI_Agent이해/프롬프트엔지니어링.md) — 좋은 프롬프트 4요소, 하네스/컨텍스트 엔지니어링, CoT·ReAct·Tree-of-Thought
- [n8n](LLM과AI_Agent이해/n8n.md) — 노코드 자동화 툴 소개

### Github 실습
- [Git 명령어 정리](github실습/Git명령어정리.md) — Git 기본 사용 흐름
- [커밋 잘 쓰는 법](github실습/commit잘쓰는법.md)
- [MD 문법 사용 예시 모음](github실습/MarkDownTest.md)

### n8n 실습
- [구글 폼 3개 입력받으면 이메일 보내기](n8n실습/구글폼3개입력받으면이메일보내기.md)
- [내 자동화 봇 소개](n8n실습/내자동화봇소개.md) — 사주·날씨 기반 오늘의 운세 디스코드 봇

### 프로그램 방법론
- [프로젝트를 바라보는 방법](프로그램방법론/프로젝트를바라보는방법.md) — 프로젝트/프로덕트/운영 구분, WBS, 마일스톤
- [기준선 작성](프로그램방법론/기준선작성.md)
- [기준선 작성 참고](프로그램방법론/기준선작성참고.md) — 도메인 요소, 사용자 역할, 업무 흐름
- [프로젝트 도구](프로그램방법론/프로젝트도구.md) — Obsidian, Notion, Jira, GitHub 역할 구분

### CS지식
- [URL 구조](CS지식/URL구조.md) — scheme/authority/path/query/fragment 등 URL 구성 요소 정리
- [HTTP 기초](CS지식/HTTP기초.md) — 요청/응답 구조, 메서드, 상태 코드, 무상태 특징 정리
- [HTTP 상태 코드](CS지식/HTTP상태코드.md) — 1XX~5XX 분류와 리다이렉션 개념 정리
- [API 기초](CS지식/API기초.md) — API 개념, REST API, API 키/인증 정리
- [AI Agent란 — 서비스 구조와 실행 환경](CS지식/AIAgent구조.md) — Client/Agent/Server/DB/Cloud 구조와 클라우드가 필요한 이유
