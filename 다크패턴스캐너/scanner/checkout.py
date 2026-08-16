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


@dataclass
class Step:
    """흐름의 한 단계. goto 로 시작하고 이후는 click 으로 넘어간다."""

    name: str
    goto: str | None = None
    click: str | None = None
    wait_ms: int = 1200

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Step":
        return Step(
            name=d["name"],
            goto=d.get("goto"),
            click=d.get("click"),
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
                elif step.click:
                    await page.click(step.click)
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
