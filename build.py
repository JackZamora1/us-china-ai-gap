"""Build index.html from the tables in data/.

Usage:  python build.py                      (standard library only)
        python build.py --as-of 2026-10-21  (compute everything as if today were that date)

Computes every lag with gap.py as of today, for two views of the data
(independent sources only, and all sources), and writes one self-contained
page with the data inlined, so index.html can be opened directly, emailed,
or hosted anywhere. Rebuild to move "today" forward.

Also writes data/profile.json, a small summary the automatic refresh uses to
check that no area moved implausibly far in one run.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

import gap
from gap import Point

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
TODAY = date.today()
START = date(2023, 1, 1)
# Before this date Epoch scored only open-weight Chinese models and the other
# sources covered few Chinese models, so charts shade the period.
THIN_UNTIL = date(2025, 1, 1)
LAPSE_WARNING_DAYS = 30
VARIANTS = {"independent": ("independent",), "all": ("independent", "self_reported", "unknown")}
OVERALL = ["eci", "aa_index", "arena_text"]
WHY = {"few": "fewer than 3 benchmarks", "split": "benchmarks disagree on direction"}


def read_csv(name: str) -> list[dict]:
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def day(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None


def pt(p: Point | None) -> list | None:
    """A frontier point as the page wants it: date, score, model, lab."""
    return None if p is None else [p.day.isoformat(), round(p.score, 4), p.model, p.lab]


def lag_out(hit: dict | None) -> dict | None:
    if hit is None:
        return None
    return {"m": gap.months(hit["days"]), "lo": gap.months(hit["lo"]), "hi": gap.months(hit["hi"]),
            "lead": pt(hit["a_best"]), "trail": pt(hit["b_best"]), "match": pt(hit["match"])}


class Bench:
    """One benchmark under one view of the data."""

    def __init__(self, cfg: dict, rows: list[dict], models: dict):
        self.cfg = cfg
        self.ceiling = number(cfg["ceiling"])
        self.listed = cfg["listed_status"]
        self.until = day(cfg["history_until"])
        sides: dict[tuple, list[Point]] = {}
        for r in rows:
            m = models.get(r["model"])
            d = m and day(m["release_date"])
            if not d or m["country"] not in ("US", "China"):
                continue
            p = Point(d, float(r["score"]), number(r["ci_low"]), number(r["ci_high"]), r["model"], m["lab"])
            sides.setdefault((m["country"], "any"), []).append(p)
            sides.setdefault((m["country"], m["weights"]), []).append(p)
        self.points = sides
        self.us, self.cn = gap.records(sides.get(("US", "any"), [])), gap.records(sides.get(("China", "any"), []))
        self.cn_days = [p.day for p in sides.get(("China", "any"), [])]
        self.n_us, self.n_cn = len(sides.get(("US", "any"), [])), len(self.cn_days)
        self.status = gap.current_status(self.us, self.cn, self.cn_days, self.ceiling, self.listed, TODAY)
        self.expires = gap.coverage_expires(self.cn_days, TODAY) if self.status == "yes" else None

    def lag(self, t: date) -> dict | None:
        return gap.lag_at(self.us, self.cn, t)

    def in_history(self, t: date) -> bool:
        return gap.counts_in_history(self.us, self.cn, self.cn_days, self.ceiling, self.listed, self.until, t, TODAY)

    def open_view(self) -> dict:
        usc = gap.records(self.points.get(("US", "closed"), []))
        uso = gap.records(self.points.get(("US", "open"), []))
        cno = gap.records(self.points.get(("China", "open"), []))
        return {"usc": [pt(p) for p in usc], "uso": [pt(p) for p in uso], "cno": [pt(p) for p in cno],
                "cno_usc": lag_out(gap.lag_at(usc, cno, TODAY)), "uso_usc": lag_out(gap.lag_at(usc, uso, TODAY)),
                "cno_uso": lag_out(gap.lag_at(uso, cno, TODAY))}

    def out(self) -> dict:
        sat = gap.saturated_from(self.us, self.cn, self.ceiling)
        return {
            "status": self.status, "lag": lag_out(self.lag(TODAY)), "n_us": self.n_us, "n_cn": self.n_cn,
            "latest_cn": max(self.cn_days).isoformat() if self.cn_days else None,
            "sat": sat.isoformat() if sat else None, "expires": self.expires.isoformat() if self.expires else None,
            "series": [[(d - START).days, v] for d, v in gap.lag_series(self.us, self.cn, START, TODAY)],
            "us": [pt(p) for p in self.us], "cn": [pt(p) for p in self.cn], "open": self.open_view(),
        }


def counted_lags(benches: dict[str, Bench], ids: list[str], t: date, current: bool) -> dict[str, int]:
    out = {}
    for b in ids:
        ok = benches[b].status == "yes" if current else benches[b].in_history(t)
        hit = benches[b].lag(t) if ok else None
        if hit is not None:
            out[b] = hit["days"]
    return out


def domain_summary(benches: dict[str, Bench], ids: list[str], t: date, current: bool) -> dict | None:
    """Median lag across an area's counted benchmarks, with spread and confidence."""
    lags = counted_lags(benches, ids, t, current)
    s = gap.summarise(list(lags.values()))
    return s and {"m": gap.months(s["median"]), "min": gap.months(s["min"]), "max": gap.months(s["max"]),
                  "n": s["n"], "low": gap.low_confidence(list(lags.values()))}


