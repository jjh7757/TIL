"""페이지 안에서 관찰 대상을 찾아내고, 다시 찾아올 수 있는 선택자를 만든다.

경쟁 제품들이 관리자 API 설정값만 보는 것과 달리, 여기서는 렌더링이 끝난 DOM을 직접 읽는다.
후보 탐색은 일부러 느슨하게 한다 — "시간처럼 보이는 것"을 넓게 모아두고,
그것이 진짜 카운트다운인지는 뒤에서 값의 변화로 판정한다.
"""

from __future__ import annotations

from typing import Any

from playwright.async_api import Page

# 각 JS 조각은 반드시 "하나의 화살표 함수"여야 한다. Playwright 는 문자열 전체를
# 함수로 평가하므로, 헬퍼는 함수 본문 안에 넣는다.
_HELPERS = r"""
  function cssPath(el) {
    // 재로드 후에도 같은 요소를 다시 집으려면 프레임워크가 만드는 임의 클래스에
    // 기대면 안 된다. id 우선, 없으면 nth-of-type 체인.
    if (el.id) return '#' + CSS.escape(el.id);
    const parts = [];
    while (el && el.nodeType === 1 && el !== document.documentElement) {
      const parent = el.parentElement;
      if (el.id) { parts.unshift('#' + CSS.escape(el.id)); break; }
      let seg = el.tagName.toLowerCase();
      if (parent) {
        const sameTag = Array.from(parent.children).filter(c => c.tagName === el.tagName);
        if (sameTag.length > 1) seg += ':nth-of-type(' + (sameTag.indexOf(el) + 1) + ')';
      }
      parts.unshift(seg);
      el = parent;
    }
    return parts.join(' > ');
  }

  function visibleText(el) {
    return (el.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function isRendered(el) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return false;
    const s = getComputedStyle(el);
    return s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
  }

  function deepElements(root) {
    // 서드파티 위젯(사회적 증거 팝업, 리뷰 위젯 등)은 스타일 캡슐화를 위해
    // open shadow DOM 으로 렌더링되는 경우가 흔하다 — 오롤리데이의 "N명이
    // 보고 있는 상품" 위젯이 그랬다. querySelectorAll 은 shadow 경계를
    // 넘지 않으므로, shadowRoot 를 만나면 그 안까지 재귀적으로 파고든다.
    // (닫힌 shadow root 는 공개 API로 접근 불가라 이 방식으로도 못 본다.)
    const out = [];
    const stack = [root];
    while (stack.length) {
      const node = stack.pop();
      for (const el of node.querySelectorAll('*')) {
        out.push(el);
        if (el.shadowRoot) stack.push(el.shadowRoot);
      }
    }
    return out;
  }

  function innermostMatches(matchFn, maxLen) {
    // 패턴에 걸리는 요소 중 "가장 안쪽" 것만 남긴다.
    // 그러지 않으면 body 부터 모든 조상이 전부 후보로 잡힌다.
    const hits = [];
    for (const el of deepElements(document.body)) {
      const tag = el.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT' || tag === 'TEMPLATE') continue;
      const text = visibleText(el);
      if (!text || text.length > maxLen) continue;
      if (matchFn(text)) hits.push(el);
    }
    return hits.filter(el => !hits.some(other => other !== el && el.contains(other)));
  }
"""

# 시간처럼 보이는 텍스트. 콜론 표기(00:22:45)는 그 자체로 신호가 강해 바로 인정한다.
# 하지만 "일/시간/분/초" 단위 표기만으로는 "단 7일간 만나는 혜택" 같은 마케팅 문구도
# 걸려버린다 — 실제 무신사에서 회전 배너의 이런 문구가 타이머로 오인된 적이 있다.
# 그래서 단위 표기 단독으로는 부족하고, 같은 요소 안에 마감·종료·남음류 긴급성
# 문구가 함께 있어야만 후보로 인정한다.
_CLOCK_RE_JS = r"/\d{1,3}\s*[:：]\s*\d{1,2}/"
_BARE_UNIT_RE_JS = (
    r"/\d+\s*(?:일|시간|분|초)"
    r"|\d+\s*(?:days?|hours?|hrs?|minutes?|mins?|seconds?|secs?|[dhms])(?![a-z])/i"
)
_URGENCY_RE_JS = r"/마감|종료|남음|남았|remaining|\bleft\b|ends?\s*in|expires?/i"

_TIMER_MATCH_FN_JS = f"""
  function looksLikeTimer(text) {{
    const clock = {_CLOCK_RE_JS};
    const bareUnit = {_BARE_UNIT_RE_JS};
    const urgency = {_URGENCY_RE_JS};
    if (clock.test(text)) return true;
    return bareUnit.test(text) && urgency.test(text);
  }}
"""

# _JS_SNAPSHOT 안에서 "시간처럼 보이는지"만 따로 재사용할 때 쓰는 순수 정규식(콜론+단위 통합).
# claims 에서 타이머 문구를 걸러내는 용도이므로, 후보 판정보다 살짝 넓게 잡아도 된다.
_TIME_RE_JS = (
    r"/\d{1,3}\s*[:：]\s*\d{1,2}"
    r"|\d+\s*(?:일|시간|분|초)"
    r"|\d+\s*(?:days?|hours?|hrs?|minutes?|mins?|seconds?|secs?|[dhms])(?![a-z])/i"
)

