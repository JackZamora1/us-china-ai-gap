"""Sanity checks for the automatic refresh. Run after refresh.py and build.py.

Usage:  python scripts/check.py

Compares the freshly built tables with the last committed version (git HEAD)
and exits with an error, so nothing is published, if:
  - a source that had rows in the committed scores now has none
  - the total number of scores fell by more than 15%
  - any area's median lag moved by more than 4 months in one run
"""

from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_SCORE_DROP = 0.15
MAX_MEDIAN_MOVE = 4.0


def committed(path: str) -> str | None:
    out = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else None


def source_counts(text: str) -> Counter:
    # "Epoch AI benchmark data (x.csv)" -> "Epoch AI benchmark data"
    return Counter(r["source"].split(" (")[0] for r in csv.DictReader(io.StringIO(text)))


def main() -> None:
    problems, notes = [], []
    new_scores = (ROOT / "data" / "scores.csv").read_text(encoding="utf-8")
    new_profile = json.loads((ROOT / "data" / "profile.json").read_text(encoding="utf-8"))
    old_scores, old_profile = committed("data/scores.csv"), committed("data/profile.json")
    if old_scores is None or old_profile is None:
        print("no committed version to compare with; checks skipped")
        return

    new, old = source_counts(new_scores), source_counts(old_scores)
    for source, n in old.items():
        if n and not new.get(source):
            problems.append(f"{source}: {n} rows in the committed version, none now")
    total_new, total_old = sum(new.values()), sum(old.values())
    if total_new < total_old * (1 - MAX_SCORE_DROP):
        problems.append(f"total scores fell from {total_old} to {total_new} (more than {MAX_SCORE_DROP:.0%})")

    for variant, areas in json.loads(old_profile)["medians"].items():
        for area, before in areas.items():
            after = new_profile["medians"].get(variant, {}).get(area)
            if before is None or after is None:
                if before != after:
                    notes.append(f"{area} ({variant}): {before} -> {after} (an area gained or lost its last counted benchmark)")
                continue
            if abs(after - before) > MAX_MEDIAN_MOVE:
                problems.append(f"{area} ({variant}): median moved from {before} to {after} months")

    print(f"scores: {total_old} committed, {total_new} now")
    for n in notes:
        print("note:", n)
    if problems:
        print("\nSANITY CHECK FAILED; nothing will be published:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("sanity checks passed")


if __name__ == "__main__":
    main()
