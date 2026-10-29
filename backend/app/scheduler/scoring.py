from __future__ import annotations

from .config import MODE_WEIGHTS


def normalize(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    if hi - lo < 1e-12:                      # all equal: avoid dividing by zero
        return [0.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def score_all(cands: list, mode: str) -> None:
    wc, wg = MODE_WEIGHTS[mode]
    nc = normalize([c.risk_adj_cost for c in cands])
    ng = normalize([c.carbon_kg for c in cands])
    for c, a, b in zip(cands, nc, ng):
        c.score = wc * a + wg * b


def rank(cands: list) -> list:
    """Lowest score first. Ties: lower interruption risk, earlier start, then stable names."""
    return sorted(cands, key=lambda c: (round(c.score, 9), c.risk_chance, c.start,
                                        round(c.risk_adj_cost, 9), c.region, c.instance))


def pick(ranked: list, n_alternatives: int = 2):
    """Best overall, plus the best candidate of each OTHER region (so alternatives differ)."""
    best, alts, seen = ranked[0], [], {ranked[0].region}
    for c in ranked[1:]:
        if c.region not in seen:
            alts.append(c)
            seen.add(c.region)
        if len(alts) == n_alternatives:
            break
    return best, alts