# 재고·조회수 등 수량 주장. 숫자가 세션마다 달라지면 실제 값이 아니다.
_CLAIM_RE_JS = (
    r"/\d+\s*(?:개|명|장|점|박스)?\s*(?:남았|남음|남아|밖에)"
    r"|재고\s*\d+"
    r"|\d+\s*명[^.\n]{0,24}?(?:보고|구매|담았|담고|열람)"
    r"|only\s*\d+\s*(?:items?\s*)?left"
    r"|\d+\s*(?:people|others|shoppers)[^.\n]{0,24}?(?:viewing|watching|bought|purchased)/i"
)

_JS_SNAPSHOT = (
    "() => {\n"
    + _HELPERS
    + _TIMER_MATCH_FN_JS
    + f"""
  const timers = innermostMatches(looksLikeTimer, 80).filter(isRendered).map(el => ({{
    selector: cssPath(el),
    text: visibleText(el),
    context: visibleText(el.parentElement || el).slice(0, 140),
  }}));

  // "00:09:58 남음" 같은 타이머 문구가 재고 주장으로 새어 들어오지 않게 시간 표기를 걸러낸다.
  const timeRe = {_TIME_RE_JS};
  const claimRe = {_CLAIM_RE_JS};
  const claims = innermostMatches(text => claimRe.test(text), 120)
    .filter(isRendered)
    .filter(el => !timeRe.test(visibleText(el)))
    .map(el => ({{
      selector: cssPath(el),
      text: visibleText(el),
    }}));

  return {{ timers, claims, url: location.href, title: document.title }};
}}
"""
)

_JS_READ_SELECTORS = (
    "(selectors) => {\n"
    + _HELPERS
    + r"""
  const out = {};
  for (const sel of selectors) {
    let el = null;
    try { el = document.querySelector(sel); } catch (e) { el = null; }
    out[sel] = el ? visibleText(el) : null;
  }
  return out;
}
"""
)

# 사전 선택된 유료 옵션. 법정 6유형 중 "특정 옵션 사전 선택"에 직접 대응한다.
_JS_PRESELECTED = (
    "() => {\n"
    + _HELPERS
    + r"""
  const results = [];
  const nodes = document.querySelectorAll(
    'input[type=checkbox], input[type=radio], select option'
  );
  for (const el of nodes) {
    const on = el.tagName === 'OPTION' ? el.selected : el.checked;
    if (!on) continue;
    if (el.tagName === 'OPTION' && el.parentElement && el.parentElement.selectedIndex === 0) {
      continue;  // select 의 첫 항목이 선택된 것은 브라우저 기본값이라 의미가 없다.
    }
    let label = '';
    if (el.id) {
      const l = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (l) label = visibleText(l);
    }
    if (!label) {
      const wrap = el.closest('label, li, tr, .row, div');
      if (wrap) label = visibleText(wrap).slice(0, 160);
    }
    results.push({
      selector: cssPath(el),
      kind: el.tagName === 'OPTION' ? 'option' : el.type,
      label: label,
      required: el.required === true,
    });
  }
  return results;
}
"""
)

_JS_PAGE_TEXT = "() => document.body ? document.body.innerText : ''"

# CSS 선택자 또는 "text=문구" 로 요소를 찾아 DOM에 직접 클릭 이벤트를 보낸다.
# Playwright 의 click() 은 요소가 실제로 화면에 "보인다"는 여러 조건을 검사하는데,
# 반응형 레이아웃/지연 렌더링 때문에 실사용자에겐 멀쩡히 보이는 버튼도 그 기준에
# 걸려 타임아웃나는 실제 사례가 있었다. 이 헬퍼는 그 검사를 건너뛴다.
_JS_CLICK = r"""
(target) => {
  let el = null;
  if (target.startsWith('text=')) {
    const wanted = target.slice(5).trim();
    el = [...document.querySelectorAll('a, button, [role=button]')]
      .find(e => e.textContent.trim() === wanted);
  } else {
    el = document.querySelector(target);
  }
  if (!el) throw new Error('js_click: 요소를 찾지 못했습니다 — ' + target);
  el.click();
}
"""


async def js_click(page: Page, target: str) -> None:
    """CSS 선택자 또는 'text=문구'로 찾은 요소에 DOM 클릭을 직접 디스패치한다."""
    await page.evaluate(_JS_CLICK, target)


async def snapshot(page: Page) -> dict[str, Any]:
    """지금 화면에 보이는 타이머 후보와 수량 주장을 모두 걷어온다."""
    return await page.evaluate(_JS_SNAPSHOT)


async def read_selectors(page: Page, selectors: list[str]) -> dict[str, str | None]:
    """앞서 찾아둔 선택자들의 현재 텍스트만 다시 읽는다."""
    if not selectors:
        return {}
    return await page.evaluate(_JS_READ_SELECTORS, selectors)


async def preselected_options(page: Page) -> list[dict[str, Any]]:
    """기본으로 켜져 있는 체크박스·라디오·옵션을 모은다."""
    return await page.evaluate(_JS_PRESELECTED)


async def page_text(page: Page) -> str:
    return await page.evaluate(_JS_PAGE_TEXT)