def fallback_estimate(area: str, assessments: list[dict]) -> dict | None:
    """The most recent published estimate for an area too thin to measure here."""
    rows = [a for a in assessments if a["domain"] == area and a["unit"] == "months" and a["date"] <= TODAY.isoformat()]
    if not rows:
        return None
    a = max(rows, key=lambda r: r["date"])
    return {"publisher": a["publisher"], "date": a["date"], "estimate": a["estimate"], "measures": a["measures"],
            "low": number(a["low"]), "high": number(a["high"]), "point": number(a["point"]), "url": a["source_url"]}


def area_profile(area: str, benches: dict[str, Bench], ids: list[str], assessments: list[dict]) -> dict | None:
    s = domain_summary(benches, ids, TODAY, current=True)
    lags = counted_lags(benches, ids, TODAY, current=True)
    out = s or {"m": None, "n": 0, "low": ["few"]}
    name = lambda b: benches[b].cfg["name"]
    if "split" in out["low"]:
        ahead = [f"{name(b)} (China ahead by {abs(gap.months(v))} months)" for b, v in lags.items() if v < 0]
        behind = [f"{name(b)} (behind by {gap.months(v)})" for b, v in lags.items() if v > 0]
        out["split_note"] = f"The median hides a disagreement: {' and '.join(ahead)} against {' and '.join(behind)}."
    if out["n"] < 2:
        out["fallback"] = fallback_estimate(area, assessments)
    # Warn when every counted benchmark in the area is about to lose eligibility.
    expiries = {b: benches[b].expires for b in lags if benches[b].expires}
    if expiries and len(expiries) == len(lags) and max(expiries.values()) <= TODAY + timedelta(days=LAPSE_WARNING_DAYS):
        last = max(expiries.values())
        out["lapse"] = {"date": last.isoformat(), "benchmarks": [name(b) for b in expiries]}
    return out if s or out.get("fallback") or ids else None


def open_summary(benches: dict[str, Bench], ids: list[str]) -> dict:
    out = {}
    for key in ("cno_usc", "uso_usc", "cno_uso"):
        vals = [v["m"] for b in ids if benches[b].status == "yes" and (v := benches[b].open_view()[key])]
        s = gap.summarise(vals)
        out[key] = s and {"m": round(s["median"], 1), "min": s["min"], "max": s["max"], "n": s["n"]}
    return out


