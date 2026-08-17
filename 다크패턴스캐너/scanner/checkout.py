"""결제 흐름을 실제로 따라가며 단계별 총액을 기록한다.

숨은 비용(순차공개 가격책정)은 설정값 어디에도 적혀 있지 않다.
상품 페이지에서 본 금액과 마지막 결제 버튼 앞의 금액이 다른지는
그 사이를 직접 걸어가 봐야만 알 수 있다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Browser, Page

from . import dom, money
from .money import Amount

# goto 직후 select/click 을 보내기 전에 최소로 기다리는 시간.
SETTLE_AFTER_GOTO_MS = 1200


@dataclass
class Step:
    """흐름의 한 단계. goto 로 시작하고 이후는 select/click 으로 넘어간다.

    실제 쇼핑몰은 "옵션(색상 등)을 고르지 않으면 장바구니 버튼이 막히는" 경우가
    흔하다 (예: 카페24 기반 스토어의 <select id=product_option_id1>). 그래서
    한 단계 안에서 select 를 먼저 적용한 뒤 click 으로 넘어갈 수 있게 한다.
    """

    name: str
    goto: str | None = None
    select: dict[str, str] | None = None  # {선택자: 값}, goto/click 사이에 적용
    click: str | None = None
    # Playwright 의 click 은 요소가 실제로 눈에 보여야 클릭한다. 그런데 실제
    # 사이트에는 CSS 로 접어두거나(display:none 아님, 높이 0) 레이아웃 계산이
    # 늦어 이 기준을 통과 못 하는 "실사용자에겐 보이는" 버튼이 있다
    # (오롤리데이 장바구니의 "전체상품주문" 버튼이 그랬다). 이런 단계는
    # js_click 으로 DOM에 직접 클릭 이벤트를 보낸다.
    js_click: str | None = None
    wait_ms: int = 1200

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Step":
        return Step(
            name=d["name"],
            goto=d.get("goto"),
            select=d.get("select"),
            click=d.get("click"),
            js_click=d.get("js_click"),
            wait_ms=int(d.get("wait_ms", 1200)),
        )


@dataclass
class StepResult:
    name: str
    url: str
    total: Amount | None
    total_basis: str
    line_items: list[money.LineItem]
    preselected: list[dict[str, Any]]
    error: str | None = None


@dataclass
class HiddenFee:
    label: str
    amount: Amount
    first_seen_step: str
    reason: str


@dataclass
class CheckoutReport:
    steps: list[StepResult]
    advertised: Amount | None
    final: Amount | None
    increase: float
    increase_pct: float
    jump_step: str | None
    hidden_fees: list[HiddenFee]
    preselected_paid: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def is_dark_pattern(self) -> bool:
        return self.increase > 0 and self.jump_step is not None


async def scan(browser: Browser, steps: list[Step]) -> CheckoutReport:
    if not steps or not steps[0].goto:
        raise ValueError("첫 단계에는 goto(시작 URL)가 있어야 합니다.")

    ctx = await browser.new_context()
    page = await ctx.new_page()
    results: list[StepResult] = []
    notes: list[str] = []

    try:
        for step in steps:
            error = None
            try:
                if step.goto:
                    await page.goto(step.goto, wait_until="domcontentloaded")
                    # DOMContentLoaded 는 HTML 파싱이 끝났다는 뜻일 뿐, 옵션 선택지를
                    # 채우거나 장바구니 버튼에 핸들러를 붙이는 페이지 자체 스크립트는
                    # 그 뒤에도 한동안 계속 실행된다. 이 틈에 select/click 을 곧바로
                    # 보내면 서버에는 요청이 가도 페이지 상태가 준비되기 전이라
                    # 조용히 무시되는 경우가 실제로 있었다(카페24 스토어 2곳에서 확인).
                    await page.wait_for_timeout(min(step.wait_ms, SETTLE_AFTER_GOTO_MS))
                if step.select:
                    for selector, value in step.select.items():
                        await page.select_option(selector, value)
                    # select_option 은 DOM 값이 바뀌고 change 이벤트가 나갔다는 것만
                    # 보장한다. 그 이벤트를 받아 "선택된 옵션" 내부 상태를 갱신하는
                    # 페이지 스크립트가 끝났다는 보장은 아니다. 이 틈에 곧바로
                    # 장바구니 버튼을 누르면 서버가 200 을 반환하고도 실제로는
                    # 담기지 않는 경우를 실제 카페24 스토어에서 반복 확인했다.
                    await page.wait_for_timeout(500)
                if step.click:
                    # 새 페이지로 넘어가지 않고 같은 화면에 장바구니 서랍만 여는
                    # 클릭도 흔하다. wait_for_load_state 는 그런 경우 이미 도달한
                    # 상태이므로 즉시 반환되어 별문제 없다.
                    await page.click(step.click)
                    await page.wait_for_load_state("domcontentloaded")
                elif step.js_click:
                    await dom.js_click(page, step.js_click)
                    await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(step.wait_ms)
            except Exception as exc:  # 단계 하나가 막혀도 거기까지의 관찰은 살린다.
                error = f"{type(exc).__name__}: {exc}"
                notes.append(f"'{step.name}' 단계에서 멈췄습니다 — {error}")
                results.append(
                    StepResult(step.name, page.url, None, "", [], [], error=error)
                )
                break

            results.append(await _observe(page, step.name))
    finally:
        await ctx.close()

    return _analyse(results, notes)


async def _observe(page: Page, name: str) -> StepResult:
    text = await dom.page_text(page)
    total, basis = money.page_total(text)
    return StepResult(
        name=name,
        url=page.url,
        total=total,
        total_basis=basis,
        line_items=money.line_items(text),
        preselected=await dom.preselected_options(page),
    )


def _analyse(results: list[StepResult], notes: list[str]) -> CheckoutReport:
    priced = [r for r in results if r.total is not None]
    if len(priced) < 2:
        notes.append("총액을 읽어낸 단계가 2개 미만이라 비교할 수 없습니다.")
        return CheckoutReport(
            steps=results, advertised=None, final=None, increase=0.0,
            increase_pct=0.0, jump_step=None, hidden_fees=[], notes=notes,
        )

    advertised = priced[0].total
    final = priced[-1].total
    assert advertised and final

    if advertised.currency != final.currency:
        notes.append("단계별 통화 단위가 달라 비교를 건너뜁니다.")
        return CheckoutReport(
            steps=results, advertised=advertised, final=final, increase=0.0,
            increase_pct=0.0, jump_step=None, hidden_fees=[], notes=notes,
        )

    increase = final.value - advertised.value
    increase_pct = (increase / advertised.value * 100) if advertised.value else 0.0

    # 총액이 처음으로 뛴 단계를 찾는다. 셀러에게는 "어디를 고쳐야 하는지"가 곧 답이다.
    jump_step = None
    prev = advertised.value
    for r in priced[1:]:
        assert r.total
        if r.total.value > prev + 0.5:
            jump_step = r.name
            break
        prev = r.total.value

    hidden_fees = _new_charges(priced) if jump_step else []
    preselected_paid = _paid_preselections(priced[-1])

    return CheckoutReport(
        steps=results,
        advertised=advertised,
        final=final,
        increase=increase,
        increase_pct=increase_pct,
        jump_step=jump_step,
        hidden_fees=hidden_fees,
        preselected_paid=preselected_paid,
        notes=notes,
    )


def _new_charges(priced: list[StepResult]) -> list[HiddenFee]:
    """뒤늦게 등장하거나, 앞서 0원/무료였다가 값이 붙는 유료 항목.

    두 가지를 구분해서 잡는다:
      1. 앞 단계에 아예 없던 항목명이 새로 등장 (예: '결제 수수료')
      2. 같은 항목명이 이미 있었지만 금액이 올라감 (예: '배송비' 0원 → 3,000원 —
         '무료배송'이라 해놓고 결제 단계에서 청구하는 전형적인 수법)
    """
    last_amount: dict[str, float] = {}
    for it in priced[0].line_items:
        amt = it.max_amount
        if amt is not None:
            last_amount[_key(it)] = amt.value
    # 첫 화면의 금액들은, 줄 구조가 달라 라벨이 안 맞더라도 '새 비용'으로 보지 않는다.
    # (상품 페이지의 제목과 가격은 별개 줄이라 라벨만으로는 장바구니의 상품 행과 이어지지 않는다.)
    seen_values = {(a.currency, a.value) for it in priced[0].line_items for a in it.amounts}

    fees: list[HiddenFee] = []
    for step in priced[1:]:
        for it in step.line_items:
            amount = it.max_amount
            if not amount or amount.value <= 0 or not it.label:
                continue
            if money.TOTAL_LABEL.search(it.label) or money.STRIKE_LABEL.search(it.label):
                continue

            key = _key(it)
            if key in last_amount:
                prev = last_amount[key]
                if amount.value > prev + 0.5:
                    fees.append(
                        HiddenFee(
                            label=it.label, amount=amount, first_seen_step=step.name,
                            reason=f"이전에는 {_fmt(prev, amount.currency)}이던 항목이 올랐습니다",
                        )
                    )
                last_amount[key] = amount.value
                continue

            last_amount[key] = amount.value
            if (amount.currency, amount.value) in seen_values:
                continue
            seen_values.add((amount.currency, amount.value))
            fees.append(
                HiddenFee(
                    label=it.label, amount=amount, first_seen_step=step.name,
                    reason="이전 단계에는 없던 항목입니다",
                )
            )
    return fees


def _fmt(value: float, currency: str) -> str:
    return str(Amount(value, currency, ""))


def _key(item: money.LineItem) -> str:
    return item.label.strip().lower()


def _paid_preselections(step: StepResult) -> list[dict[str, Any]]:
    """기본 선택된 항목 중 라벨에 금액이 붙어 있는 것 — 사전 선택된 유료 옵션."""
    out = []
    for opt in step.preselected:
        amounts = money.parse_amounts(opt.get("label", ""))
        paid = [a for a in amounts if a.value > 0]
        if paid:
            out.append({**opt, "amount": str(max(paid, key=lambda a: a.value))})
    return out
