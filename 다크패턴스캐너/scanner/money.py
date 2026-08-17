"""화면 텍스트에서 금액과 그 금액에 붙은 항목명을 읽는다.

체크아웃 단계마다 "지금 화면이 말하는 총액"을 뽑아내야 단계 간 비교가 가능하다.
DOM 구조는 쇼핑몰마다 다르므로 innerText 의 줄 단위로 읽는다 —
표의 한 행은 innerText 에서도 한 줄로 나오기 때문에 항목명과 금액이 같은 줄에 남는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_KRW = re.compile(r"₩\s*([\d,]+)|([\d,]+)\s*원")
_USD = re.compile(r"\$\s*([\d,]+(?:\.\d{1,2})?)")

# "이 줄의 금액이 그 화면의 총액"이라고 볼 수 있는 항목명들.
TOTAL_LABEL = re.compile(
    r"총\s*결제|최종\s*결제|결제\s*(?:예정\s*)?금액|주문\s*금액|합계|총액|총\s*금액"
    r"|order\s*total|grand\s*total|amount\s*due|\btotal\b",
    re.IGNORECASE,
)

# 총액이 아니라 "원래 가격"을 뜻하는 줄. 정가·할인 전 금액을 총액/신규비용으로 오인하지 않기 위함.
STRIKE_LABEL = re.compile(r"정가|소비자가|할인\s*전|정상가|was\b|list\s*price", re.IGNORECASE)

# 총액 표기가 없어 "화면 최대 금액"으로 갈음할 때, 몇 번째 가격 줄까지만 후보로 볼지.
# 실제 상품 상세 페이지에는 "함께 사면 좋은 상품" 추천 위젯이 뒤에 잔뜩 붙어 있고
# 그중 하나가 본 상품보다 비싸면 그게 "광고가"로 잘못 뽑힌다(실제 오롤리데이에서 확인:
# 15,200원짜리 상품인데 추천 위젯의 26,000원짜리를 광고가로 오인). 본 상품 가격은
# 페이지 앞부분에 있다고 보고 탐색 범위를 제한한다.
EARLY_CANDIDATE_WINDOW = 20


@dataclass
class Amount:
    value: float
    currency: str
    raw: str

    def __str__(self) -> str:
        if self.currency == "KRW":
            return f"{int(self.value):,}원"
        return f"${self.value:,.2f}"


@dataclass
class LineItem:
    label: str
    amounts: list[Amount]
    raw: str

    @property
    def max_amount(self) -> Amount | None:
        return max(self.amounts, key=lambda a: a.value) if self.amounts else None


def parse_amounts(text: str) -> list[Amount]:
    found: list[tuple[int, Amount]] = []
    for m in _KRW.finditer(text):
        digits = m.group(1) or m.group(2)
        value = _to_float(digits)
        if value is not None:
            found.append((m.start(), Amount(value, "KRW", m.group(0).strip())))
    for m in _USD.finditer(text):
        value = _to_float(m.group(1))
        if value is not None:
            found.append((m.start(), Amount(value, "USD", m.group(0).strip())))
    found.sort(key=lambda p: p[0])
    return [a for _, a in found]


def line_items(page_text: str) -> list[LineItem]:
    items: list[LineItem] = []
    seen_raw: set[str] = set()
    for raw_line in page_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        amounts = parse_amounts(line)
        if not amounts:
            continue
        # 마퀴/티커 배너는 무한 스크롤 효과를 위해 같은 문구를 DOM에 여러 번 반복해
        # 넣는 경우가 흔하다(실제 오롤리데이 홈에서 확인). 그대로 두면 이 반복이
        # "화면 앞부분"을 다 차지해 뒤에 나오는 진짜 가격 정보를 밀어낸다.
        if line in seen_raw:
            continue
        seen_raw.add(line)
        # 금액 표기를 지운 나머지를 항목명으로 본다.
        label = line
        for a in amounts:
            label = label.replace(a.raw, " ")
        label = re.sub(r"\s+", " ", label).strip(" \t:·-")
        items.append(LineItem(label=label, amounts=amounts, raw=line))
    return items


def page_total(page_text: str) -> tuple[Amount | None, str]:
    """화면이 주장하는 총액과, 그것을 어떻게 골랐는지의 근거를 함께 돌려준다."""
    items = line_items(page_text)
    if not items:
        return None, "금액을 찾지 못함"

    labeled = [
        it for it in items
        if TOTAL_LABEL.search(it.label) and not STRIKE_LABEL.search(it.label)
    ]
    if labeled:
        # 총액 줄이 여러 개면 마지막 것이 최종 결제액인 경우가 많다.
        chosen = labeled[-1]
        amount = chosen.max_amount
        if amount:
            return amount, f"'{chosen.label}' 줄에서 읽음"

    # 총액 표기가 없으면 화면 최대 금액으로 갈음하되, 할인 전 정가는 후보에서 뺀다.
    # 뒤쪽 추천 위젯의 다른 상품 가격까지 후보로 삼지 않도록 앞부분으로 범위를 좁힌다.
    candidates = [
        it for it in items[:EARLY_CANDIDATE_WINDOW]
        if it.max_amount and not STRIKE_LABEL.search(it.label)
    ]
    biggest = max(candidates, key=lambda it: it.max_amount.value, default=None)
    if biggest and biggest.max_amount:
        where = f"'{biggest.label}' 줄" if biggest.label else "라벨 없는 줄"
        return biggest.max_amount, f"총액 표기가 없어 화면 최대 금액({where})을 사용"
    return None, "금액을 찾지 못함"


def _to_float(digits: str) -> float | None:
    try:
        return float(digits.replace(",", ""))
    except ValueError:
        return None