def compare(a: dict, benches: dict[str, Bench], by_domain: dict[str, list[str]], tops: list[dict]) -> dict | None:
    """My own number for the same thing a published estimate measures."""
    how, t = a["compare_to"], day(a["date"])
    if how == "eci_mean_since_2023":
        vals = [h["days"] for d in gap.month_ends(START, t) if (h := benches["eci"].lag(d))]
        return vals and {"m": gap.months(mean(vals)), "lo": gap.months(min(vals)), "hi": gap.months(max(vals)),
                         "label": f"ECI lag at each month end, January 2023 to {t:%B %Y}: mean and range"}
    if how.startswith("bench:") and how[6:] in benches:
        h = lag_out(benches[how[6:]].lag(t))
        return h and {"m": h["m"], "lo": h["lo"], "hi": h["hi"], "label": f"{benches[how[6:]].cfg['name']} lag on {t.isoformat()}"}
    if how.startswith("domain:"):
        s = domain_summary(benches, by_domain.get(how[7:], []), t, current=False)
        return s and {"m": s["m"], "lo": s["min"], "hi": s["max"],
                      "label": f"{how[7:]} area lag on {t.isoformat()} ({s['n']} benchmark{'s' if s['n'] != 1 else ''}; China against the US, any weights)"}
    if how == "arena_text_pct":
        past = [r for r in tops if r["date"] <= a["date"] and r.get("us_top") and r.get("cn_top")]
        if not past:
            return None
        r = past[-1]
        pct = (float(r["us_top"]) - float(r["cn_top"])) / float(r["cn_top"]) * 100
        return {"m": round(pct, 1), "lo": None, "hi": None, "unit": "percent",
                "label": f"Arena text board of {r['date']}: {r['us_model']} over {r['cn_model']}"}
    return None


# The seven companies Epoch names individually are all headquartered in the US.
US_CHIP_OWNERS = ["Amazon", "CoreWeave", "Google", "Meta", "Microsoft", "Oracle", "xAI"]
PRICE_THRESHOLDS = [20, 30, 40, 45]
# Pricing terms the blended list price hides, shown when the model sets a row of the cost table.
PRICE_NOTES = [
    {"model": "Claude Haiku 5.5", "note": "Its list price ($0.10 input and $0.50 output per million tokens) applies to prompts under 100K tokens; "
     "longer prompts are charged five times as much, so the blended price understates the cost of long-context use."},
]


