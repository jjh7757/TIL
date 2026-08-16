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

  function innermostMatches(re, maxLen) {
    // 패턴에 걸리는 요소 중 "가장 안쪽" 것만 남긴다.
    // 그러지 않으면 body 부터 모든 조상이 전부 후보로 잡힌다.
    const hits = [];
    for (const el of document.querySelectorAll('body *')) {
      const tag = el.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT' || tag === 'TEMPLATE') continue;
      const text = visibleText(el);
      if (!text || text.length > maxLen) continue;
      if (re.test(text)) hits.push(el);
    }
    return hits.filter(el => !hits.some(other => other !== el && el.contains(other)));
  }
"""

# 시간처럼 보이는 텍스트. timeparse.LOOKS_LIKE_TIME 과 같은 뜻을 JS 로 옮긴 것.
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
    + f"""
  const timers = innermostMatches({_TIME_RE_JS}, 80).filter(isRendered).map(el => ({{
    selector: cssPath(el),
    text: visibleText(el),
    context: visibleText(el.parentElement || el).slice(0, 140),
  }}));

  // "00:09:58 남음" 같은 타이머 문구가 재고 주장으로 새어 들어오지 않게 시간 표기를 걸러낸다.
  const timeRe = {_TIME_RE_JS};
  const claims = innermostMatches({_CLAIM_RE_JS}, 120)
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
