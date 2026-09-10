# LangGraph 가드레일 — Input/Output Guardrail과 프롬프트 인젝션 방어

## 왜 챗봇보다 Agent에 더 강한 통제가 필요한가

일반 챗봇은 잘못된 답변을 생성하는 데서 그치지만, Agent는 API 호출·데이터 변경·이메일 발송처럼 **외부 시스템에 실제 영향을 주는 행동**을 수행한다. 그래서 Guardrail(가드레일)은 "시스템 프롬프트에 금지 사항을 적는 것" 이상이어야 한다 — 입력 검사, 정책/권한 검증, Tool 실행 통제, 출력 검사, 실행 횟수·시간 제한과 승인 절차를 여러 계층으로 쌓는 게 정석이다. **중요한 규칙은 LLM의 판단에만 맡기지 않고 애플리케이션 코드와 실행 환경에서 강제해야 한다**는 게 핵심 원칙이다.

```text
User → Input Guardrail → Agent/LLM → Tool Guardrail → Tools/API
                                      ↓
                              Output Guardrail → User
```

| 계층 | 역할 |
|---|---|
| Input Guardrail | 빈 입력, 길이 제한, 유해 요청과 프롬프트 인젝션 검사 |
| Policy / Tool Guardrail | 권한, Tool 이름과 인자, 업무 규칙 및 승인 여부 검사 |
| Output Guardrail | 민감정보, 금지 콘텐츠와 응답 형식 검사 |
| Runtime Guardrail | 호출 횟수, 시간, 비용 제한과 감사 기록 |

이번 실습은 이 중 **Input Guardrail과 Output Guardrail**만 LangGraph로 직접 구현했다.

## Input Guardrail

```
START → check_input → 안전? → handle_query → END
                       유해? → reject → END
```

빈 입력·최대 길이처럼 **규칙으로 확정 가능한 것**은 먼저 걸러내고, 안전성·프롬프트 인젝션처럼 맥락 판단이 필요한 것은 하나의 LLM 호출로 함께 판단한다. 유해 감지 노드를 그래프 최상단에 두면 감지 즉시 이후 노드를 아예 실행하지 않고 거부 응답으로 분기할 수 있다 — "일단 실행해보고 나중에 걸러내기"가 아니라 "위험하면 아예 진입을 막기".

**프롬프트 인젝션 방어는 한 겹으로 끝나지 않는다**:
- 다층 방어: 키워드 필터 + LLM 판단을 함께 쓴다
- 메시지 역할 분리(사용자 입력 vs 시스템 지시)는 기본 조치일 뿐, 방어를 보장하지는 않는다
- LLM 기반 감지는 새로운 공격 패턴에도 어느 정도 대응 가능
- 최소 권한: 허용된 작업·Tool 권한을 제한해서 감지가 실패해도 피해 범위를 줄인다
- 장애 처리: 검사 모델 오류·타임아웃 시 재시도 횟수와 차단 정책을 미리 정해둔다
- **완벽한 방어는 불가능하다** — 그래서 입력 검증·권한 통제·Output Guardrail을 함께 쓴다

## Output Guardrail

```
START → generate → validate_output → 안전? → pass_through → END
                                      민감정보? → sanitize → END
```

최종 응답을 사용자에게 돌려주기 전에 개인정보·API 키 같은 민감정보 노출을 검사한다. 실습에서는 정규식으로 직접 PII를 감지했는데, 이 방식은 구분자 없는 형식이나 국가별 형식, 난독화된 값까지 다 잡지는 못한다 — 실무에서는 `presidio`(Microsoft) 같은 전용 PII 탐지 라이브러리를 쓰거나 LLM에게 판단을 맡기는 방법도 쓴다.

**마스킹보다 재생성이 더 자연스러울 때가 많다.** "[전화번호 마스킹]" 같은 응답은 어색하므로, 민감정보가 감지되면 마스킹 대신 처음부터 다시 생성하는 루프를 만드는 게 낫다.

```
generate → validate → 민감정보 있음? → generate (다시 생성)
                      안전? → END
```

이런 재생성 루프에는 **반드시 `retry_count`를 두고 최대 횟수에 도달하면 안전한 고정 응답으로 종료**해야 한다 — 그렇지 않으면 검증에 계속 걸리는 응답이 무한 루프를 만들 수 있다. 같은 구조를 할루시네이션 필터링, 응답 포맷 검증, 톤/스타일 검증에도 그대로 적용할 수 있다.

## input_schema / output_schema로 내부 State 숨기기

Output Guardrail 그래프를 그냥 `invoke`하면 `raw_response`, `has_sensitive_info`처럼 **내부 처리용 필드까지 결과에 그대로 노출**된다. `StateGraph`에 `input_schema`/`output_schema`를 따로 지정하면 외부에 노출할 형태와 내부 State를 분리할 수 있다.

```python
StateGraph(InternalState, input_schema=InputSchema, output_schema=OutputSchema)
```

| 파라미터 | 역할 | 기본값 |
|----------|------|--------|
| 첫 번째 인자 | 내부 State (노드 간 공유) | 필수 |
| `input_schema` | 그래프에 들어오는 데이터 형태 | State와 동일 |
| `output_schema` | 그래프에서 나가는 데이터 형태 | State와 동일 |

이걸 적용하면 호출하는 쪽은 `query`만 넘기고 `query`(또는 최종 답변)만 돌려받으면 되고, 그래프 내부에서 무슨 필드를 주고받는지는 신경 쓸 필요가 없어진다 — API 설계에서 내부 구현과 외부 계약을 분리하는 것과 같은 원리를 State에도 적용하는 셈이다.