def stock_view() -> dict:
    """AI chip stock by owner group at each complete quarter end, in H100-equivalents."""
    rows = read_csv("compute_stock.csv")
    partial = {r["quarter_end"] for r in rows if r["incomplete"] == "True"}
    quarters = sorted({r["quarter_end"] for r in rows} - partial)
    # Cumulative figures carry forward through quarters where an owner has no new row.
    latest: dict[tuple, dict] = {}
    series = {k: [] for k in ("china", "china_lo", "china_hi", "smuggled", "us_named", "other")}
    by_quarter: dict[str, list[dict]] = {}
    for r in rows:
        by_quarter.setdefault(r["quarter_end"], []).append(r)
    mix = {}
    for q in quarters:
        for r in by_quarter[q]:
            latest[(r["owner"], r["chip_designer"])] = r
        total = lambda owners, col="h100e": sum(number(r[col]) or 0 for (o, _), r in latest.items() if o in owners)
        series["china"].append(total({"China"}))
        series["china_lo"].append(total({"China"}, "h100e_p5"))
        series["china_hi"].append(total({"China"}, "h100e_p95"))
        series["smuggled"].append(total({"China (smuggled)"}))
        series["us_named"].append(total(set(US_CHIP_OWNERS)))
        series["other"].append(total({"Other"}))
        mix = {d: number(r["h100e"]) for (o, d), r in latest.items() if o == "China"}
    days = [day(q) for q in quarters]
    asof = days[-1]

    def lag(china: list[float], lo=None, hi=None) -> dict | None:
        us = gap.records([Point(d, v, model="Seven US companies") for d, v in zip(days, series["us_named"])])
        cn = gap.records([Point(d, v, lo and lo[i], hi and hi[i], "China") for i, (d, v) in enumerate(zip(days, china))])
        hit = gap.lag_at(us, cn, asof)
        return hit and {"m": gap.months(hit["days"]), "lo": gap.months(hit["lo"]), "hi": gap.months(hit["hi"]),
                        "match": hit["match"].day.isoformat() if hit["match"] else None}

    with_smuggled = [a + b for a, b in zip(series["china"], series["smuggled"])]
    history = []
    for i, d in enumerate(days):  # lag and ratio at each quarter end, for the policy timeline
        us = gap.records([Point(x, v) for x, v in zip(days[:i + 1], series["us_named"][:i + 1])])
        cn = gap.records([Point(x, v) for x, v in zip(days[:i + 1], series["china"][:i + 1])])
        hit = gap.lag_at(us, cn, d)
        history.append({"m": gap.months(hit["days"]) if hit else None,
                        "ratio": round(series["us_named"][i] / series["china"][i], 1) if series["china"][i] else None})
    return {
        "quarters": quarters, "asof": asof.isoformat(), "partial": sorted(partial), "owners": US_CHIP_OWNERS,
        "china": series["china"], "smuggled": with_smuggled, "has_smuggled": [v > 0 for v in series["smuggled"]],
        "us_named": series["us_named"], "non_china": [a + b for a, b in zip(series["us_named"], series["other"])],
        "lag": lag(series["china"], series["china_lo"], series["china_hi"]), "lag_smuggled": lag(with_smuggled),
        "ratio": round(series["us_named"][-1] / series["china"][-1], 1),
        "ratio_smuggled": round(series["us_named"][-1] / with_smuggled[-1], 1),
        "ratio_non_china": round((series["us_named"][-1] + series["other"][-1]) / series["china"][-1], 1),
        "mix": {k: v for k, v in sorted(mix.items(), key=lambda t: -t[1])}, "history": history,
    }


# A chip type counts as deployed at scale for an owner group once the group's cumulative
# units pass this threshold (see DECISIONS); the page also shows the lag at the others.
DEPLOYED_UNITS = 10_000
DEPLOYED_SENSITIVITY = [1_000, 5_000, 10_000, 25_000, 50_000, 100_000]
DEPLOYED_GROUPS = {"us": "Seven US companies", "cn_any": "China, any designer", "cn_cn": "China, Chinese-designed"}
METRICS = {"perf": "perf_16bit_flop_s", "bw": "memory_bandwidth_byte_s"}


