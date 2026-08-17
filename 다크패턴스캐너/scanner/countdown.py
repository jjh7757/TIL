"""카운트다운 타이머가 진짜 마감을 가리키는지, 방문자마다 새로 주어지는 연출인지 판정한다.

핵심 아이디어: 진짜 마감은 벽시계 위의 한 점이다. 누가 언제 몇 번을 열든,
남은 시간은 "마감 - 지금"이라는 하나의 값으로 수렴해야 한다.
그래서 같은 페이지를 세 가지 조건으로 열어보고 세 값이 한 직선 위에 있는지 본다.

  A. 새 브라우저 컨텍스트로 첫 방문 → 기준값을 잡고, 몇 초 뒤 다시 읽어 실제로 줄어드는지 확인
  B. 같은 컨텍스트에서 새로고침       → 쿠키·스토리지가 살아 있을 때의 동작
  C. 완전히 새 컨텍스트로 재방문       → 저장소가 비어 있는 "다른 방문자"의 동작

C 가 A 의 처음 값으로 되돌아가면, 그 타이머에는 마감이 존재하지 않는다.
이 판정은 관리자 API 로는 원리적으로 불가능하다 — 설정값이 아니라 시간의 흐름을 봐야 하기 때문이다.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Browser

from . import dom
from .timeparse import format_duration, parse_duration

# 판정 여유. 렌더링 지연과 초 단위 반올림을 흡수한다.
TOLERANCE_S = 2.5
# A 의 첫 관측과 C 의 관측 사이에 이만큼은 흘러야 "되돌아갔다"와 "이어졌다"가 구분된다.
MIN_SPREAD_S = 5.0
# 후보 탐색 시 스냅샷을 몇 번, 얼마 간격으로 찍을지.
# 회전 배너(캐러셀)는 여러 슬라이드가 페이드 인/아웃하며 한 슬라이드씩만 보이므로,
# 단 한 번만 스냅샷을 찍으면 그 순간 숨어 있던 진짜 타이머 슬라이드를 놓친다.
# (실제로 무신사 홈에서 "종료까지 00:22:45 남음" 슬라이드가 한 번의 스냅샷에서는
#  보이지 않아 후보에서 빠진 적이 있다.)
DISCOVERY_ROUNDS = 3
DISCOVERY_INTERVAL_MS = 700


@dataclass
class TimerVerdict:
    selector: str
    context: str
    first_value: int
    verdict: str  # fake_session | fake_storage | genuine | not_counting | inconclusive
    detail: str
    observations: dict[str, Any] = field(default_factory=dict)

    @property
    def is_dark_pattern(self) -> bool:
        return self.verdict in ("fake_session", "fake_storage")


@dataclass
class ClaimVerdict:
    text_by_visit: list[str]
    verdict: str  # volatile | stable
    detail: str


@dataclass
class CountdownReport:
    url: str
    timers: list[TimerVerdict]
    claims: list[ClaimVerdict]
    notes: list[str]


async def scan(
    browser: Browser,
    url: str,
    *,
    settle_ms: int = 1500,
    sample_gap_s: float = 4.0,
) -> CountdownReport:
    notes: list[str] = []

    # ---- A: 첫 방문 ----------------------------------------------------
    ctx_a = await browser.new_context()
    page_a = await ctx_a.new_page()
    await _goto(page_a, url, settle_ms)

    timers, claims_a = await _discover_candidates(page_a)
    selectors = [t["selector"] for t in timers]

    if not timers:
        notes.append("시간처럼 보이는 요소를 찾지 못했습니다. 타이머가 없거나 iframe 안에 있을 수 있습니다.")

    # 여러 스냅샷으로 후보를 찾은 뒤, 모든 후보를 같은 순간에 다시 읽어 기준 시각을 통일한다.
    # (캐러셀 슬라이드마다 발견된 시점이 다르면 경과 시간 계산이 후보별로 어긋난다.)
    read_a0 = await dom.read_selectors(page_a, selectors)
    t_a0 = time.monotonic()
    for t in timers:
        found = read_a0.get(t["selector"])
        if found is not None:
            t["text"] = found

    # 같은 페이지를 그대로 두고 몇 초 뒤 다시 읽는다. 실제로 감소하는 값만 타이머로 인정한다.
    await asyncio.sleep(sample_gap_s)
    read_a1 = await dom.read_selectors(page_a, selectors)
    t_a1 = time.monotonic()

    # ---- B: 같은 컨텍스트에서 새로고침 ----------------------------------
    await page_a.reload(wait_until="domcontentloaded")
    await page_a.wait_for_timeout(settle_ms)
    read_b = await dom.read_selectors(page_a, selectors)
    claims_b = await _claim_texts(page_a)
    t_b = time.monotonic()
    await ctx_a.close()

    # ---- C: 저장소가 빈 새 컨텍스트 -------------------------------------
    ctx_c = await browser.new_context()
    page_c = await ctx_c.new_page()
    await _goto(page_c, url, settle_ms)
    read_c = await dom.read_selectors(page_c, selectors)
    claims_c = await _claim_texts(page_c)
    t_c = time.monotonic()
    await ctx_c.close()

    spread = t_c - t_a0
    if spread < MIN_SPREAD_S:
        notes.append(
            f"A~C 관측 간격이 {spread:.1f}초로 짧아 판정이 흔들릴 수 있습니다. "
            f"sample_gap_s 를 늘리세요."
        )

    verdicts = [
        _judge_timer(
            timer=t,
            a0_text=t["text"],
            a1_text=read_a1.get(t["selector"]),
            b_text=read_b.get(t["selector"]),
            c_text=read_c.get(t["selector"]),
            elapsed_a=t_a1 - t_a0,
            elapsed_b=t_b - t_a0,
            elapsed_c=t_c - t_a0,
        )
        for t in timers
    ]

    claim_verdicts = _judge_claims(claims_a, claims_b, claims_c)

    return CountdownReport(url=url, timers=verdicts, claims=claim_verdicts, notes=notes)


async def _discover_candidates(page) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """스냅샷을 여러 번 찍어 후보를 합친다.

    캐러셀의 각 슬라이드는 고유한 선택자를 유지한 채 opacity 로만 보였다 숨었다 하므로,
    한 번의 스냅샷으로는 그 순간 숨어 있는 슬라이드(예: 진짜 카운트다운)를 놓칠 수 있다.
    """
    timers: dict[str, dict[str, Any]] = {}
    claims: dict[str, str] = {}
    for i in range(DISCOVERY_ROUNDS):
        snap = await dom.snapshot(page)
        for t in snap["timers"]:
            timers.setdefault(t["selector"], t)
        for c in snap["claims"]:
            claims.setdefault(c["selector"], c["text"])
        if i < DISCOVERY_ROUNDS - 1:
            await page.wait_for_timeout(DISCOVERY_INTERVAL_MS)
    return list(timers.values()), claims


async def _goto(page, url: str, settle_ms: int) -> None:
    await page.goto(url, wait_until="domcontentloaded")
    # 타이머 위젯은 대부분 스크립트가 늦게 그린다. 잠깐 기다렸다가 읽는다.
    await page.wait_for_timeout(settle_ms)


async def _claim_texts(page) -> dict[str, str]:
    snap = await dom.snapshot(page)
    return {c["selector"]: c["text"] for c in snap["claims"]}


def _judge_timer(
    *,
    timer: dict[str, Any],
    a0_text: str,
    a1_text: str | None,
    b_text: str | None,
    c_text: str | None,
    elapsed_a: float,
    elapsed_b: float,
    elapsed_c: float,
) -> TimerVerdict:
    a0 = parse_duration(a0_text)
    a1 = parse_duration(a1_text or "")
    b = parse_duration(b_text or "")
    c = parse_duration(c_text or "")

    obs = {
        "A(첫 방문)": f"{a0_text} = {format_duration(a0)}",
        f"A+{elapsed_a:.1f}s": f"{a1_text} = {format_duration(a1)}",
        f"B(새로고침, +{elapsed_b:.1f}s)": f"{b_text} = {format_duration(b)}",
        f"C(새 세션, +{elapsed_c:.1f}s)": f"{c_text} = {format_duration(c)}",
    }
    base = dict(selector=timer["selector"], context=timer["context"], observations=obs)

    if a0 is None:
        return TimerVerdict(
            **base, first_value=0, verdict="inconclusive",
            detail="값을 시간으로 읽지 못했습니다.",
        )

    # 네 번의 관측(A, A+gap, B, C)이 오차 범위 안에서 전부 똑같다면, 같은 페이지에서도
    # 리로드·새 세션을 거쳐도 전혀 움직이지 않았다는 뜻이다. 실제 무신사에서 "1:1 문의하기"
    # 같은 전화번호 표기가 콜론 패턴에 걸려 이런 식으로 나타났다 — 시간이 아니라 우연히
    # 시간처럼 보이는 문자열이므로 타이머로 취급하지 않는다.
    values = [a0, a1, b, c]
    if all(v is not None for v in values) and all(abs(v - a0) <= TOLERANCE_S for v in values):
        return TimerVerdict(
            **base, first_value=a0, verdict="not_counting",
            detail="같은 페이지·새로고침·새 세션 어디에서도 값이 변하지 않았습니다. 카운트다운이 아닙니다.",
        )

    if a1 is None:
        return TimerVerdict(
            **base, first_value=a0, verdict="inconclusive",
            detail="같은 페이지에서 값을 다시 읽지 못했습니다.",
        )

    # 같은 페이지 안에서 매초 줄어드는 유형(setInterval 애니메이션)은 속도가 맞는지 검증한다.
    # 반면 페이지를 열 때만 서버 마감을 기준으로 계산해 정적으로 보여주는 유형은
    # 같은 페이지 안에서는 안 움직이는 게 정상이므로(drift == 0), 이 검사를 건너뛰고
    # 곧바로 B/C 비교(리로드·새 세션 사이에 경과 시간만큼 줄었는지)로 넘어간다.
    drift = a0 - a1
    if drift < 0:
        return TimerVerdict(
            **base, first_value=a0, verdict="inconclusive",
            detail="시간이 거꾸로 흐릅니다. 값을 직접 확인해 주세요.",
        )
    if drift > 0 and abs(drift - elapsed_a) > max(TOLERANCE_S, elapsed_a * 0.5):
        return TimerVerdict(
            **base, first_value=a0, verdict="inconclusive",
            detail=f"{elapsed_a:.1f}초 동안 {drift}초 감소 — 실시간 초읽기와 속도가 맞지 않습니다.",
        )

    if b is None or c is None:
        return TimerVerdict(
            **base, first_value=a0, verdict="inconclusive",
            detail="재방문 시 같은 요소를 다시 찾지 못했습니다.",
        )

    reset_b = abs(b - a0) <= TOLERANCE_S
    cont_b = abs(b - (a0 - elapsed_b)) <= TOLERANCE_S
    reset_c = abs(c - a0) <= TOLERANCE_S
    cont_c = abs(c - (a0 - elapsed_c)) <= TOLERANCE_S

    if reset_c and reset_b:
        return TimerVerdict(
            **base, first_value=a0, verdict="fake_session",
            detail=(
                f"새로고침만 해도 {format_duration(a0)} 로 되돌아갑니다. "
                f"서버가 정한 마감 시각이 없으므로 이 마감은 영원히 오지 않습니다."
            ),
        )
    if reset_c and cont_b:
        return TimerVerdict(
            **base, first_value=a0, verdict="fake_storage",
            detail=(
                f"같은 브라우저에서는 이어지지만, 저장소를 비운 새 방문에서는 "
                f"{format_duration(a0)} 부터 다시 시작합니다. 방문자마다 별도의 마감을 부여하는 방식입니다."
            ),
        )
    if cont_c and cont_b:
        return TimerVerdict(
            **base, first_value=a0, verdict="genuine",
            detail=(
                f"새로고침과 새 세션 모두에서 경과 시간만큼 줄어 있습니다. "
                f"고정된 마감 시각을 기준으로 동작합니다."
            ),
        )
    if reset_c and not cont_b:
        return TimerVerdict(
            **base, first_value=a0, verdict="fake_session",
            detail=f"새 세션에서 {format_duration(a0)} 로 되돌아갑니다.",
        )
    return TimerVerdict(
        **base, first_value=a0, verdict="inconclusive",
        detail="되돌아감·이어짐 어느 쪽과도 맞지 않습니다. 값을 직접 확인해 주세요.",
    )


def _judge_claims(
    a: dict[str, str], b: dict[str, str], c: dict[str, str]
) -> list[ClaimVerdict]:
    out: list[ClaimVerdict] = []
    for selector, text_a in a.items():
        texts = [text_a, b.get(selector), c.get(selector)]
        seen = [t for t in texts if t is not None]
        if len(seen) < 2:
            continue
        if len(set(seen)) > 1:
            out.append(
                ClaimVerdict(
                    text_by_visit=seen,
                    verdict="volatile",
                    detail=(
                        "몇 초 사이 서로 다른 세션에서 값이 달라졌습니다. "
                        "실제 재고·조회수가 아니라 무작위로 생성된 값일 가능성이 큽니다."
                    ),
                )
            )
        else:
            out.append(
                ClaimVerdict(
                    text_by_visit=seen,
                    verdict="stable",
                    detail="여러 세션에서 같은 값이 유지됩니다.",
                )
            )
    return out
