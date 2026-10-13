"""The one lag method used everywhere on the dashboard.

A "side" is a list of scored models from one group (a country, or a country and
weights class). For a leader side A and a trailing side B at date t:

    lag(t) = t - (release date of the earliest A model scoring at least B's best to date)

If no A model has reached B's best, B leads and the lag is negative, computed
the same way in reverse. The overall ECI headline, every benchmark, and the
open-versus-closed comparisons all call `lag_at`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median

DAYS_PER_MONTH = 365.25 / 12
COVERAGE_MIN_MODELS = 3        # trailing-side models released in the last 12 months
COVERAGE_WINDOW_DAYS = 365
COVERAGE_RECENT_DAYS = 183     # and at least one in the last 6 months
SATURATION_SHARE = 0.95        # both sides within 5% of the ceiling


@dataclass(frozen=True)
class Point:
    day: date
    score: float
    lo: float | None = None
    hi: float | None = None
    model: str = ""
    lab: str = ""


def records(points: list[Point]) -> list[Point]:
    """Best-to-date frontier: models that beat everything released before them."""
    out: list[Point] = []
    for p in sorted(points, key=lambda p: (p.day, p.score)):
        if out and out[-1].day == p.day and p.score > out[-1].score:
            out[-1] = p  # same-day release: keep the better one
        elif not out or p.score > out[-1].score:
            out.append(p)
    return out


def best_at(recs: list[Point], t: date) -> Point | None:
    hit = None
    for p in recs:
        if p.day > t:
            break
        hit = p
    return hit


def first_reached(recs: list[Point], score: float, t: date) -> Point | None:
    """Earliest record released by t that scores at least `score`."""
    for p in recs:
        if p.day > t:
            return None
        if p.score >= score:
            return p
    return None


def _lag_days(a: list[Point], b: list[Point], t: date, b_score: float, a_score: float) -> tuple[int, Point | None]:
    hit = first_reached(a, b_score, t)
    if hit is not None:
        return (t - hit.day).days, hit
    hit = first_reached(b, a_score, t)
    if hit is not None:
        return -(t - hit.day).days, hit
    return 0, None  # neither side clearly ahead at this threshold


def lag_at(a_recs: list[Point], b_recs: list[Point], t: date) -> dict | None:
    """How far side B is behind side A at date t, in days. Negative if B leads.

    Also returns the lag recomputed at the low and high ends of the confidence
    interval on the trailing side's best score, when it has one.
    """
    a, b = best_at(a_recs, t), best_at(b_recs, t)
    if a is None or b is None:
        return None
    days, match = _lag_days(a_recs, b_recs, t, b.score, a.score)
    trailing = b if days >= 0 else a
    lo = hi = None
    if trailing.lo is not None and trailing.hi is not None:
        if days >= 0:
            ends = [_lag_days(a_recs, b_recs, t, s, a.score)[0] for s in (b.lo, b.hi)]
        else:
            ends = [_lag_days(a_recs, b_recs, t, b.score, s)[0] for s in (a.lo, a.hi)]
        lo, hi = min(ends + [days]), max(ends + [days])
    return {"days": days, "lo": lo, "hi": hi, "a_best": a, "b_best": b, "match": match}


def lag_series(a_recs: list[Point], b_recs: list[Point], start: date, end: date) -> list[tuple[date, int]]:
    """Lag at every date where it can jump. Between these dates it grows by one
    day per day (or shrinks, while B leads), which is what makes the sawtooth."""
    days = sorted({p.day for p in a_recs + b_recs if start <= p.day <= end} | {start})
    out = []
    for d in days:
        hit = lag_at(a_recs, b_recs, d)
        if hit is not None:
            out.append((d, hit["days"]))
    return out


def covered(b_days: list[date], t: date) -> bool:
    """Enough recent trailing-side models to trust the lag at date t."""
    past = [d for d in b_days if d <= t]
    if not past:
        return False
    recent = sum(1 for d in past if d > t - timedelta(days=COVERAGE_WINDOW_DAYS))
    return recent >= COVERAGE_MIN_MODELS and max(past) > t - timedelta(days=COVERAGE_RECENT_DAYS)


def saturated_from(a_recs: list[Point], b_recs: list[Point], ceiling: float | None) -> date | None:
    """First date both sides' best scores are within 5% of the ceiling."""
    if not ceiling:
        return None
    bar = SATURATION_SHARE * ceiling
    hits = [next((p.day for p in recs if p.score >= bar), None) for recs in (a_recs, b_recs)]
    return None if None in hits else max(hits)


def months(days: float | None) -> float | None:
    return None if days is None else round(days / DAYS_PER_MONTH, 1)


def summarise(values: list[float]) -> dict | None:
    """Domain lag: the median across eligible benchmarks, with the spread."""
    if not values:
        return None
    return {"median": median(values), "min": min(values), "max": max(values), "n": len(values)}


def month_ends(start: date, end: date) -> list[date]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        nxt = date(y + (m == 12), m % 12 + 1, 1)
        out.append(min(nxt - timedelta(days=1), end))
        y, m = nxt.year, nxt.month
    return out


def current_status(us: list[Point], cn: list[Point], cn_days: list[date], ceiling: float | None,
                   listed: str, t: date) -> str:
    """Whether a benchmark counts toward the current profile.

    no_china: no Chinese score at all.  saturated: on the hand-kept saturated
    list, or both countries within 5% of the ceiling.  historical: a closed or
    superseded series.  stale: too few recent Chinese models.  yes: counts.
    """
    if not cn_days:
        return "no_china"
    sat = saturated_from(us, cn, ceiling)
    if listed == "saturated" or (sat is not None and sat <= t):
        return "saturated"
    if listed == "historical":
        return "historical"
    return "yes" if covered(cn_days, t) else "stale"


def counts_in_history(us: list[Point], cn: list[Point], cn_days: list[date], ceiling: float | None,
                      listed: str, history_until: date | None, t: date, today: date) -> bool:
    """Whether a benchmark counts toward the domain lag for a past date t.
    The same coverage and saturation rules, applied as of t. Benchmarks on the
    saturated list and closed series count for the past but never for today."""
    if t >= today:
        return current_status(us, cn, cn_days, ceiling, listed, t) == "yes"
    sat = saturated_from(us, cn, ceiling)
    if (sat is not None and sat <= t) or (history_until is not None and t >= history_until):
        return False
    if listed == "saturated" and t >= today.replace(day=1):
        return False
    return covered(cn_days, t)


LOW_CONFIDENCE_MIN = 3  # an area needs this many counted benchmarks to be trusted


def low_confidence(lags: list[float]) -> list[str]:
    """Why an area's lag should be read with caution; empty if it should not.

    few: fewer than three counted benchmarks.  split: the benchmarks disagree
    on direction (China ahead on at least one and behind on at least one).
    """
    reasons = []
    if len(lags) < LOW_CONFIDENCE_MIN:
        reasons.append("few")
    if any(v < 0 for v in lags) and any(v > 0 for v in lags):
        reasons.append("split")
    return reasons


def coverage_expires(b_days: list[date], t: date) -> date | None:
    """The date a benchmark stops counting if no new trailing-side model is
    scored: six months after the latest one, or when fewer than three remain
    inside the 12-month window. None if it is not covered at t."""
    if not covered(b_days, t):
        return None
    past = sorted((d for d in b_days if d <= t), reverse=True)
    lapse_recent = past[0] + timedelta(days=COVERAGE_RECENT_DAYS)
    lapse_count = past[COVERAGE_MIN_MODELS - 1] + timedelta(days=COVERAGE_WINDOW_DAYS)
    return min(lapse_recent, lapse_count)