def deployed_view() -> dict:
    """Best chip actually deployed at scale by each owner group, quarter by quarter.

    Uses Epoch's cumulative units by chip type. A chip type is deployed for a group
    from the first complete quarter end at which the group's cumulative units pass
    the threshold and the chip has been released. The months-behind rule is then
    applied to the best per-chip 16-bit performance and memory bandwidth among
    deployed types.
    """
    rows = read_csv("chip_deployment.csv")
    mapping = {(r["chip_designer"], r["chip_type"]): r for r in read_csv("chip_type_map.csv")}
    specs = {r["name"]: r for r in read_csv("chips.csv")}
    partial = {r["quarter_end"] for r in rows if r["incomplete"] == "True"}
    quarters = sorted({r["quarter_end"] for r in rows} - partial)
    owners = {"us": set(US_CHIP_OWNERS), "cn_any": {"China"}, "cn_cn": {"China"}}
    unmapped = sorted({f"{r['chip_designer']} {r['chip_type']}" for r in rows if (r["chip_designer"], r["chip_type"]) not in mapping
                       or mapping[(r["chip_designer"], r["chip_type"])]["chip_name"] not in specs})

    # Cumulative units per group and chip type at each complete quarter end, carried forward.
    latest: dict[tuple, float] = {}
    by_quarter: dict[str, list[dict]] = {}
    for r in rows:
        by_quarter.setdefault(r["quarter_end"], []).append(r)
    units: dict[str, dict[tuple, list[float]]] = {g: {} for g in owners}
    for i, q in enumerate(quarters):
        for r in by_quarter[q]:
            latest[(r["owner"], r["chip_designer"], r["chip_type"])] = number(r["units"]) or 0
        for g, who in owners.items():
            for (o, d, t), u in latest.items():
                if o in who and (d, t) in mapping and mapping[(d, t)]["chip_name"] in specs:
                    if g == "cn_cn" and specs[mapping[(d, t)]["chip_name"]]["country"] != "China":
                        continue
                    units[g].setdefault((d, t), [0.0] * len(quarters))[i] += u

    def spec(key: tuple, metric: str) -> float | None:
        m = mapping[key]
        if metric == "bw" and m["use_bandwidth"] != "yes":
            return None
        return number(specs[m["chip_name"]][METRICS[metric]])

    def deployed(threshold: int) -> dict[str, dict[tuple, str]]:
        out = {g: {} for g in owners}
        for g, types in units.items():
            for key, series in types.items():
                released = day(specs[mapping[key]["chip_name"]]["release_date"])
                for q, u in zip(quarters, series):
                    if u >= threshold and released and released <= day(q):
                        out[g][key] = q
                        break
        return out

    def frontier(dep: dict[tuple, str], metric: str) -> list[Point]:
        return gap.records([Point(day(q), v, model=key[1], lab=key[0]) for key, q in dep.items() if (v := spec(key, metric))])

    asof = day(quarters[-1])

    def lags(threshold: int) -> dict:
        dep = deployed(threshold)
        out = {}
        for metric in METRICS:
            us = frontier(dep["us"], metric)
            for g in ("cn_any", "cn_cn"):
                hit = gap.lag_at(us, frontier(dep[g], metric), asof)
                out[f"{g}_{metric}"] = lag_out(hit)
                # Epoch's data starts in 2022 Q1, so a match in that quarter means "at least".
                if out[f"{g}_{metric}"] and hit["match"] and hit["match"].day == day(quarters[0]):
                    out[f"{g}_{metric}"]["floor"] = True
        return out

    dep = deployed(DEPLOYED_UNITS)
    table = []
    for g, types in dep.items():
        for key, q in sorted(types.items(), key=lambda kv: (kv[1], kv[0])):
            m = mapping[key]
            table.append({"group": g, "chip_type": key[1], "designer": key[0], "chip_name": m["chip_name"], "deployed_from": q,
                          "units_then": round(units[g][key][quarters.index(q)]), "units_latest": round(units[g][key][-1]),
                          "perf_16bit_flop_s": spec(key, "perf"), "memory_bandwidth_byte_s": spec(key, "bw"), "flag": m["flag"]})
    best = {g: {metric: [pt(p) for p in frontier(dep[g], metric)] for metric in METRICS} for g in owners}
    return {
        "threshold": DEPLOYED_UNITS, "asof": asof.isoformat(), "first_quarter": quarters[0], "best": best, **lags(DEPLOYED_UNITS),
        "sensitivity": [{"t": t, **{k: (v and v["m"]) for k, v in lags(t).items()}} for t in DEPLOYED_SENSITIVITY],
        "table": table, "unmapped": unmapped,
        "flags": [{"type": f"{r['chip_designer']} {r['chip_type']}", "chip": r["chip_name"], "flag": r["flag"], "notes": r["notes"]}
                  for r in read_csv("chip_type_map.csv") if r["flag"]],
    }


