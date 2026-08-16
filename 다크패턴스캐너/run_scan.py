"""다크패턴 스캐너 CLI.

  python run_scan.py demo                 # fixture 로 탐지기 자체를 검증 (정답 대조)
  python run_scan.py timer <url>          # 카운트다운·재고 표시 검사
  python run_scan.py checkout <flow.json> # 결제 흐름을 따라가며 총액 추적

flow.json 예시:
  [{"name": "상품", "goto": "https://.../item"},
   {"name": "장바구니", "click": "#to-cart"},
   {"name": "결제", "click": "#to-checkout"}]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright

from scanner import checkout, countdown, report
from scanner.serve import serve

FIXTURES = Path(__file__).parent / "fixtures"


async def cmd_timer(url: str, headed: bool) -> int:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not headed)
        try:
            result = await countdown.scan(browser, url)
        finally:
            await browser.close()
    print(report.render(f"카운트다운 검사 — {url}", report.from_countdown(result)))
    return 0


async def cmd_checkout(flow_path: str, headed: bool) -> int:
    steps = [checkout.Step.from_dict(d) for d in json.loads(Path(flow_path).read_text("utf-8"))]
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not headed)
        try:
            result = await checkout.scan(browser, steps)
        finally:
            await browser.close()
    print(report.render(f"결제 흐름 검사 — {steps[0].goto}", report.from_checkout(result)))
    return 0


async def cmd_demo(headed: bool = False) -> int:
    """fixture 는 정답을 알고 있다. 탐지기가 그 정답을 맞히는지 확인한다."""
    checks: list[tuple[str, bool, str]] = []

    with serve(FIXTURES) as base:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=not headed)
            try:
                # --- 1. 카운트다운 --------------------------------------
                expected = {
                    "fake_urgency.html": ("fake_session", "새로고침마다 초기화되는 가짜 타이머"),
                    "cookie_urgency.html": ("fake_storage", "쿠키 기반 방문자별 가짜 타이머"),
                    "real_deadline.html": ("genuine", "실제 마감 시각 기반 정상 타이머"),
                }
                for filename, (want, label) in expected.items():
                    url = f"{base}/{filename}"
                    result = await countdown.scan(browser, url)
                    print(report.render(f"{label} — {filename}", report.from_countdown(result)))
                    print()

                    got = [t.verdict for t in result.timers]
                    checks.append((
                        f"{filename}: 판정 {want}",
                        want in got,
                        f"실제 판정 {got or '(타이머 미발견)'}",
                    ))

                # 가짜 재고는 세션마다 값이 달라져야 잡힌다.
                fake = await countdown.scan(browser, f"{base}/fake_urgency.html")
                checks.append((
                    "fake_urgency.html: 재고·조회수 변동 탐지",
                    any(c.verdict == "volatile" for c in fake.claims),
                    f"claims={[c.verdict for c in fake.claims] or '(없음)'}",
                ))

                # --- 2. 결제 흐름 ---------------------------------------
                dark_flow = [
                    checkout.Step("상품", goto=f"{base}/checkout/step1_product.html"),
                    checkout.Step("장바구니", click="#to-cart"),
                    checkout.Step("결제", click="#to-checkout"),
                ]
                dark = await checkout.scan(browser, dark_flow)
                print(report.render("숨은 비용 흐름 — checkout/step1~3", report.from_checkout(dark)))
                print()
                checks.append((
                    "숨은 비용 흐름: 총액 증가 탐지",
                    dark.is_dark_pattern and round(dark.increase) == 6500,
                    f"increase={dark.increase} jump={dark.jump_step}",
                ))
                checks.append((
                    "숨은 비용 흐름: 사전 선택된 유료 옵션 탐지",
                    len(dark.preselected_paid) >= 1,
                    f"preselected_paid={len(dark.preselected_paid)}",
                ))

                ghost_flow = [
                    checkout.Step("상품", goto=f"{base}/checkout/ghost_step1_product.html"),
                    checkout.Step("장바구니", click="#to-cart"),
                    checkout.Step("결제", click="#to-checkout"),
                ]
                ghost = await checkout.scan(browser, ghost_flow)
                print(report.render("유령 배송비 흐름 — checkout/ghost_step1~3", report.from_checkout(ghost)))
                print()
                checks.append((
                    "유령 배송비: 같은 라벨의 금액 인상 탐지",
                    any("배송비" in f.label for f in ghost.hidden_fees),
                    f"hidden_fees={[(f.label, str(f.amount)) for f in ghost.hidden_fees]}",
                ))

                honest_flow = [
                    checkout.Step("상품", goto=f"{base}/checkout/honest_step1_product.html"),
                    checkout.Step("장바구니", click="#to-cart"),
                    checkout.Step("결제", click="#to-checkout"),
                ]
                honest = await checkout.scan(browser, honest_flow)
                print(report.render("정상 결제 흐름 (대조군)", report.from_checkout(honest)))
                print()
                checks.append((
                    "정상 흐름: 오탐 없음",
                    not honest.is_dark_pattern,
                    f"increase={honest.increase} jump={honest.jump_step}",
                ))
            finally:
                await browser.close()

    print("=" * 78)
    print("정답 대조")
    print("=" * 78)
    failed = 0
    for name, ok, note in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}   ({note})")
        if not ok:
            failed += 1
    print()
    print(f"{len(checks) - failed}/{len(checks)} 통과")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="렌더링 기반 다크패턴 스캐너")
    parser.add_argument("--headed", action="store_true", help="브라우저 창을 띄워 눈으로 확인")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo", help="fixture 로 탐지기 검증")
    t = sub.add_parser("timer", help="카운트다운·재고 표시 검사")
    t.add_argument("url")
    c = sub.add_parser("checkout", help="결제 흐름 총액 추적")
    c.add_argument("flow", help="단계를 적은 JSON 파일 경로")

    args = parser.parse_args()
    if args.cmd == "demo":
        return asyncio.run(cmd_demo(args.headed))
    if args.cmd == "timer":
        return asyncio.run(cmd_timer(args.url, args.headed))
    return asyncio.run(cmd_checkout(args.flow, args.headed))


if __name__ == "__main__":
    sys.exit(main())
