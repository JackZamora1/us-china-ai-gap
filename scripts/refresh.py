"""Pull every automated source and rebuild the data tables.

Usage:  python scripts/refresh.py            (then: python build.py)
        AA_API_KEY=... python scripts/refresh.py   to include Artificial Analysis

Sources: Epoch benchmark_data.zip, the Arena leaderboard dataset on Hugging
Face, the Artificial Analysis API (optional), and METR's time-horizon file.
Raw copies go to data/raw/YYYY-MM-DD/ so a past build can be reproduced.
Writes data/inventory.csv, models.csv, scores.csv and benchmarks.csv.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import gap  # noqa: E402

DATA = ROOT / "data"
TODAY = date.today()
RAW = DATA / "raw" / TODAY.isoformat()

EPOCH_ZIP = "https://epoch.ai/data/benchmark_data.zip"
EPOCH_MODELS_DB = "https://epoch.ai/data/all_ai_models.csv"
ARENA_REPO = "https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset"
AA_API = "https://artificialanalysis.ai/api/v2/data/llms/models"
METR_YAML = "https://metr.org/assets/benchmark_results_1_1.yaml"

DOMAINS = [
    "Overall", "Agentic and real-world work", "Coding", "Frontier reasoning and science",
    "Research math", "Knowledge and hallucination", "Long context", "Multimodal",
    "Cyber and security", "Puzzles and games",
]
AGENT, CODE, SCI, MATH, KNOW, LONG, MULTI, CYBER, GAMES = DOMAINS[1:]

# status: "" = judged by the coverage and saturation rules; "saturated" = on the
# owner's saturated list (history only); "historical" = closed or superseded series.
# src_type is the default for rows that carry no source of their own.
LEADERBOARD = "Epoch says it takes these from the benchmark's public leaderboard"
EPOCH_RUN = "Run by Epoch AI"
EPOCH = [
    # id, name, domain, file, score column, CI spec, default source type, basis, status, history_until, note
    ("gpqa_diamond", "GPQA Diamond", SCI, "gpqa_diamond.csv", None, ("se", "stderr"), "independent", EPOCH_RUN, "saturated", None, ""),
    ("frontiermath_t13", "FrontierMath Tiers 1-3 (v2)", MATH, "frontiermath_tiers_1_3_v2.csv", None, ("se", "stderr"), "independent", EPOCH_RUN, "", None, ""),
    ("frontiermath_t4", "FrontierMath Tier 4 (v2)", MATH, "frontiermath_tier_4_v2.csv", None, ("se", "stderr"), "independent", EPOCH_RUN, "", None, ""),
    ("frontiermath_t13_v1", "FrontierMath Tiers 1-3 (2025 set)", MATH, "frontiermath.csv", None, ("se", "stderr"), "independent", EPOCH_RUN, "historical", "2026-06-12", "Superseded by the v2 set on 2026-06-12"),
    ("frontiermath_t4_v1", "FrontierMath Tier 4 (2025 set)", MATH, "frontiermath_tier_4.csv", None, ("se", "stderr"), "independent", EPOCH_RUN, "historical", "2026-06-12", "Superseded by the v2 set on 2026-06-12"),
    ("math_level_5", "MATH Level 5", MATH, "math_level_5.csv", None, ("se", "stderr"), "independent", EPOCH_RUN, "saturated", None, ""),
    ("otis_mock_aime", "OTIS Mock AIME 2024-2025", MATH, "otis_mock_aime_2024_2025.csv", None, ("se", "stderr"), "independent", EPOCH_RUN, "saturated", None, ""),
    ("proofbench", "ProofBench", MATH, "proofbench_external.csv", "Accuracy", ("se", "Accuracy Standard Error"), "independent", "Vals AI leaderboard (Source column)", "", None, ""),
    ("swe_bench_verified", "SWE-bench Verified", CODE, "swe_bench_verified.csv", None, ("se", "stderr"), "independent", EPOCH_RUN, "saturated", None, ""),
    ("frontiercode", "FrontierCode", CODE, "frontiercode_external.csv", "Main score", None, "independent", "Cognition's leaderboard (Source column)", "", None, ""),
    ("deepswe", "DeepSWE", CODE, "deepswe_external.csv", "Pass@1", ("half", "95% CI half-width"), "independent", "Datacurve leaderboard (Source column)", "", None, ""),
    ("frontierswe", "FrontierSWE", CODE, "frontierswe_external.csv", "Score", None, "independent", "FrontierSWE leaderboard (Source column)", "", None, ""),
    ("terminal_bench_2", "Terminal-Bench 2.0", CODE, "terminalbench_external.csv", "Accuracy mean", ("se", "Accuracy SE"), "independent", "tbench.ai leaderboard; rows where the agent was built by the model's own developer are marked self-reported", "", None, ""),
    ("ale_bench", "ALE-Bench", CODE, "ale_bench_external.csv", "Performance", None, "independent", LEADERBOARD, "", None, "Algorithm-engineering contests; score has no ceiling"),
    ("weirdml", "WeirdML", CODE, "weirdml_external.csv", "Accuracy", ("se", "Accuracy SE"), "independent", "WeirdML leaderboard (Source column)", "", None, "Machine-learning coding tasks"),
    ("cursorbench", "CursorBench", CODE, "cursorbench_external.csv", "Score", None, "independent", "Cursor's leaderboard (Source column)", "", None, ""),
    ("aider_polyglot", "Aider Polyglot", CODE, "aider_polyglot_external.csv", "Percent correct", None, "independent", "Aider leaderboard (Source column)", "", None, ""),
    ("gso", "GSO-Bench", CODE, "gso_external.csv", "Score OPT@1", None, "independent", "GSO leaderboard (Source column)", "", None, ""),
    ("apex_agents", "APEX-Agents", AGENT, "apex_agents_external.csv", "Pass@1 score", ("se", "Pass@1 Standard Error"), "independent", "Run by Mercor, the benchmark's maker, at maximum reasoning effort for every model (mercor.com/apex/methodology)", "", None, ""),
    ("vending_bench_2", "Vending-Bench 2", AGENT, "vending_bench_2_external.csv", "Score", None, "independent", LEADERBOARD, "", None, "Score is money made; no ceiling"),
    ("osworld_2", "OSWorld 2.0", AGENT, "osworld_2_external.csv", "Binary accuracy", None, "independent", "OSWorld leaderboard (Source column)", "", None, ""),
    ("osworld", "OSWorld", AGENT, "os_world_external.csv", "Score", None, "independent", "OSWorld website (Source column)", "", None, ""),
    ("posttrainbench", "PostTrainBench", AGENT, "posttrainbench_external.csv", "Average (%)", None, "unknown", "No source given in Epoch's file", "", None, ""),
    ("the_agent_company", "TheAgentCompany", AGENT, "the_agent_company_external.csv", "% Resolved", None, "independent", "TheAgentCompany leaderboard (Source column)", "", None, ""),
    ("gdpval", "GDPval", AGENT, "gdpval_external.csv", "Win Rate (%)", None, "unknown", "No source given in Epoch's file", "", None, ""),
    ("rli", "Remote Labor Index", AGENT, "rli_external.csv", "Score", None, "unknown", "No source given in Epoch's file", "", None, ""),
    ("critpt", "CritPt", SCI, "critpt_external.csv", "Accuracy", None, "independent", "Epoch says it takes these from the public CritPt leaderboard hosted by Artificial Analysis", "", None, "Research-level physics"),
    ("simplebench", "SimpleBench", SCI, "simplebench_external.csv", "Score (AVG@5)", None, "independent", "SimpleBench leaderboard (Source column)", "", None, ""),
    ("lmca", "LMCA (conceptual argumentation)", SCI, "lmca_external.csv", "Score", ("half", "Score 95% CI (±)"), "unknown", "Built by Redwood Research with Anthropic; neither the site nor the announcement says who runs the evaluations", "", None, "Language Model Conceptual Argumentation: models rate arguments on decision theory, philosophy and AI safety and are scored against expert ratings"),
    ("simpleqa_verified", "SimpleQA Verified", KNOW, "simpleqa_verified.csv", None, ("se", "stderr"), "independent", EPOCH_RUN, "", None, ""),
    ("mmlu", "MMLU", KNOW, "mmlu_external.csv", "EM", None, "unknown", "Mixed: HELM runs and developers' own reports", "saturated", None, ""),
    ("gdp_pdf", "GDP.pdf", LONG, "gdp_pdf_external.csv", "GDP.pdf score", None, "independent", "Surge AI leaderboard (Source column)", "", None, "Long professional documents"),
    ("fiction_livebench", "Fiction.LiveBench (120k tokens)", LONG, "fictionlivebench_external.csv", "120k token score", None, "independent", "Fiction.live leaderboard (Source column)", "", None, ""),
    ("furniture_assembly", "Furniture Assembly", MULTI, "furniture_assembly.csv", None, ("se", "stderr"), "independent", EPOCH_RUN, "", None, "Spatial reasoning from a photo of part-built furniture and its PDF assembly manual"),
    ("video_mme", "Video-MME (no subtitles)", MULTI, "video_mme_external.csv", "Overall (no subtitles)", None, "independent", "Video-MME leaderboard (Source column)", "", None, ""),
    ("exploitbench", "ExploitBench", CYBER, "exploitbench_external.csv", "Mean capability", None, "independent", LEADERBOARD, "", None, "Software exploitation ladder (CMU)"),
    ("cybench", "Cybench", CYBER, "cybench_external.csv", "Unguided % Solved", None, "independent", "Cybench leaderboard; system-card rows are marked self-reported", "", None, ""),
    ("chess_puzzles", "Chess Puzzles", GAMES, "chess_puzzles.csv", None, ("se", "stderr"), "independent", EPOCH_RUN, "", None, ""),
    ("mystery_game_puzzles", "Mystery Game Puzzles", GAMES, "mystery_game_puzzles.csv", None, ("se", "stderr"), "independent", EPOCH_RUN, "", None, ""),
    ("arc_agi", "ARC-AGI-1", GAMES, "arc_agi_external.csv", "Score", None, "independent", "ARC Prize leaderboard (Source column)", "saturated", None, ""),
    ("arc_agi_2", "ARC-AGI-2", GAMES, "arc_agi_2_external.csv", "Score", None, "unknown", "No source given in Epoch's file", "saturated", None, ""),
    ("balrog", "BALROG", GAMES, "balrog_external.csv", "Average progress", None, "independent", "BALROG leaderboard (Source column)", "", None, ""),
    ("enigma_eval", "EnigmaEval", GAMES, "enigma_eval_external.csv", "Accuracy", ("bounds", "CI Lower Bound", "CI Upper Bound"), "independent", "Scale AI leaderboard (Source column)", "", None, ""),
]
# Why an Epoch file with usable Chinese coverage was still left out.
EPOCH_SKIPPED = {
    "scicode_external.csv": "Copy of Artificial Analysis data; pulled from their API instead",
    "webdev_arena_external.csv": "Copy of Arena data; pulled from the Arena dataset instead",
    "hle_external.csv": "Only 3 Chinese models; the Artificial Analysis API covers HLE far better",
    "metr_time_horizons_external.csv": "Used only to add Chinese models to the METR historical series",
    "dtbench_external.csv": "Decision-theory multiple choice from the same Conceptual Reasoning Index as LMCA; dropped so one project is not counted twice",
    "ebr_bench.csv": "Could not confirm what it measures",
    "gbaeval_external.csv": "Could not confirm what it measures",
    "surface_evolver_bench_external.csv": "Could not confirm what it measures; both countries already at the same top score",
    "forecastbench_external.csv": "Forecasting is outside the domain list",
    "btf3_external.csv": "Forecasting is outside the domain list",
    "cl_bench_external.csv": "Latest Chinese score is older than 6 months",
    "cl_bench_life_external.csv": "Latest Chinese score is older than 6 months",
    "weirdml_v3_external.csv": "Only 2 Chinese models so far",
    "blueprint_bench_2_external.csv": "Only 2 Chinese models so far",
    "live_bench_external.csv": "No Chinese model in the last 12 months",
}
SELF_REPORT = re.compile(r"system card|model card|technical report|annou|release notes|blog", re.I)

ARENA = [
    # id, name, domain, subset, value column, note
    ("arena_text", "Arena text (style-controlled)", "Overall", "text_style_control", "rating", ""),
    ("arena_agent", "Arena agent", AGENT, "agent", "score", "Board started 2026-06-04; score definition not documented in the dataset"),
    ("arena_webdev", "Arena WebDev", CODE, "webdev", "rating", "No style-controlled variant"),
    ("arena_text_factuality", "Arena text factuality", KNOW, "text_factuality", "rating", "Board started 2026-07-14"),
    ("arena_vision", "Arena vision (style-controlled)", MULTI, "vision_style_control", "rating", ""),
    ("arena_document", "Arena document (style-controlled)", MULTI, "document_style_control", "rating", "Board started 2026-03-03"),
]
ARENA_DATES_ONLY = ["text"]  # longest history: used for first-appearance dates and the Stanford comparison
ARENA_NOTE = "Human preference votes, not a capability test"

AA = [
    # API field, id, name, domain, ceiling, status, note
    ("artificial_analysis_intelligence_index", "aa_index", "AA Intelligence Index", "Overall", None, "", "The API does not say which older scores are estimates; the website marks most pre-2026 models as estimated"),
    ("hle", "aa_hle", "Humanity's Last Exam (AA)", SCI, 1.0, "", ""),
    ("scicode", "aa_scicode", "SciCode (AA)", SCI, 1.0, "", "Scientific coding"),
    ("terminalbench_v4_0", "aa_terminalbench_4", "Terminal-Bench 4.0 (AA)", CODE, 1.0, "", ""),
    ("livecodebench", "aa_livecodebench", "LiveCodeBench (AA)", CODE, 1.0, "saturated", ""),
    ("tau2", "aa_tau2", "tau2-bench (AA)", AGENT, 1.0, "", "Tool-use customer-service tasks"),
    ("lcr", "aa_lcr", "AA-LCR long-context reasoning", LONG, 1.0, "", ""),
    ("mmlu_pro", "aa_mmlu_pro", "MMLU-Pro (AA)", KNOW, 1.0, "", ""),
]
METR_ID = "metr_horizon"

MODEL_COLS = ["name", "lab", "country", "release_date", "weights", "training_compute_flop",
              "release_url", "aliases", "date_source", "flag", "notes", "added_by"]
SCORE_COLS = ["model", "benchmark", "domain", "score", "ci_low", "ci_high", "source",
              "source_type", "source_url", "retrieved_date"]


# ---------------------------------------------------------------- helpers

def fetch(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.read()


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def strip_parens(name: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", str(name)).strip()


DATE_STAMP = re.compile(r"[-_ ]?(20\d{2})[-_]?(\d{2})[-_]?(\d{2})")
STAGE = re.compile(r"[-_ ](preview|latest|exp)$", re.I)
EFFORT = re.compile(r"[-_ ](x?high|max|low|medium|minimal|none|thinking|reasoning|nothinking|\d+k|\d{4})$", re.I)


def name_keys(name: str, loose: bool = True) -> list[str]:
    """Match keys from strictest to loosest: exact, without brackets, without
    date stamps and preview tags; then (loose only) with trailing effort tags
    or four-digit build stamps peeled off. New models register the strict keys;
    lookups also try the loose ones."""
    keys, base = [norm(name)], strip_parens(name)
    keys.append(norm(base))
    base = DATE_STAMP.sub("", base)
    keys.append(norm(base))
    while STAGE.search(base):
        base = STAGE.sub("", base)
        keys.append(norm(base))
    while loose and (EFFORT.search(base) or STAGE.search(base)):
        base = STAGE.sub("", EFFORT.sub("", base))
        keys.append(norm(base))
    return list(dict.fromkeys(k for k in keys if k))


def country_code(value) -> str:
    if not isinstance(value, str) or not value.strip():
        return "Unknown"
    return {"United States of America": "US", "China": "China"}.get(value.strip(), "Other")


def weights_code(access) -> str:
    if not isinstance(access, str):
        return "unknown"
    return "open" if access.startswith("Open weights") else "closed"


class Registry:
    """One row per model, with every name each source uses for it."""

    def __init__(self, labs: pd.DataFrame):
        self.models: dict[str, dict] = {}
        self.index: dict[str, str] = {}
        self.lab_country, self.lab_name = {}, {}
        for r in labs.itertuples():
            for alias in [r.lab] + [a for a in str(r.aliases).split("|") if a and a != "nan"]:
                self.lab_country[alias.lower()] = r.country
                self.lab_name[alias.lower()] = r.lab
        self.unmapped_labs: set[str] = set()

    def lab(self, org: str) -> tuple[str, str]:
        key = str(org).strip().lower()
        if key in self.lab_country:
            return self.lab_name[key], self.lab_country[key]
        if key and key != "nan":
            self.unmapped_labs.add(str(org))
        return str(org) if key and key != "nan" else "", "Unknown"

    def add(self, name: str, keys: list[str], **fields) -> str:
        self.models[name] = {"name": name, "aliases": set(), "flag": "", "notes": "", "added_by": "refresh",
                             "training_compute_flop": "", "release_url": "", **fields}
        for k in keys:
            self.index.setdefault(k, name)
        return name

    def find(self, name: str) -> str | None:
        return next((self.index[k] for k in name_keys(name) if k in self.index), None)

    def alias(self, canonical: str, alias: str) -> None:
        if alias != canonical:
            self.models[canonical]["aliases"].add(alias)


# ---------------------------------------------------------------- Epoch

def load_epoch(reg: Registry) -> tuple[list[dict], list[dict], dict]:
    raw = fetch(EPOCH_ZIP)
    (RAW / "epoch").mkdir(parents=True, exist_ok=True)
    (RAW / "epoch" / "benchmark_data.zip").write_bytes(raw)
    zf = zipfile.ZipFile(io.BytesIO(raw))
    files = {Path(n).name: pd.read_csv(zf.open(n)) for n in zf.namelist()
             if n.endswith(".csv") and not n.startswith("epoch_capabilities_index/")}
    eci = pd.read_csv(zf.open("epoch_capabilities_index/eci_scores.csv"))
    meta = files["benchmark_metadata.csv"]
    by_file = {r.source_file: r for r in meta.itertuples() if isinstance(r.source_file, str)}
    mm = files["model_metadata.csv"].dropna(subset=["model_version"])

    # Models: one per Epoch model group.
    group_of = dict(zip(mm.model_version, mm.model_group))
    for group, g in mm.dropna(subset=["model_group"]).groupby("model_group"):
        first = lambda col: next((v for v in g[col] if isinstance(v, str) and v), "")
        country = country_code(first("country"))
        compute = pd.to_numeric(g.training_compute_flop, errors="coerce").max()
        keys = [norm(group)] + [k for v in g.model_version for k in name_keys(str(v).split("_")[0], loose=False)] \
            + [norm(strip_parens(d)) for d in g.display_name.dropna()]
        reg.add(group, list(dict.fromkeys(keys)), lab=first("organization"), country=country,
                release_date=first("date"), weights=weights_code(first("accessibility") or None),
                training_compute_flop="" if pd.isna(compute) else f"{compute:.3g}",
                date_source="Epoch model_metadata")
        reg.models[group]["aliases"].update(str(v) for v in g.model_version)
        if "," in first("country"):
            reg.models[group]["flag"] = "country mixed"
            reg.models[group]["notes"] = "Epoch lists countries: " + ", ".join(sorted(c.strip() for c in first("country").split(",")))

    def canonical(version: str, row) -> str | None:
        group = group_of.get(version)
        if isinstance(group, str) and group in reg.models:
            return group
        found = reg.find(str(version).split("_")[0])
        if found:
            return found
        if not isinstance(row.get("Release date"), str):
            return None
        name = str(version).split("_")[0]
        reg.add(name, name_keys(name, loose=False), lab=row.get("Organization") if isinstance(row.get("Organization"), str) else "",
                country=country_code(row.get("Country")), release_date=row["Release date"], weights="unknown",
                date_source="Epoch benchmark file", flag="not in Epoch model list",
                notes="Appears in a benchmark file but not in Epoch's model metadata")
        return name

    scores, inventory = [], []
    configured = {c[3]: c for c in EPOCH}
    for fname, df in sorted(files.items()):
        if "metadata" in fname:
            continue
        cfg, m = configured.get(fname), by_file.get(fname)
        col = (cfg[4] if cfg and cfg[4] else None) or (m.score_column if m is not None else None)
        if col not in df.columns:  # files Epoch ships without a metadata row
            col = next((c for c in ("Score", "Accuracy", "Overall score", "Best score (across scorers)",
                                    "Performance", "Global average", "Arena Score", "Pooled score",
                                    "GDP.pdf score", "Overall (no subtitles)") if c in df.columns), None)
        if col is None:
            continue
        d = df.dropna(subset=["Model version"]).copy()
        d["s"] = pd.to_numeric(d[col], errors="coerce")
        d = d.dropna(subset=["s"])
        default_type = cfg[6] if cfg else ("independent" if not fname.endswith("_external.csv") else "unknown")
        rows = []
        for _, r in d.iterrows():
            name = canonical(r["Model version"], r)
            if name is None:
                continue
            lo = hi = None
            spec = cfg[5] if cfg else None
            if spec and spec[0] in ("se", "half") and spec[1] in d.columns and pd.notna(r[spec[1]]):
                half = float(r[spec[1]]) * (1.96 if spec[0] == "se" else 1.0)
                lo, hi = r.s - half, r.s + half
            elif spec and spec[0] == "bounds" and pd.notna(r.get(spec[1])) and pd.notna(r.get(spec[2])):
                lo, hi = float(r[spec[1]]), float(r[spec[2]])
            source = r.get("Source") if isinstance(r.get("Source"), str) else ""
            stype = "self_reported" if SELF_REPORT.search(source) else default_type
            if fname == "terminalbench_external.csv" and isinstance(r.get("Agent Org"), str) \
                    and r["Agent Org"].strip().lower() == str(r.get("Model Org")).strip().lower():
                stype = "self_reported"
            link = next((r[c] for c in ("Source link", "Source Link", "Source link (site from table)", "Source")
                         if isinstance(r.get(c), str) and r[c].startswith("http")), EPOCH_ZIP)
            rows.append({"model": name, "score": float(r.s), "ci_low": lo, "ci_high": hi,
                         "source": f"Epoch AI benchmark data ({fname})", "source_type": stype, "source_url": link})
        inv = pd.DataFrame(rows)
        if inv.empty:
            continue
        inv["country"] = inv.model.map(lambda n: reg.models[n]["country"])
        inv["day"] = pd.to_datetime(inv.model.map(lambda n: reg.models[n]["release_date"]), errors="coerce")
        scale = float(m.scale) if m is not None and pd.notna(m.scale) else 1.0
        ceiling = float(m.score_ceiling) / scale if m is not None and pd.notna(m.score_ceiling) and m.in_eci else \
            (float(m.score_ceiling) / scale if m is not None and pd.notna(m.score_ceiling) and inv.score.max() <= 1.0 else None)
        if cfg and cfg[0] in ("ale_bench", "vending_bench_2"):
            ceiling = None
        inventory.append(inventory_row(cfg[0] if cfg else "", m.benchmark if m is not None else fname, "Epoch", fname, inv, ceiling,
                                       cfg[2] if cfg else "", "" if cfg else EPOCH_SKIPPED.get(fname, "")))
        if cfg:
            for row in rows:
                scores.append({**row, "benchmark": cfg[0], "domain": cfg[2]})
            BENCH[cfg[0]] = {"name": cfg[1], "domain": cfg[2], "source": "Epoch AI", "kind": "capability",
                             "ceiling": ceiling, "status": cfg[8], "history_until": cfg[9] or "",
                             "notes": cfg[10], "source_basis": cfg[7],
                             "source_url": "https://epoch.ai/benchmarks"}

    # ECI itself.
    for r in eci.itertuples():
        if r.Model not in reg.models:
            continue
        scores.append({"model": r.Model, "benchmark": "eci", "domain": "Overall", "score": r.eci,
                       "ci_low": r.eci_ci_low, "ci_high": r.eci_ci_high,
                       "source": "Epoch AI benchmark data (eci_scores.csv)", "source_type": "independent",
                       "source_url": "https://epoch.ai/benchmarks/eci"})
    BENCH["eci"] = {"name": "Epoch Capabilities Index", "domain": "Overall", "source": "Epoch AI", "kind": "capability",
                    "ceiling": None, "status": "", "history_until": "", "source_basis": "Composite fitted by Epoch AI",
                    "notes": "90% confidence intervals; two anchor models have none", "source_url": "https://epoch.ai/benchmarks/eci"}
    e = pd.DataFrame([s for s in scores if s["benchmark"] == "eci"])
    e["country"] = e.model.map(lambda n: reg.models[n]["country"])
    e["day"] = pd.to_datetime(e.model.map(lambda n: reg.models[n]["release_date"]), errors="coerce")
    inventory.append(inventory_row("eci", "Epoch Capabilities Index", "Epoch", "eci_scores.csv", e, None, "Overall", ""))
    return scores, inventory, files


def inventory_row(bench_id, name, source, origin, df, ceiling, domain, reason) -> dict:
    us, cn = df[df.country == "US"], df[df.country == "China"]
    year_ago = pd.Timestamp(TODAY) - pd.DateOffset(months=12)
    top = df.score.max()
    recent = cn[cn.day >= year_ago].model.nunique()
    if not bench_id and not reason:
        reason = "No Chinese model in the last 12 months" if recent == 0 else "Fewer than 3 Chinese models in the last 12 months" if recent < 3 else "Not selected"
    return {
        "benchmark": name, "source": source, "file_or_field": origin,
        "us_models": us.model.nunique(), "cn_models": cn.model.nunique(),
        "cn_models_last_12m": cn[cn.day >= year_ago].model.nunique(),
        "latest_cn_score_date": "" if cn.day.dropna().empty else cn.day.max().date().isoformat(),
        "latest_us_score_date": "" if us.day.dropna().empty else us.day.max().date().isoformat(),
        "us_top": round(us.score.max(), 4) if len(us) else "", "cn_top": round(cn.score.max(), 4) if len(cn) else "",
        "ceiling": "" if ceiling is None else ceiling,
        "top_vs_ceiling": "" if not ceiling else round(top / ceiling, 3),
        "source_types": "; ".join(f"{k} {v}" for k, v in df.source_type.value_counts().items()),
        "selected_as": bench_id, "domain": domain, "reason_if_not_selected": reason,
    }


# ---------------------------------------------------------------- Artificial Analysis

def load_aa(reg: Registry) -> tuple[list[dict], list[dict]]:
    key = os.environ.get("AA_API_KEY")
    if not key:
        print("AA_API_KEY not set: skipping Artificial Analysis")
        return [], []
    body = fetch(AA_API, {"x-api-key": key})
    (RAW / "aa").mkdir(parents=True, exist_ok=True)
    (RAW / "aa" / "llms_models.json").write_bytes(body)
    data = json.loads(body)["data"]
    wanted = {a[0]: a for a in AA}
    best: dict[tuple[str, str], float] = {}
    fields: dict[str, list[dict]] = {}
    dropped_zeros: list[tuple[str, str]] = []
    for m in data:
        name = reg.find(m["name"])
        if name is None:
            lab, country = reg.lab(m["model_creator"]["name"])
            base = strip_parens(m["name"])
            name = reg.add(base, name_keys(m["name"], loose=False), lab=lab, country=country, release_date=m.get("release_date") or "",
                           weights="unknown", date_source="Artificial Analysis API")
        reg.alias(name, m["name"])
        for field, value in (m.get("evaluations") or {}).items():
            if value is None:
                continue
            # An exact zero on a 0-to-1 evaluation is almost always a run that could not
            # complete (for example, no tool calling), so it is not treated as a score.
            if value == 0 and field in wanted and wanted[field][4]:
                dropped_zeros.append((m["name"], field))
                continue
            fields.setdefault(field, []).append({"model": name, "score": float(value), "source_type": "independent"})
            if field in wanted and value > best.get((name, field), float("-inf")):
                best[(name, field)] = float(value)
    scores = [{"model": name, "benchmark": wanted[f][1], "domain": wanted[f][3], "score": v, "ci_low": None, "ci_high": None,
               "source": f"Artificial Analysis API ({f})", "source_type": "independent",
               "source_url": "https://artificialanalysis.ai/"} for (name, f), v in best.items()]
    for a in AA:
        BENCH[a[1]] = {"name": a[2], "domain": a[3], "source": "Artificial Analysis", "kind": "capability", "ceiling": a[4],
                       "status": a[5], "history_until": "", "notes": a[6], "source_basis": "Run by Artificial Analysis",
                       "source_url": "https://artificialanalysis.ai/"}
    if dropped_zeros:
        print(f"Artificial Analysis: ignored {len(dropped_zeros)} exact-zero scores (likely failed runs)")
    inventory = []
    for field, rows in sorted(fields.items()):
        df = pd.DataFrame(rows).groupby("model", as_index=False).agg(score=("score", "max"), source_type=("source_type", "first"))
        df["country"] = df.model.map(lambda n: reg.models[n]["country"])
        df["day"] = pd.to_datetime(df.model.map(lambda n: reg.models[n]["release_date"]), errors="coerce")
        cfg = wanted.get(field)
        ceiling = 1.0 if df.score.max() <= 1.0 else None
        inventory.append(inventory_row(cfg[1] if cfg else "", cfg[2] if cfg else field, "Artificial Analysis API", field, df, ceiling,
                                       cfg[3] if cfg else "", "" if cfg else "Not needed: older or saturated evaluation, or covered by another source"))
    return scores, inventory


# ---------------------------------------------------------------- Arena

def load_arena(reg: Registry) -> tuple[list[dict], list[dict]]:
    out_dir = RAW / "arena"
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = {}
    for subset in dict.fromkeys(ARENA_DATES_ONLY + [a[3] for a in ARENA]):
        df = pd.read_parquet(io.BytesIO(fetch(f"{ARENA_REPO}/resolve/main/{subset}/full-00000-of-00001.parquet")))
        if "category" in df.columns and (df.category == "overall").any():
            df = df[df.category == "overall"]
        df.to_parquet(out_dir / f"{subset}_overall.parquet", index=False)  # the full files are ~120 MB, so only this slice is kept
        frames[subset] = df

    everything = pd.concat([f[["model_name", "organization", "license", "leaderboard_publish_date"]] for f in frames.values()])
    first_seen = everything.groupby("model_name").leaderboard_publish_date.min()
    info = everything.sort_values("leaderboard_publish_date").groupby("model_name").last()
    # Some boards leave the organisation blank for a model that others label; use its usual label.
    named = everything[everything.organization.fillna("").str.strip() != ""]
    usual_org = named.groupby("model_name").organization.agg(lambda o: o.mode().iat[0])
    info["organization"] = [usual_org.get(name, org) for name, org in zip(info.index, info.organization)]

    def resolve(model_name: str) -> str:
        name = reg.find(model_name)
        if name is None:
            lab, country = reg.lab(info.at[model_name, "organization"])
            name = reg.add(strip_parens(model_name), name_keys(model_name, loose=False), lab=lab, country=country,
                           release_date=first_seen[model_name], weights="unknown", date_source="First Arena appearance",
                           flag="release date approximate", notes="Dated by first appearance on an Arena leaderboard")
        reg.alias(name, model_name)
        if reg.models[name]["weights"] == "unknown" and isinstance(info.at[model_name, "license"], str):
            reg.models[name]["weights"] = "closed" if info.at[model_name, "license"].lower() == "proprietary" else "open"
        return name

    # Top US and Chinese rating on each published text board (not style-controlled),
    # so published "percent gap on Arena" figures can be recomputed.
    tops = []
    for day, board in frames["text"].groupby("leaderboard_publish_date"):
        board = board.assign(country=[reg.lab(usual_org.get(n, o))[1] for n, o in zip(board.model_name, board.organization)])
        row = {"date": day}
        for code, key in (("US", "us"), ("China", "cn")):
            side = board[board.country == code].sort_values("rating")
            if len(side):
                row.update({f"{key}_top": round(side.rating.iloc[-1], 2), f"{key}_model": side.model_name.iloc[-1]})
        tops.append(row)
    pd.DataFrame(tops).to_csv(DATA / "arena_text_tops.csv", index=False)

    scores, inventory = [], []
    for bench_id, label, domain, subset, value, note in ARENA:
        df = frames[subset].sort_values("leaderboard_publish_date").groupby("model_name").last().reset_index()
        lo_col, hi_col = ("rating_lower", "rating_upper") if value == "rating" else ("score_ci_lower", "score_ci_upper")
        rows = []
        for r in df.itertuples():
            v = getattr(r, value)
            if pd.isna(v):
                continue
            lo, hi = getattr(r, lo_col, None), getattr(r, hi_col, None)
            rows.append({"model": resolve(r.model_name), "benchmark": bench_id, "domain": domain, "score": float(v),
                         "ci_low": None if pd.isna(lo) else float(lo), "ci_high": None if pd.isna(hi) else float(hi),
                         "source": f"Arena leaderboard dataset ({subset}, board of {r.leaderboard_publish_date})",
                         "source_type": "independent", "source_url": ARENA_REPO})
        best = pd.DataFrame(rows).sort_values("score").groupby("model", as_index=False).last()
        scores += best.to_dict("records")
        best["country"] = best.model.map(lambda n: reg.models[n]["country"])
        best["day"] = pd.to_datetime(best.model.map(lambda n: reg.models[n]["release_date"]), errors="coerce")
        inventory.append(inventory_row(bench_id, label, "Arena dataset", subset, best, None, domain, ""))
        BENCH[bench_id] = {"name": label, "domain": domain, "source": "Arena", "kind": "preference", "ceiling": None,
                           "status": "", "history_until": "", "notes": "; ".join(n for n in (ARENA_NOTE, note) if n),
                           "source_basis": "Arena's published leaderboards; each model's most recent rating",
                           "source_url": ARENA_REPO}
    return scores, inventory


# ---------------------------------------------------------------- METR

def load_metr(reg: Registry, epoch_files: dict) -> tuple[list[dict], list[dict]]:
    body = fetch(METR_YAML)
    (RAW / "metr").mkdir(parents=True, exist_ok=True)
    (RAW / "metr" / "benchmark_results_1_1.yaml").write_bytes(body)
    rows, seen = [], set()
    for key, r in yaml.safe_load(body)["results"].items():
        name = reg.find(key.replace("_inspect", "").replace("_", "-"))
        h = r["metrics"]["p50_horizon_length"]
        if name is None or h.get("estimate") is None:
            continue
        seen.add(name)
        rows.append({"model": name, "score": float(h["estimate"]), "ci_low": h.get("ci_low"), "ci_high": h.get("ci_high"),
                     "source": "METR time horizons 1.1 (benchmark_results_1_1.yaml)", "source_url": METR_YAML})
    # Epoch's copy carries a few Chinese models METR's own file does not.
    extra = epoch_files["metr_time_horizons_external.csv"]
    for _, r in extra.dropna(subset=["Time horizon"]).iterrows():
        name = reg.find(str(r["Model version"]).split("_")[0])
        if name is None or name in seen:
            continue
        seen.add(name)
        rows.append({"model": name, "score": float(r["Time horizon"]), "ci_low": r.get("CI_low"), "ci_high": r.get("CI_high"),
                     "source": "Epoch AI benchmark data (metr_time_horizons_external.csv)",
                     "source_url": r["Source link"] if isinstance(r.get("Source link"), str) else EPOCH_ZIP})
    scores = [{**r, "benchmark": METR_ID, "domain": AGENT, "source_type": "independent"} for r in rows]
    BENCH[METR_ID] = {"name": "METR time horizon (50%)", "domain": AGENT, "source": "METR", "kind": "capability", "ceiling": None,
                      "status": "historical", "history_until": "2026-05-31", "source_basis": "Run by METR",
                      "notes": "Closed series: METR stopped updating it in May 2026 and it is unreliable above 16 hours. Minutes.",
                      "source_url": "https://metr.org/time-horizons/"}
    df = pd.DataFrame(scores)
    df["country"] = df.model.map(lambda n: reg.models[n]["country"])
    df["day"] = pd.to_datetime(df.model.map(lambda n: reg.models[n]["release_date"]), errors="coerce")
    return scores, [inventory_row(METR_ID, "METR time horizon (50%)", "METR + Epoch copy", "benchmark_results_1_1.yaml", df, None, AGENT, "")]


# ---------------------------------------------------------------- tables

def bench_table(scores: pd.DataFrame, models: pd.DataFrame) -> pd.DataFrame:
    info = models.set_index("name")
    s = scores.join(info[["country", "release_date"]], on="model")
    s["day"] = pd.to_datetime(s.release_date, errors="coerce").dt.date
    s = s.dropna(subset=["day"])
    rows = []
    for bench_id, cfg in BENCH.items():
        out = {"benchmark": bench_id, "name": cfg["name"], "domain": cfg["domain"], "source": cfg["source"],
               "kind": cfg["kind"], "ceiling": "" if cfg["ceiling"] is None else cfg["ceiling"],
               "listed_status": cfg["status"], "history_until": cfg["history_until"]}
        for label, sub in (("", s[s.benchmark == bench_id]),
                           ("_independent", s[(s.benchmark == bench_id) & (s.source_type == "independent")])):
            sides = {c: [gap.Point(r.day, r.score) for r in sub[sub.country == c].itertuples()] for c in ("US", "China")}
            us, cn = gap.records(sides["US"]), gap.records(sides["China"])
            cn_days = [p.day for p in sides["China"]]
            sat = gap.saturated_from(us, cn, cfg["ceiling"])
            status = gap.current_status(us, cn, cn_days, cfg["ceiling"], cfg["status"], TODAY)
            out["eligible" + label] = status
            if not label:
                year_ago = TODAY.replace(year=TODAY.year - 1)
                out.update({"saturated_from": sat.isoformat() if sat else "", "us_models": len({r.model for r in sub[sub.country == "US"].itertuples()}),
                            "cn_models": len(cn_days), "cn_models_last_12m": sum(d > year_ago for d in cn_days),
                            "latest_cn_score_date": max(cn_days).isoformat() if cn_days else ""})
        out.update({"source_type_basis": cfg["source_basis"], "notes": cfg["notes"], "source_url": cfg["source_url"]})
        rows.append(out)
    table = pd.DataFrame(rows)
    table["domain"] = pd.Categorical(table.domain, DOMAINS, ordered=True)
    return table.sort_values(["domain", "benchmark"])


def add_release_urls(reg: Registry) -> None:
    try:
        db = pd.read_csv(io.BytesIO(fetch(EPOCH_MODELS_DB)), low_memory=False)[["Model", "Link"]].dropna().drop_duplicates("Model")
    except Exception as exc:
        print(f"warning: no announcement links ({exc})", file=sys.stderr)
        return
    for name, link in zip(db.Model, db.Link):
        if name in reg.models:
            reg.models[name]["release_url"] = str(link).split(",")[0].strip()


BENCH: dict[str, dict] = {}


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    reg = Registry(pd.read_csv(DATA / "labs.csv"))
    scores, inventory, epoch_files = load_epoch(reg)
    counts = {"Epoch": len(scores)}
    for label, loader in (("Artificial Analysis", load_aa), ("Arena", load_arena)):
        s, inv = loader(reg)
        counts[label] = len(s)
        scores += s
        inventory += inv
    s, inv = load_metr(reg, epoch_files)
    counts["METR"] = len(s)
    scores += s
    inventory += inv
    empty = [k for k, n in counts.items() if n == 0 and not (k == "Artificial Analysis" and not os.environ.get("AA_API_KEY"))]
    if empty:
        sys.exit(f"refresh failed: no rows from {', '.join(empty)}; tables left unchanged")
    print("rows per source:", ", ".join(f"{k} {n}" for k, n in counts.items()))
    add_release_urls(reg)

    models = pd.DataFrame(reg.models.values())
    models["aliases"] = models.aliases.map(lambda a: "|".join(sorted(a)))
    models = models.reindex(columns=MODEL_COLS).fillna("")
    path = DATA / "models.csv"
    if path.exists():  # keep hand-added rows
        old = pd.read_csv(path, dtype=str, keep_default_na=False)
        if "added_by" in old.columns:
            manual = old[old.added_by == "manual"].reindex(columns=MODEL_COLS).fillna("")
            models = pd.concat([models[~models.name.isin(manual.name)], manual], ignore_index=True)
            if len(manual):
                print(f"kept {len(manual)} manual model row(s)")
    models = models.sort_values(["release_date", "name"])

    table = pd.DataFrame(scores)
    table["retrieved_date"] = TODAY.isoformat()
    # One row per model, benchmark and source type: the best score of that type.
    table = table.sort_values("score").groupby(["model", "benchmark", "source_type"], as_index=False).last()
    table = table[table.model.isin(models.name)].reindex(columns=SCORE_COLS)
    path = DATA / "scores.csv"
    if path.exists():
        old = pd.read_csv(path, keep_default_na=False)
        # A score keeps the date it was first retrieved, so a refresh only changes rows whose value changed.
        seen = {(r.model, r.benchmark, r.source_type, round(float(r.score), 9)): r.retrieved_date for r in old.itertuples()}
        table["retrieved_date"] = [seen.get((r.model, r.benchmark, r.source_type, round(float(r.score), 9)), r.retrieved_date)
                                   for r in table.itertuples()]
        manual = old[old.source.str.startswith("manual")] if "source" in old.columns else old.iloc[0:0]
        if len(manual):
            table = pd.concat([table, manual.reindex(columns=SCORE_COLS)], ignore_index=True)
            print(f"kept {len(manual)} manual score row(s)")
    table = table.sort_values(["benchmark", "model", "source_type"])

    models.to_csv(DATA / "models.csv", index=False)
    table.to_csv(DATA / "scores.csv", index=False)
    pd.DataFrame(inventory).sort_values(["source", "cn_models_last_12m"], ascending=[True, False]).to_csv(DATA / "inventory.csv", index=False)
    benches = bench_table(table, models)
    benches.to_csv(DATA / "benchmarks.csv", index=False)

    print(f"models {len(models)}  scores {len(table)}  benchmarks {len(benches)}  raw copies in {RAW.relative_to(ROOT)}")
    print(benches.groupby("eligible", observed=True).size().to_string())
    if reg.unmapped_labs:
        print("labs missing from data/labs.csv (treated as Unknown):", ", ".join(sorted(reg.unmapped_labs)))


if __name__ == "__main__":
    main()
