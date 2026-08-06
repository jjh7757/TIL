/**
 * REQ-05 :: 검증 안전판
 * 노드: Code ("Code in JavaScript")
 * 위치: Basic LLM Chain 바로 다음
 * Mode: Run Once for Each Item
 *
 * LLM 출력이 계약(허용값 / 타입 / 길이)을 어겨도 워크플로우가 죽지 않도록,
 * 위반 시 urgency=중(안전 기본값), needs_review=true 로 강제하고
 * 검증 실패건도 그대로 다음 노드(시트 저장)로 흘려보낸다.
 */

const ALLOW = {
  category: ['결제', '계정', '상품', '배송', '기타'],
  sentiment: ['긍정', '중립', '부정'],
  urgency: ['상', '중', '하'],
};

let raw = $json.output ?? '';
let parsed = {};
let violated = false;

try {
  if (typeof raw === 'object' && raw !== null) parsed = raw;
  else parsed = JSON.parse(String(raw).replace(/```(json)?/g, '').trim());
} catch (e) {
  violated = true;
}

const pick = (key, fallback) => {
  const v = typeof parsed[key] === 'string' ? parsed[key].trim() : parsed[key];
  if (!ALLOW[key].includes(v)) { violated = true; return fallback; }
  return v;
};

const result = {
  category:  pick('category', '기타'),
  sentiment: pick('sentiment', '중립'),
  urgency:   pick('urgency', '중'),
  summary:   String(parsed.summary ?? '').slice(0, 80),
  needs_review: parsed.needs_review === true,
};

if (typeof parsed.summary !== 'string' || parsed.summary.length > 80) violated = true;
if (typeof parsed.needs_review !== 'boolean') violated = true;

if (violated) { result.urgency = '중'; result.needs_review = true; }

return { json: { ...$json, ...result } };