def chip_view() -> dict:
    """Announced specifications: best 16-bit performance to date, Nvidia against Chinese designers."""
    rows = [r for r in read_csv("chips.csv") if day(r["release_date"]) and number(r["perf_16bit_flop_s"])]
    side = lambda keep: gap.records([Point(day(r["release_date"]), float(r["perf_16bit_flop_s"]), model=r["name"], lab=r["designer"])
                                     for r in rows if keep(r)])
    nvidia, china = side(lambda r: r["designer"] == "NVIDIA"), side(lambda r: r["country"] == "China")
    huawei = side(lambda r: r["designer"] == "Huawei")
    every = read_csv("chips.csv")
    announced = [{"name": r["name"], "planned": r["planned"], "notes": r["notes"], "url": r["source_url"]}
                 for r in every if r["status"] == "announced, not released"]
    undated = sorted(r["name"] for r in every if r["country"] == "China" and not day(r["release_date"]) and r["status"] != "announced, not released")
    added = [{"name": r["name"], "date": r["release_date"], "flag": r["flag"], "notes": r["notes"], "url": r["source_url"]}
             for r in every if r["added_by"] == "manual" and r["status"] == "released"]
    return {"announced": announced, "added": added,"nvidia": [pt(p) for p in nvidia], "china": [pt(p) for p in china], "huawei": [pt(p) for p in huawei],
            "lag": lag_out(gap.lag_at(nvidia, china, TODAY)), "lag_huawei": lag_out(gap.lag_at(nvidia, huawei, TODAY)),
            "undated": undated, "n_china": sum(r["country"] == "China" for r in rows), "n_nvidia": sum(r["designer"] == "NVIDIA" for r in rows)}


def training_view(models: dict, eci: dict) -> dict:
    """Largest disclosed training run to date by country, and capability against compute."""
    known = [m for m in models.values() if m["country"] in ("US", "China") and day(m["release_date"]) and number(m["training_compute_flop"])]
    side = lambda c: gap.records([Point(day(m["release_date"]), float(m["training_compute_flop"]), model=m["name"], lab=m["lab"])
                                  for m in known if m["country"] == c])
    us, cn = side("US"), side("China")
    scored = [m for m in models.values() if m["country"] in ("US", "China") and m["name"] in eci and day(m["release_date"]) and day(m["release_date"]) >= START]
    coverage = []
    for year in range(START.year, TODAY.year + 1):
        row = {"year": year}
        for c, key in (("US", "us"), ("China", "cn")):
            group = [m for m in scored if m["country"] == c and m["release_date"][:4] == str(year)]
            row[key] = [sum(1 for m in group if number(m["training_compute_flop"])), len(group)]
        coverage.append(row)
    return {"us": [pt(p) for p in us], "cn": [pt(p) for p in cn], "lag": lag_out(gap.lag_at(us, cn, TODAY)),
            "scatter": [[float(m["training_compute_flop"]), eci[m["name"]], m["country"], m["name"], m["release_date"]]
                        for m in scored if number(m["training_compute_flop"])],
            "coverage": coverage}


def cost_view() -> dict | None:
    """List price against capability today. There is no history yet, so no lag."""
    if not (DATA / "prices.csv").exists():
        return None
    rows = [r for r in read_csv("prices.csv") if r["country"] in ("US", "China") and number(r["aa_intelligence_index"]) is not None]
    pts = [[float(r["aa_intelligence_index"]), float(r["price_blended_usd_per_1m"]), r["country"], r["aa_name"], r["lab"]] for r in rows]
    frontier = {}
    for c in ("US", "China"):
        best, line = -1.0, []
        for p in sorted((p for p in pts if p[2] == c), key=lambda p: (p[1], -p[0])):  # cheapest first
            if p[0] > best:
                best = p[0]
                line.append(p)
        frontier[c] = line
    table = []
    for t in PRICE_THRESHOLDS:
        row = {"t": t}
        for c, key in (("US", "us"), ("China", "cn")):
            ok = [p for p in pts if p[2] == c and p[0] >= t]
            row[key] = min(ok, key=lambda p: p[1]) if ok else None
        row["ratio"] = round(row["us"][1] / row["cn"][1], 1) if row["us"] and row["cn"] else None
        table.append(row)
    history = read_csv("price_history.csv") if (DATA / "price_history.csv").exists() else []
    return {"points": pts, "frontier": frontier, "table": table, "n_priced": len(read_csv("prices.csv")),
            "n_us": sum(p[2] == "US" for p in pts), "n_cn": sum(p[2] == "China" for p in pts),
            "history_start": min((r["date"] for r in history), default=TODAY.isoformat()), "notes": PRICE_NOTES}


