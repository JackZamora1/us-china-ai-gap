"""Build index.html from the tables in data/.

Usage:  python build.py        (standard library only)

Computes every lag with gap.py as of today, for two views of the data
(independent sources only, and all sources), and writes one self-contained
page with the data inlined, so index.html can be opened directly, emailed,
or hosted anywhere. Rebuild to move "today" forward.

Also writes data/profile.json, a small summary the automatic refresh uses to
check that no area moved implausibly far in one run.
"""

from __future__ import annotations

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
    data = {
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
    for d in domains:
        lapse = (variants["independent"]["profile"][d] or {}).get("lapse")
        if lapse:
            print(f"\nWARNING: {d} loses its last counted benchmark on {lapse['date']} "
                  f"({', '.join(lapse['benchmarks'])}) unless a newer Chinese model is scored.")


if __name__ == "__main__":
    main()
