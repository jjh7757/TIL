"""화면에 보이는 남은 시간 문자열을 초 단위 정수로 바꾼다.

타이머 표기는 쇼핑몰마다 제각각이라, 탐지의 첫 단계는 "이 텍스트가 몇 초를 뜻하는가"를
플랫폼 독립적으로 읽어내는 것이다. 콜론 표기(01:23:45)와 단위 표기(1시간 23분 45초)를
모두 다루고, 둘이 섞인 표기(2일 03:04:05)도 지원한다.
"""

from __future__ import annotations

import re

# 콜론 표기. 뒤에서부터 초·분·시·일 순으로 채운다.
_COLON = re.compile(
    r"(?<![\d.])(\d{1,3})\s*[:：]\s*(\d{1,2})"
    r"(?:\s*[:：]\s*(\d{1,2}))?"
    r"(?:\s*[:：]\s*(\d{1,2}))?"
    r"(?![\d.])"
)

# 단위 표기. 한국어와 영어를 함께 받는다.
_UNITS: list[tuple[int, str]] = [
    (86400, r"일|days?|d"),
    (3600, r"시간|시|hours?|hrs?|h"),
    (60, r"분|minutes?|mins?|m"),
    (1, r"초|seconds?|secs?|s"),
]
_UNIT_RES = [
    (mult, re.compile(r"(?<![\d.])(\d{1,4})\s*(?:" + pat + r")(?![a-z가-힣])", re.IGNORECASE))
    for mult, pat in _UNITS
]

# 남은 시간처럼 "보이기만" 하면 통과시키는 느슨한 필터.
# 후보를 넓게 잡고, 실제 감소 여부는 뒤에서 행동으로 검증한다.
LOOKS_LIKE_TIME = re.compile(
    r"\d{1,3}\s*[:：]\s*\d{1,2}"
    r"|\d+\s*(?:일|시간|분|초)"
    r"|\d+\s*(?:days?|hours?|hrs?|minutes?|mins?|seconds?|secs?|[dhms])(?![a-z])",
    re.IGNORECASE,
)


def parse_duration(text: str) -> int | None:
    """텍스트에서 남은 시간을 초로 읽는다. 읽을 수 없으면 None."""
    if not text:
        return None

    colon = _COLON.search(text)
    if colon:
        parts = [int(g) for g in colon.groups() if g is not None]
        seconds = _from_colon_parts(parts)
        # "2일 03:04:05"처럼 콜론 앞에 일수가 따로 붙는 표기를 보정한다.
        if len(parts) < 4:
            head = text[: colon.start()]
            days = _UNIT_RES[0][1].search(head)
            if days:
                seconds += int(days.group(1)) * 86400
        return seconds

    total = 0
    matched = False
    consumed: list[tuple[int, int]] = []
    for mult, pattern in _UNIT_RES:
        for m in pattern.finditer(text):
            # 큰 단위가 이미 먹은 구간을 작은 단위가 다시 읽지 않도록 막는다.
            # ("1시간" 의 '시간' 을 '분'/'초' 패턴이 건드리는 경우는 없지만,
            #  영어 축약형끼리는 겹칠 수 있다.)
            if any(s <= m.start() < e for s, e in consumed):
                continue
            consumed.append((m.start(), m.end()))
            total += int(m.group(1)) * mult
            matched = True

    return total if matched else None


def _from_colon_parts(parts: list[int]) -> int:
    """[3, 4] -> 분:초, [1, 2, 3] -> 시:분:초, [1, 2, 3, 4] -> 일:시:분:초."""
    weights = {2: (60, 1), 3: (3600, 60, 1), 4: (86400, 3600, 60, 1)}[len(parts)]
    return sum(p * w for p, w in zip(parts, weights))


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "-"
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if d:
        return f"{sign}{d}일 {h:02d}:{m:02d}:{s:02d}"
    return f"{sign}{h:02d}:{m:02d}:{s:02d}"
