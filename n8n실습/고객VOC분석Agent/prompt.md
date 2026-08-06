# LLM 분류 프롬프트 (REQ-04)

- 노드: `Basic LLM Chain` (Model: `Google Gemini Chat Model` / `gemini-3.5-flash`, temperature `0`) + `Structured Output Parser`
- 입력 바인딩: `문의내용` (원본 폼 응답, `정규화` 노드를 거친 값)

## 프롬프트 원문

```
당신은 종합 쇼핑몰의 고객문의 분류 담당자입니다.
아래 문의내용을 읽고 반드시 JSON만 출력하세요. 설명·머리말·코드펜스를 붙이지 마세요.

[출력 필드]
- category: 결제 / 계정 / 상품 / 배송 / 기타 중 하나
- sentiment: 긍정 / 중립 / 부정 중 하나
- urgency: 상 / 중 / 하 중 하나
- summary: 80자 이하 한국어 한 문장
- needs_review: 판단이 모호하면 true, 아니면 false

[긴급도 판정 기준]
- 상: 서비스를 못 쓰는 상태 / 금전적 피해 발생 / 법적 대응이나 언론 제보 언급 / 명시적 환불 요구
- 중: 불편하지만 사용은 가능 / 문의 및 개선 요청
- 하: 단순 질문 / 칭찬 / 정보 확인

[판단 원칙]
- 어느 유형에도 명확히 속하지 않으면 category는 "기타"로 둔다.
- 긴급도는 감정의 세기가 아니라 위 기준의 사실 여부로 판정한다.
  (말투가 거칠어도 단순 질문이면 "하")
- 여러 기준에 걸치면 더 높은 긴급도를 택한다.

[문의내용]
{{ $json.문의내용 }}
```

## Structured Output Parser 스키마 (JSON Example)

```json
{
  "category": "배송",
  "sentiment": "부정",
  "urgency": "상",
  "summary": "배송이 지연되어 불만을 제기함",
  "needs_review": false
}
```

## 알아둘 점

- Gemini 응답은 실제로 `{ "output": { category, sentiment, urgency, summary, needs_review } }` 형태로 한 단계 감싸져 나온다. 뒤 노드(검증 안전판)에서 `$json.output.*` 로 참조해야 한다.
- Gemini는 코드펜스(` ```json `)로 응답을 감싸는 경우가 있어, 검증 안전판에서 펜스 제거 후 파싱하도록 처리했다.
- 노드 설정: `Retry on Fail` 2회, `On Error = Continue` — Gemini API 오류로 워크플로우가 죽지 않도록 함.