def write_deployed(d: dict) -> None:
    """The deployed-chip table behind the page, for checking against the sources."""
    cols = ["group", "chip_type", "designer", "chip_name", "deployed_from", "units_then", "units_latest",
            "perf_16bit_flop_s", "memory_bandwidth_byte_s", "flag"]
    with open(DATA / "deployed_chips.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in d["table"]:
            w.writerow({k: ("" if r[k] is None else r[k]) for k in cols})


def main() -> None:
    models = {m["name"]: m for m in read_csv("models.csv")}
    cfgs = read_csv("benchmarks.csv")
    scores = read_csv("scores.csv")
    domains = list(dict.fromkeys(c["domain"] for c in cfgs))
    by_domain = {d: [c["benchmark"] for c in cfgs if c["domain"] == d] for d in domains}
    months = gap.month_ends(START, TODAY)
    tops = read_csv("arena_text_tops.csv") if (DATA / "arena_text_tops.csv").exists() else []
    assessments = read_csv("assessments.csv")

    variants = {}
    for variant, types in VARIANTS.items():
        rows_by = {}
        for r in scores:
            if r["source_type"] in types:
                rows_by.setdefault(r["benchmark"], []).append(r)
        # A model can have one row per source type; keep its best allowed score.
        benches = {}
        for c in cfgs:
            best = {}
            for r in rows_by.get(c["benchmark"], []):
                if r["model"] not in best or float(r["score"]) > float(best[r["model"]]["score"]):
                    best[r["model"]] = r
            benches[c["benchmark"]] = Bench(c, list(best.values()), models)
        variants[variant] = {
            "bench": {b: x.out() for b, x in benches.items()},
            "profile": {d: area_profile(d, benches, by_domain[d], assessments) for d in domains},
            "heat": {d: [domain_summary(benches, by_domain[d], t, current=(t >= TODAY)) for t in months] for d in domains},
            "open": {d: open_summary(benches, by_domain[d]) for d in domains},
            "mine": [compare(a, benches, by_domain, tops) for a in assessments],
        }

    eci = {r["model"]: float(r["score"]) for r in scores if r["benchmark"] == "eci"}
    scored = {}
    for r in scores:
        scored.setdefault(r["model"], set()).add(r["benchmark"])
    releases = sorted(
        ({"name": m["name"], "lab": m["lab"], "country": m["country"], "date": m["release_date"], "weights": m["weights"],
          "url": m["release_url"], "flag": m["flag"], "notes": m["notes"], "eci": eci.get(m["name"]), "n": len(scored[m["name"]])}
         for m in models.values() if m["country"] in ("US", "China") and m["name"] in scored and day(m["release_date"])),
        key=lambda m: m["date"], reverse=True)

    events = [{"date": r["date"], "title": r["event"], "kind": r["category"], "text": r["description"],
               "src": r["source_url"], "flag": r["flag"], "notes": r["notes"]} for r in read_csv("events.csv") if r["date"]]
    stock = stock_view()
    deployed = deployed_view()
    write_deployed(deployed)
    data = {
        "compute": {"stock": stock, "deployed": deployed, "chips": chip_view(), "training": training_view(models, eci)},
        "cost": cost_view(),
        "built": TODAY.isoformat(), "start": START.isoformat(), "thin_until": THIN_UNTIL.isoformat(),
        "months": [t.isoformat() for t in months], "domains": domains, "overall": OVERALL, "why": WHY,
        "benchmarks": [{"id": c["benchmark"], "name": c["name"], "domain": c["domain"], "source": c["source"],
                        "kind": c["kind"], "ceiling": number(c["ceiling"]), "listed": c["listed_status"],
                        "until": c["history_until"], "notes": c["notes"], "basis": c["source_type_basis"],
                        "url": c["source_url"]} for c in cfgs],
        "variants": variants,
        "releases": releases[:150], "n_models": len(releases), "n_scores": len(scores),
        "flagged_models": [m for m in releases if m["flag"]][:60],
        "events": sorted(events, key=lambda e: e["date"]),
        "assessments": assessments,
        "has_aa": any(c["source"] == "Artificial Analysis" for c in cfgs),
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (ROOT / "template.html").read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
    (ROOT / "index.html").write_text(html, encoding="utf-8")

    # A small dated summary: the automatic refresh compares it with the committed one.
    summary = {"built": TODAY.isoformat(), "scores": len(scores),
               "compute": {"asof": stock["asof"], "china_h100e": stock["china"][-1]},
               "medians": {v: {d: (p or {}).get("m") for d, p in variants[v]["profile"].items()} for v in VARIANTS}}
    (DATA / "profile.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")

    print(f"wrote index.html ({len(html) // 1024} KB) as of {TODAY}")
    for variant in VARIANTS:
        print(f"\n{variant}: area lag in months (min to max across benchmarks, n)")
        for d in domains:
            s = variants[variant]["profile"][d]
            if not s or s["m"] is None:
                print(f"  {d:34s} no counted benchmark")
                continue
            low = f"  LOW CONFIDENCE: {', '.join(WHY[k] for k in s['low'])}" if s["low"] else ""
            print(f"  {d:34s} {s['m']:5.1f}  ({s['min']} to {s['max']}, n={s['n']}){low}")
    c = data["compute"]
    print(f"\ncompute stock at {stock['asof']}: China {stock['china'][-1]:,.0f} H100e, seven US companies {stock['us_named'][-1]:,.0f} "
          f"({stock['ratio']}x); lag {stock['lag']['m']} months, {stock['lag_smuggled']['m']} with the smuggling estimate ({stock['ratio_smuggled']}x)")
    dp = c["deployed"]
    for metric, unit in (("perf", "16-bit"), ("bw", "bandwidth")):
        print(f"deployed chips ({unit}, {dp['threshold']:,} units, to {dp['asof']}): China any designer "
              f"{(dp['cn_any_' + metric] or {}).get('m')} months; Chinese-designed {(dp['cn_cn_' + metric] or {}).get('m')}")
    if dp["unmapped"]:
        print("WARNING: chip types with no row in data/chip_type_map.csv or no match in chips.csv:", ", ".join(dp["unmapped"]))
    print(f"spec sheets (16-bit): all Chinese designers {c['chips']['lag']['m']} months behind Nvidia; Huawei {c['chips']['lag_huawei']['m']}")
    print(f"largest disclosed training run: {c['training']['lag']['m']} months (disclosure-limited; not a headline)")
    if data["cost"]:
        for row in data["cost"]["table"]:
            print(f"  index >= {row['t']}: US {row['us'] and (row['us'][3], row['us'][1])}  China {row['cn'] and (row['cn'][3], row['cn'][1])}  ratio {row['ratio']}")
    for d in domains:
        lapse = (variants["independent"]["profile"][d] or {}).get("lapse")
        if lapse:
            print(f"\nWARNING: {d} loses its last counted benchmark on {lapse['date']} "
                  f"({', '.join(lapse['benchmarks'])}) unless a newer Chinese model is scored.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--as-of", type=date.fromisoformat, help="build as if today were this date (YYYY-MM-DD)")
    TODAY = ap.parse_args().as_of or TODAY
    main()
