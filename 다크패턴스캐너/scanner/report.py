"""탐지 결과를 셀러가 읽고 바로 고칠 수 있는 형태로 옮긴다.

리포트에는 세 가지가 반드시 들어간다: 무엇이 문제인지, 어디에 있는지, 왜 문제인지(법적 근거).
법적 근거는 유형 이름까지만 적는다 — 조문 번호는 별도 검증 전까지 단정하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from .checkout import CheckoutReport
from .countdown import CountdownReport

DISCLAIMER = (
    "※ 아래 법령 매핑은 전자상거래법 개정안이 명시한 6개 유형과의 대응 관계이며, "
    "법률 자문이 아닙니다. 조문 번호는 별도 확인이 필요합니다."
)


@dataclass
class Finding:
    severity: str  # high | medium | low | info
    title: str
    where: str
    detail: str
    legal: str
    fix: str


_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
_SEVERITY_MARK = {"high": "[높음]", "medium": "[보통]", "low": "[낮음]", "info": "[참고]"}


def from_countdown(report: CountdownReport) -> list[Finding]:
    findings: list[Finding] = []

    for t in report.timers:
        if t.verdict in ("fake_session", "fake_storage"):
            findings.append(
                Finding(
                    severity="high",
                    title="마감 시각이 존재하지 않는 카운트다운",
                    where=f"{report.url}  ·  {t.selector}\n    문맥: {t.context}",
                    detail=t.detail + "\n" + _observation_block(t.observations),
                    legal=(
                        "표시·광고의 공정화에 관한 법률상 거짓·과장 광고에 해당할 소지. "
                        "(전자상거래법이 명시한 다크패턴 6개 유형에는 직접 포함되지 않음)"
                    ),
                    fix=(
                        "서버가 정한 실제 마감 시각을 기준으로 남은 시간을 계산하도록 바꾸거나, "
                        "마감이 없다면 타이머 자체를 제거하세요."
                    ),
                )
            )
        elif t.verdict == "genuine":
            findings.append(
                Finding(
                    severity="info",
                    title="정상 동작하는 카운트다운",
                    where=f"{report.url}  ·  {t.selector}",
                    detail=t.detail,
                    legal="-",
                    fix="조치 불필요.",
                )
            )
        elif t.verdict == "inconclusive":
            findings.append(
                Finding(
                    severity="low",
                    title="판정 보류 — 사람이 확인 필요",
                    where=f"{report.url}  ·  {t.selector}\n    문맥: {t.context}",
                    detail=t.detail + "\n" + _observation_block(t.observations),
                    legal="-",
                    fix="관측값을 직접 확인하세요.",
                )
            )

    for c in report.claims:
        if c.verdict == "volatile":
            findings.append(
                Finding(
                    severity="medium",
                    title="세션마다 값이 달라지는 재고·조회수 표시",
                    where=report.url,
                    detail=c.detail + "\n    관측값: " + " / ".join(c.text_by_visit),
                    legal="표시·광고의 공정화에 관한 법률상 거짓·과장 광고에 해당할 소지.",
                    fix="실제 재고·조회 데이터에 연결하거나, 표시를 제거하세요.",
                )
            )

    return findings


def from_checkout(report: CheckoutReport) -> list[Finding]:
    findings: list[Finding] = []

    if report.is_dark_pattern and report.advertised and report.final:
        lines = [
            f"처음 표시 금액 {report.advertised} → 최종 결제 금액 {report.final} "
            f"(+{int(report.increase):,}, {report.increase_pct:.1f}% 증가)",
            f"총액이 처음 뛴 단계: {report.jump_step}",
            "",
            "단계별 총액:",
        ]
        for s in report.steps:
            total = str(s.total) if s.total else "(읽지 못함)"
            lines.append(f"    {s.name}: {total}   — {s.total_basis}")
        if report.hidden_fees:
            lines.append("")
            lines.append("뒤늦게 등장하거나 값이 오른 비용 항목:")
            for f in report.hidden_fees:
                lines.append(
                    f"    {f.label}: {f.amount}  ({f.first_seen_step} 단계, {f.reason})"
                )

        findings.append(
            Finding(
                severity="high",
                title="결제 단계에서 총액이 증가함 (숨은 비용)",
                where=report.steps[-1].url if report.steps else "-",
                detail="\n".join(lines),
                legal="전자상거래법 다크패턴 6개 유형 중 '순차공개 가격책정'에 해당.",
                fix=(
                    "상품 페이지에서부터 배송비·수수료를 포함한 총액을 함께 표시하거나, "
                    "최소한 추가 비용의 존재와 금액을 첫 화면에 고지하세요."
                ),
            )
        )

    for opt in report.preselected_paid:
        findings.append(
            Finding(
                severity="high",
                title="유료 옵션이 기본 선택되어 있음",
                where=f"{report.steps[-1].url if report.steps else '-'}  ·  {opt['selector']}",
                detail=f"{opt['label']} (기본값 선택됨, 금액 {opt['amount']})",
                legal="전자상거래법 다크패턴 6개 유형 중 '특정 옵션 사전 선택'에 해당.",
                fix="선택 해제 상태를 기본값으로 두고, 소비자가 직접 선택하게 하세요.",
            )
        )

    for note in report.notes:
        findings.append(
            Finding(
                severity="low", title="스캔 제약", where="-",
                detail=note, legal="-", fix="-",
            )
        )

    return findings


def render(title: str, findings: list[Finding]) -> str:
    findings = sorted(findings, key=lambda f: _SEVERITY_ORDER.get(f.severity, 9))
    counts = {k: 0 for k in _SEVERITY_ORDER}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    out = [
        "=" * 78,
        title,
        "=" * 78,
        f"높음 {counts['high']} · 보통 {counts['medium']} · 낮음 {counts['low']} · 참고 {counts['info']}",
        "",
    ]
    if not findings:
        out.append("탐지된 항목이 없습니다.")
    for i, f in enumerate(findings, 1):
        out.append(f"{i}. {_SEVERITY_MARK.get(f.severity, '')} {f.title}")
        out.append(f"   위치: {f.where}")
        for line in f.detail.splitlines():
            out.append(f"   {line}")
        if f.legal != "-":
            out.append(f"   법적 근거: {f.legal}")
        if f.fix != "-":
            out.append(f"   조치: {f.fix}")
        out.append("")
    out.append(DISCLAIMER)
    return "\n".join(out)


def _observation_block(observations: dict[str, str]) -> str:
    return "\n".join(f"    {k:<28} {v}" for k, v in observations.items())
