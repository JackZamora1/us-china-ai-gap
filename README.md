# US–China frontier AI capability gap

A single-page dashboard that shows how far China trails the US in AI, measured in months wherever that is meaningful: by capability area, in AI chip stock and in the best chips each side actually has in use, with the largest disclosed training runs and a comparison of what models cost to use.

**Live page:** https://jackzamora1.github.io/us-china-ai-gap/ (refreshed daily). Or open `index.html` locally.

## Gap profile on 2026-10-13

Lag in months (median across the area's counted benchmarks; range in brackets).

| Area | Independent only | All sources | Benchmarks (independent / all) | Confidence |
|---|---|---|---|---|
| Overall | 7.3 (4.1 to 8.2) | 7.3 | 3 / 3 | OK |
| Agentic and real-world work | 5.0 (1.4 to 7.8) | 5.0 | 4 / 4 | OK |
| Coding | 4.3 (2.7 to 11.0) | 4.3 | 8 / 8 | OK |
| Frontier reasoning and science | 5.7 (4.1 to 10.8) | 7.3 | 4 / 5 | OK |
| Research math | 7.3 (4.1 to 7.3) | 7.3 | 3 / 3 | OK |
| Knowledge and hallucination | 9.0 (8.2 to 9.9) | 9.0 | 2 / 2 | Low: fewer than 3 benchmarks |
| Long context | 1.4 (-2.9 to 5.7) | 1.4 | 2 / 2 | Low: fewer than 3 benchmarks; benchmarks disagree on direction |
| Multimodal | 10.1 (5.9 to 10.6) | 10.1 | 3 / 3 | OK |
| Cyber and security | 7.8 | 7.8 | 1 / 1 | Low: fewer than 3 benchmarks |
| Puzzles and games | 7.9 (5.7 to 10.1) | 7.9 | 2 / 2 | Low: fewer than 3 benchmarks |

Overall is three measures that disagree: 7.3 months on Epoch's Capabilities Index, 4.1 on the Artificial Analysis Intelligence Index and 8.2 on Arena text, which measures human preference.

## Compute and cost on 2026-10-13

| Measure | China against the US | Detail |
|---|---|---|
| AI chip stock (to 2025-12-31) | 13.6 times smaller; at least 21.0 months behind | China 1,155,114 H100e against 15,746,640 for seven US companies. With Epoch's smuggling estimate: 8.7 times, 18.0 months |
| Best chip deployed in China (any designer), 16-bit performance | 36.0 months behind (30.1 to 39.0 across thresholds) | Nvidia H800 (989 TFLOP/s), deployed at scale from Q2 2023; the seven US companies had deployed the H100 by Q4 2022. Measured to 2025-12-31 |
| Best Chinese-designed chip deployed in China, 16-bit performance | 36.0 months behind (30.1 to 39.0) | Huawei Ascend 910C (800 TFLOP/s), from Q4 2024; also matched by the H100 in Q4 2022 |
| Best chip deployed in China (any designer), memory bandwidth | 21.0 months behind (15.0 to 21.0) | Nvidia H20 (4,000 GB/s), from Q1 2024; matched by AMD's MI300X (5,300 GB/s) in Q1 2024 |
| Best Chinese-designed chip deployed in China, memory bandwidth | 36.0 months behind (30.1 to 39.0) | Ascend 910C (3,200 GB/s); matched by the H100 (3,350 GB/s) in Q4 2022 |
| Cheapest model scoring 20+ on the AA index | US price is 2.0 times the Chinese price | Hy3-preview (Reasoning) at $0.1 against Claude Haiku 5.5 (High) at $0.2 per million tokens |
| Cheapest model scoring 30+ on the AA index | US price is 1.1 times the Chinese price | MiMo-V2.6-Flash at $0.175 against Claude Haiku 5.5 (High) at $0.2 per million tokens |
| Cheapest model scoring 40+ on the AA index | US price is 0.8 times the Chinese price | GLM-5.3-Flash at $0.237 against Claude Haiku 5.5 (Max) at $0.2 per million tokens |
| Cheapest model scoring 45+ on the AA index | US price is 3.7 times the Chinese price | MiMo-V2.6-Pro at $0.544 against Muse Spark 1.3 (Max) at $2 per million tokens |

## The site

One static page with six tabs, each with its own link: `#overview`, `#capabilities`, `#compute`, `#cost`, `#policy` and `#methods`. The overview gives one headline per dimension and no single overall number. Each tab shows its "as of" date and sources at the bottom.

## How to read it

- **Lag at date t:** take China's best score among models released by t. Find the earliest US model, released by t, that scored at least that high. The lag is t minus that model's release date.
- **China ahead:** if no US model has reached China's best, the same rule runs in reverse and the lag is negative.
- **Range:** where the trailing country's best score has a confidence interval, the lag is recomputed at its low and high ends.
- **Dates:** a score is dated by its model's release date, not by when the benchmark was run.
- **Area lag:** the median of its counted benchmarks' lags, shown with the minimum, maximum and count.
- **Counted:** a benchmark counts today only if it has at least 3 Chinese models released in the last 12 months and one in the last 6 months, and is not saturated or closed.
- **Saturated:** from the date both countries' best scores are within 5% of the benchmark's ceiling, or if it is on the hand-kept saturated list.
- **History:** the heatmap and history charts apply the same coverage and saturation rules as of each month end.
- **Open and closed weights:** the same rule between three groups (China open, US open, US closed). Models with unknown weights are left out.

One implementation, in `gap.py`, produces every number on the page, including the compute lags below.

### Compute

All compute data is from Epoch AI (CC BY 4.0).

| Source | What it measures | Table |
|---|---|---|
| AI chip owners (`ai_chip_owners.zip`, file `cumulative_by_designer.csv`) | Cumulative AI chips acquired since Q1 2022 by owner and chip designer, in H100-equivalents, units and power, with 5th and 95th percentiles | `data/compute_stock.csv` |
| AI chip owners (same zip, file `cumulative_by_chip_type.csv`) | The same, split by chip type (H100/H200, H20, Ascend 910C, TPU v7 and so on), in units | `data/chip_deployment.csv` |
| ML hardware (`ml_hardware.csv`) | Specifications of 178 accelerators, including 50 from Chinese designers: 16-bit and 8-bit performance, memory bandwidth and capacity | `data/chips.csv` |
| Model training compute | Epoch's estimate of each model's training compute, already in `data/models.csv` | `data/models.csv` |

- **Chip stock.** The rule is applied to cumulative H100-equivalents at each quarter end, up to Epoch's last complete quarter (quarters Epoch marks incomplete are dropped). The lag therefore moves in three-month steps. The page also shows the ratio, because a lag of nearly two years on an exponential curve is easier to read as "13.6 times smaller".
- **What "China" is.** Epoch's bucket for chips it infers were sold to companies based in China (A100, A800, H800, H20, MI308X) plus Chinese-designed chips (Huawei Ascend 910B and 910C, Cambricon Siyuan 590). It does not mean government ownership.
- **Smuggling.** The file has a separate owner, "China (smuggled)", from Q1 2024: Epoch's own model of diverted and resold Nvidia chips, which Epoch calls speculative. The page leaves it out by default and adds it with a toggle.
- **No US total.** The owners are companies. "Seven US companies" is the sum of the ones Epoch names (Amazon, CoreWeave, Google, Meta, Microsoft, Oracle, xAI), all headquartered in the US. It understates the US, so the lag against it is a minimum. "Everything outside China" adds Epoch's "Other" owner, which mixes smaller US buyers with buyers elsewhere, so it is not called "US".
- **Best chip deployed at scale.** This replaces the old spec-sheet headline. A chip type counts as deployed for an owner group (seven US companies; China, any designer; China, Chinese-designed) from the first complete quarter end at which the group's cumulative units pass 10,000 and the chip has been released. Each quarter, the group's best chip is the highest per-chip figure among its deployed types, and the months-behind rule is applied to that, measured to Epoch's last complete quarter (2025-12-31). "China, any designer" includes Nvidia's China-specific H800 and H20 and AMD's MI308X, so it shows what export controls let through. "Chinese-designed" is Huawei and Cambricon. `build.py` writes the result to `data/deployed_chips.csv`.
- **What it shows.** On 16-bit performance, both China lines are 36.0 months behind: China's best deployed chip is the H800 (989 TFLOP/s) and its best Chinese-designed chip is the Ascend 910C (800 TFLOP/s), and the seven US companies had the H100 (989 TFLOP/s) in volume by Q4 2022. They have since deployed the B200, B300, TPU v7 and MI355X (2,250 to 2,517 TFLOP/s). On memory bandwidth, China's best deployed chip is the H20 (4,000 GB/s), 21.0 months behind; the 910C (3,200 GB/s) is 36.0 months behind; the US best is 8,000 GB/s.
- **Threshold sensitivity.** At 1,000, 5,000, 10,000, 25,000, 50,000 and 100,000 units, the 16-bit lag is 39.0, 36.0, 36.0, 33.1, 33.1 and 30.1 months for both China lines. Bandwidth for any designer is 21.0, 21.0, 21.0, 21.0, 18.0 and 15.0. The movement comes almost entirely from when the US H100 and MI300X pass the threshold, so the conclusion (about three years on compute, under two years on bandwidth for chips China buys) does not depend on the choice. The page shows this table.
- **Memory bandwidth** is shown as a toggle on the same chart, because training and serving large models is usually limited by moving data to and from memory, which depends mostly on access to high-bandwidth memory (HBM), more than by peak arithmetic.
- **Chip type map.** The owner data's chip types are matched to rows of `chips.csv` by `data/chip_type_map.csv`, kept by hand. Every type in today's data maps. Flagged: H100/H200 (one combined type; the H100's figures are used), Ascend 910B (variant mix unknown; Epoch's generic row is used), Siyuan 590 (no bandwidth in Epoch's table) and MI308X (Epoch's bandwidth of 10.3 TB/s is double the MI300X it is cut from; left out of the bandwidth view). `build.py` warns if a new chip type has no mapping.
- **System-level scaling.** The page notes under the chip views that per-chip comparisons understate Huawei's approach of linking many chips: its Atlas 900 A3 SuperPoD (sold as CloudMatrix 384) joins up to 384 Ascend 910C chips (Huawei Connect keynote, 2025-09-18), and SemiAnalysis (2025-04-16) estimates about 300 PFLOP/s of dense BF16, almost double Nvidia's GB200 NVL72, at about 4.1 times the power.
- **Chip designs on paper.** The old comparison (best 16-bit performance of any chip released to date, Nvidia against Chinese designers) is kept as the last section of the compute tab, labelled "announced specifications, not deployed chips", and is not on the overview. On it, Biren's BR100 still sets China's line from 2022, although Epoch's chip-owner data shows no Biren chips in China's stock.
- **Huawei roadmap chips.** Epoch's table has no release date for the Ascend 950PR, 950DT, 960 and 970. They are now hand-kept rows in `chips.csv` (`added_by` = `manual`, kept by every refresh), sourced from Huawei's 2025-09-18 keynote. The 950PR is dated 2026-03-31, the end of the quarter Huawei announced; its FP8 figure (1 PFLOPS) is from the keynote, its 1.6 TB/s bandwidth is Epoch's (citing Tom's Hardware) and is flagged, and Huawei published no 16-bit figure, so it is in no 16-bit comparison. It is not in Epoch's owner data, so it is not in the deployed view. The 950DT, 960 and 970 are marked "announced, not released" with their planned quarters and are kept out of every comparison. Eight other Chinese chips still have no release date and are left out of the spec-sheet view.
- **Training compute: largest disclosed run.** The compute tab leads this section with the coverage table, then names the largest disclosed run by country and the first disclosed US run as large as China's largest, each with the disclosure caveat beside it. No months-behind figure is shown for it on the page or in the summary above. On disclosed runs only, a US model passed China's largest (Doubao-pro, 2.5×10²⁵ FLOP) in June 2024; that comparison mostly reflects who discloses.
- **Disclosure bias.** Of ECI-scored models released in 2026, 3 of 46 US models have a compute estimate against 9 of 33 Chinese ones (2025: 12 of 46 against 20 of 23). The US side is limited to models that disclose, so "China achieves more per unit of compute" is suggestive, not proven.
- **No map.** Epoch's data-centre dataset lists 77 US sites and 4 Chinese sites with no coordinates, so a map would show a coverage gap, not a compute gap. It could be added later if coverage improves.

### Cost

Prices come from the Artificial Analysis API response already used for scores: blended price (three parts input to one part output), input price, output price and output speed, per model configuration. `data/prices.csv` holds today's table, joined to `models.csv` for lab and country.

- **The months-behind rule is not applied.** The API gives only today's prices, so there is nothing to look back through. The page says so and compares prices directly.
- **Cheapest model at a level.** For index scores of 20, 30, 40 and 45, the cheapest US and cheapest Chinese configuration that reaches the score, and the ratio.
- **Price frontier.** For each country, the configurations that are cheaper than every configuration scoring at least as high.
- **History starts 2026-10-13.** `data/price_history.csv` logs a row whenever a configuration's price first appears or changes, so the committed file builds a time series from that date.
- **List prices, not costs.** They show what a user pays per token. Some providers price below cost, and models that use more tokens per task cost more than their per-token price suggests.
- **Zero prices are treated as missing.** 264 of 699 configurations have a blended price of zero in the API, which means no list price, not free.
- **Long-context pricing.** Claude Haiku 5.5, the cheapest US model at index scores of 20, 30 and 40, lists $0.10 input and $0.50 output per million tokens for prompts under 100K tokens and charges five times as much above that, so its blended list price understates the cost of long-context use. The cost tab says so under the table (`PRICE_NOTES` in `build.py`).

### Low-confidence areas

An area is low confidence if either holds:

- it has fewer than 3 counted benchmarks, or
- its benchmarks disagree on direction: China is ahead on at least one and behind on at least one.

Low-confidence areas stay on the page but are drawn lighter: a hollow marker and faded bar in the timeline, a dashed chip, and a faded cell in the heatmap, each with a label or tooltip giving the reason. The same test is applied to every past quarter in the heatmap. The headline sentence uses only areas that are not low confidence.

### Published estimates for thin areas

When an area has fewer than 2 counted benchmarks, the page shows the most recent row for that area from `data/assessments.csv` beside it: a dashed bracket on the timeline and a sentence in the area's description, labelled as a published estimate with its publisher, date and what it measures. Today that applies to cyber, where the UK AISI figure compares open-weight models with closed models, not China with the US, and the page says so.

### Benchmarks about to stop counting

`build.py` prints a warning, and the page shows a notice, when every counted benchmark in an area will lose eligibility within 30 days. Today: cyber and security loses ExploitBench on 2026-10-20 unless a newer Chinese model is scored, after which the area has no current figure.

The transition was tested with `python build.py --as-of 2026-10-21`. Cyber then has no counted benchmark in either view; the timeline row reads "No current data" with the UK AISI bracket (4 to 7 months, labelled as open-weight against closed models); the area explorer gives the same sentence and an empty history after the last month that qualified; the heatmap's quarter-to-date cell is blank; the overview lists cyber as "no data"; and the headline, which already excluded cyber as low confidence, is unchanged. No errors in the build or the browser console.

### Before 2025

Every time chart and the heatmap shade 2023 and 2024 and label them "limited Chinese coverage". Epoch's index scored 20 Chinese models released in those two years and all 20 were open-weight. Arena and Artificial Analysis rated another 25, but only four of those were closed (GLM-4, GLM-4-Plus, Yi-Lightning and a Qwen 2.5 Plus build).

I checked whether the 2024 peak (about 18 months on ECI in August 2024) comes from missing data. It does not appear to:

| Month end | ECI | Artificial Analysis index | Arena text |
|---|---|---|---|
| December 2023 | 9.6 | 7.7 | 9.6 |
| June 2024 | 15.6 | 12.6 | 15.6 |
| August 2024 | 17.6 | 14.6 | 17.6 |
| September 2024 | 3.4 | 7.0 | 8.2 |

All three sources show the same shape, including Arena, whose best Chinese model in mid-2024 was the closed GLM-4. On ECI and Arena, no Chinese model had passed the original GPT-4 (March 2023) until Qwen 2.5 in September 2024, so the lag grew by a month each month; Artificial Analysis shows the same against GPT-4's June 2023 version. The caveat that remains: a closed Chinese model that none of the three sources rated could have closed the gap earlier, and this data cannot rule that out.

## View it

Open `index.html` in a browser. It is one self-contained file with the data inlined. Fonts load from Google Fonts and fall back to system fonts offline.

## Refresh by hand

```bash
pip install -r requirements.txt          # once: pandas, pyarrow, pyyaml
export AA_API_KEY=...                    # optional: your Artificial Analysis key
python3 scripts/refresh.py               # pull every source, rebuild the tables
python3 build.py                         # recompute every lag as of today, write index.html
python3 build.py --as-of 2026-10-21      # or as of another date, to test a transition (rebuild without it afterwards)
python3 scripts/check.py                 # optional: compare with the last commit
```

- `scripts/refresh.py` downloads every source and rewrites `inventory.csv`, `models.csv`, `scores.csv`, `benchmarks.csv`, `arena_text_tops.csv`, `compute_stock.csv`, `chip_deployment.csv`, `chips.csv` (keeping hand-added rows), `prices.csv` and `price_history.csv`. It stops without changing anything if a source returns no rows. `python3 scripts/refresh.py --compute-from data/raw/YYYY-MM-DD` rebuilds only the compute tables from a saved download, offline.
- Without `AA_API_KEY` it skips Artificial Analysis and the rest still works, with fewer benchmarks and no cost tab data.
- The key is read from the environment only. It is not written to any file here.
- `build.py` needs only the standard library. All lags are as of the day you run it, so rerun it to move "today" forward. It also writes `data/profile.json`, a small summary of the area medians.
- Edit the page's design in `template.html`. `index.html` is overwritten on each build.

## Automatic refresh

A GitHub Actions workflow (`.github/workflows/refresh.yml`) refreshes and publishes the page every day at 09:17 UTC. It can also be started by hand.

Each run:

1. Installs the requirements and runs `scripts/refresh.py`, then `build.py`.
2. Runs `scripts/check.py`. The run fails, and nothing is committed or published, if:
   - any source returns no rows (or the `AA_API_KEY` secret is missing),
   - the total number of scores is more than 15% below the committed version,
   - any area's median lag moved more than 4 months since the committed version,
   - the chip-owner, chip-type, chip-specification or price table is empty, or
   - China's chip stock changed by more than 50% since the committed version.
3. Commits the processed CSVs (including today's prices and any price changes), `data/profile.json` and `index.html` with the message "Data refresh YYYY-MM-DD", only if something changed. The page changes daily because every lag grows by a day.
4. Deploys `index.html` to GitHub Pages.

An area gaining or losing its last counted benchmark is printed as a note and does not fail the run.

### The Artificial Analysis key

The workflow reads the key from a repository secret named `AA_API_KEY`. It is never stored in a file. To add or replace it:

- **In the browser:** open the repository on GitHub, then Settings > Secrets and variables > Actions > New repository secret. Name it `AA_API_KEY`, paste the key as the value, and save.
- **From a terminal:** run `gh secret set AA_API_KEY` in this folder and paste the key when prompted.

### Run it by hand

- **On GitHub:** Actions > Refresh and publish > Run workflow.
- **From a terminal:** `gh workflow run refresh.yml`, then `gh run watch` to follow it.

### When a run fails

GitHub emails the repository owner when a scheduled run fails. The published page stays at the last good version.

1. Open the failed run (Actions tab, or `gh run view --log-failed`) and read the step that failed.
2. **"Check the Artificial Analysis key is set":** the secret is missing or was deleted. Add it as above.
3. **"Pull every source":** a source was unreachable or changed format. Rerun later; if it keeps failing, run `python3 scripts/refresh.py` locally to see the error.
4. **"Sanity checks":** the log names the source that dropped or the area that moved. If the change is real (for example, a source retired a benchmark, or a major Chinese release closed a gap by more than 4 months), run the three commands under "Refresh by hand" locally, review the result, then commit and push. The next scheduled run compares against that commit and passes.
5. If a lab is reported as missing from `data/labs.csv`, add it and push; the run does not fail for this, but that lab's models are ignored until you do.

### Past headlines

`data/raw/` is not committed, so the dated git history is the record of past figures. To see what the page said on a given day, check out that day's "Data refresh" commit and open `index.html`, or read `data/profile.json` from it:

```bash
git log --oneline -- data/profile.json
git show <commit>:data/profile.json
```

## Data files

| File | What it holds | Maintained by |
|---|---|---|
| `data/models.csv` | One row per model: name, lab, country, release date, weights, training compute, announcement link, aliases | refresh; rows with `added_by` = `manual` are kept |
| `data/scores.csv` | Long format: model, benchmark, domain, score, CI, source, source type, source URL, retrieved date | refresh; rows whose `source` starts with `manual` are kept |
| `data/benchmarks.csv` | Benchmark, area, ceiling, saturation date, status, coverage counts, notes | refresh |
| `data/inventory.csv` | Every benchmark found in every source, with coverage and why it was or was not used | refresh |
| `data/compute_stock.csv` | Epoch's chip-owner estimates: quarter, owner, chip designer, H100e with percentiles, units, power | refresh |
| `data/chip_deployment.csv` | Epoch's chip-owner estimates by chip type: quarter, owner, designer, chip type, units with percentiles, H100e | refresh |
| `data/chips.csv` | Epoch's accelerator specifications: designer, country, release date, 16-bit and 8-bit performance, memory bandwidth and capacity, status; rows with `added_by` = `manual` are kept | refresh, plus you |
| `data/chip_type_map.csv` | Which `chips.csv` row stands for each chip type in the owner data, whether its bandwidth is used, and flags | you |
| `data/deployed_chips.csv` | Each chip type counted as deployed, per owner group: first quarter, units, 16-bit performance, bandwidth | build |
| `data/prices.csv` | Today's list prices and index score per Artificial Analysis model configuration | refresh |
| `data/price_history.csv` | A row each time a configuration's price first appears or changes | refresh (append only) |
| `data/profile.json` | Area medians, score count and China's chip stock from the last build | build |
| `data/labs.csv` | Lab, country and the names each source uses for it | you |
| `data/events.csv` | Export controls, Entity List actions, chip milestones | you |
| `data/assessments.csv` | Published gap estimates | you |

`data/raw/` holds each refresh's downloads and is not committed.

### Add a model

Normally models arrive through a refresh. To add one by hand, add a row to `models.csv` with `country` (`US` or `China`), `release_date` (`YYYY-MM-DD`), `weights` (`open`, `closed` or `unknown`) and `added_by` = `manual`.

### Add a score

Add a row to `scores.csv`. `model` must match a `name` in `models.csv` and `benchmark` an id in `benchmarks.csv`. Set `source` to something starting with `manual`, `source_type` to `independent`, `self_reported` or `unknown`, and give a `source_url`. To add a new benchmark, add it to the `EPOCH`, `ARENA` or `AA` list at the top of `scripts/refresh.py`.

### Add a lab

If a refresh prints "labs missing from data/labs.csv", add a row with the country and the source's spelling under `aliases` (separate several with `|`). Until then that lab's models are treated as unknown country and ignored.

### Add or map a chip

If `build.py` warns that a chip type has no row in `data/chip_type_map.csv`, add one naming the `chips.csv` row it corresponds to (`use_bandwidth` = `yes` or `no`, and a `flag` and `notes` if the match is approximate). To add a chip Epoch lacks or has no date for, add a row to `chips.csv` with `added_by` = `manual`, a `source_url`, `status` (`released` or `announced, not released`) and `flag` for any value not confirmed from a primary source. Leave a spec blank rather than estimating it.

### Add an event

Add a row to `events.csv`: `date`, `event`, `category` (`export_control`, `entity_list` or `china_chip`), `description`, `source_url`, and `flag` and `notes` if anything is unverified.

### Add a published estimate

Add a row to `assessments.csv`: `date`, `publisher`, `domain` (an area name, so it can serve as a fallback), `estimate` (a sentence), `measures` (what is compared, in a few words), `method`, `source_url`, `unit` (`months` or `percent`), `low`, `high`, `point`, and `compare_to`, which tells the page what to plot beside it: `bench:<id>`, `domain:<area name>`, `eci_mean_since_2023` or `arena_text_pct`.

## Inventory results

`data/inventory.csv` lists 108 benchmarks or evaluation fields across the four sources (83 of them files in Epoch's archive). 59 are used.

Status and lag are for the "all sources" view.

| Benchmark | Area | Source | Status | Lag today (months) | Why |
|---|---|---|---|---|---|
| AA Intelligence Index | Overall | Artificial Analysis | counts | 4.1 | 90 Chinese models in 12 months |
| Arena text (style-controlled) | Overall | Arena | counts | 8.2 | 51 Chinese models in 12 months |
| Epoch Capabilities Index | Overall | Epoch AI | counts | 7.3 | 36 Chinese models in 12 months |
| tau2-bench (AA) | Agentic and real-world work | Artificial Analysis | saturated | China ahead 7.0 | both countries within 5% of ceiling since 2026-02-17 |
| APEX-Agents | Agentic and real-world work | Epoch AI | counts | 4.1 | 14 Chinese models in 12 months |
| Arena agent | Agentic and real-world work | Arena | counts | 1.4 | 24 Chinese models in 12 months |
| GDPval | Agentic and real-world work | Epoch AI | no Chinese scores |  | no Chinese model scored |
| METR time horizon (50%) | Agentic and real-world work | METR | closed series | 19.6 | Closed series |
| OSWorld | Agentic and real-world work | Epoch AI | stale | 10.6 | latest Chinese score 2026-01-27; 1 Chinese models in 12 months |
| OSWorld 2.0 | Agentic and real-world work | Epoch AI | counts | 7.8 | 3 Chinese models in 12 months |
| PostTrainBench | Agentic and real-world work | Epoch AI | stale | 4.5 | latest Chinese score 2026-07-16; 2 Chinese models in 12 months |
| Remote Labor Index | Agentic and real-world work | Epoch AI | no Chinese scores |  | no Chinese model scored |
| TheAgentCompany | Agentic and real-world work | Epoch AI | stale | China ahead 12.5 | latest Chinese score 2025-09-29; 0 Chinese models in 12 months |
| Vending-Bench 2 | Agentic and real-world work | Epoch AI | counts | 5.9 | 18 Chinese models in 12 months |
| LiveCodeBench (AA) | Coding | Artificial Analysis | saturated | 10.8 | on the saturated list |
| Terminal-Bench 4.0 (AA) | Coding | Artificial Analysis | counts | 4.1 | 29 Chinese models in 12 months |
| Aider Polyglot | Coding | Epoch AI | stale | 17.9 | latest Chinese score 2025-12-01; 1 Chinese models in 12 months |
| ALE-Bench | Coding | Epoch AI | counts | 8.2 | 33 Chinese models in 12 months |
| Arena WebDev | Coding | Arena | counts | 2.7 | 46 Chinese models in 12 months |
| CursorBench | Coding | Epoch AI | stale | 2.7 | latest Chinese score 2026-08-20; 2 Chinese models in 12 months |
| DeepSWE | Coding | Epoch AI | counts | 4.1 | 6 Chinese models in 12 months |
| FrontierCode | Coding | Epoch AI | counts | 4.5 | 10 Chinese models in 12 months |
| FrontierSWE | Coding | Epoch AI | counts | 4.1 | 5 Chinese models in 12 months |
| GSO-Bench | Coding | Epoch AI | stale | 17.9 | latest Chinese score 2025-07-31; 0 Chinese models in 12 months |
| SWE-bench Verified | Coding | Epoch AI | saturated | 8.2 | on the saturated list |
| Terminal-Bench 2.0 | Coding | Epoch AI | counts | 11.0 | 11 Chinese models in 12 months |
| WeirdML | Coding | Epoch AI | counts | 5.7 | 17 Chinese models in 12 months |
| Humanity's Last Exam (AA) | Frontier reasoning and science | Artificial Analysis | counts | 4.1 | 90 Chinese models in 12 months |
| SciCode (AA) | Frontier reasoning and science | Artificial Analysis | counts | 4.1 | 44 Chinese models in 12 months |
| CritPt | Frontier reasoning and science | Epoch AI | counts | 7.3 | 35 Chinese models in 12 months |
| GPQA Diamond | Frontier reasoning and science | Epoch AI | saturated | 7.8 | on the saturated list |
| LMCA (conceptual argumentation) | Frontier reasoning and science | Epoch AI | counts | 8.2 | 28 Chinese models in 12 months |
| SimpleBench | Frontier reasoning and science | Epoch AI | counts | 10.8 | 14 Chinese models in 12 months |
| FrontierMath Tiers 1-3 (v2) | Research math | Epoch AI | counts | 7.3 | 22 Chinese models in 12 months |
| FrontierMath Tiers 1-3 (2025 set) | Research math | Epoch AI | closed series | 10.1 | Superseded by the v2 set on 2026-06-12 |
| FrontierMath Tier 4 (v2) | Research math | Epoch AI | counts | 7.3 | 13 Chinese models in 12 months |
| FrontierMath Tier 4 (2025 set) | Research math | Epoch AI | closed series | 12.2 | Superseded by the v2 set on 2026-06-12 |
| MATH Level 5 | Research math | Epoch AI | saturated | 17.9 | both countries within 5% of ceiling since 2025-05-28 |
| OTIS Mock AIME 2024-2025 | Research math | Epoch AI | saturated | 5.7 | both countries within 5% of ceiling since 2026-04-20 |
| ProofBench | Research math | Epoch AI | counts | 4.1 | 24 Chinese models in 12 months |
| MMLU-Pro (AA) | Knowledge and hallucination | Artificial Analysis | stale | 14.3 | latest Chinese score 2025-12-23; 18 Chinese models in 12 months |
| Arena text factuality | Knowledge and hallucination | Arena | counts | 8.2 | 50 Chinese models in 12 months |
| MMLU | Knowledge and hallucination | Epoch AI | saturated | 23.7 | on the saturated list |
| SimpleQA Verified | Knowledge and hallucination | Epoch AI | counts | 9.9 | 20 Chinese models in 12 months |
| AA-LCR long-context reasoning | Long context | Artificial Analysis | counts | China ahead 2.9 | 86 Chinese models in 12 months |
| Fiction.LiveBench (120k tokens) | Long context | Epoch AI | stale | 18.6 | latest Chinese score 2026-01-27; 1 Chinese models in 12 months |
| GDP.pdf | Long context | Epoch AI | counts | 5.7 | 6 Chinese models in 12 months |
| Arena document (style-controlled) | Multimodal | Arena | counts | 10.6 | 5 Chinese models in 12 months |
| Arena vision (style-controlled) | Multimodal | Arena | counts | 5.9 | 22 Chinese models in 12 months |
| Furniture Assembly | Multimodal | Epoch AI | counts | 10.1 | 4 Chinese models in 12 months |
| Video-MME (no subtitles) | Multimodal | Epoch AI | stale | China ahead 15.8 | latest Chinese score 2025-06-18; 0 Chinese models in 12 months |
| Cybench | Cyber and security | Epoch AI | no Chinese scores |  | no Chinese model scored |
| ExploitBench | Cyber and security | Epoch AI | counts | 7.8 | 3 Chinese models in 12 months |
| ARC-AGI-1 | Puzzles and games | Epoch AI | saturated | 8.0 | on the saturated list |
| ARC-AGI-2 | Puzzles and games | Epoch AI | saturated | 8.2 | on the saturated list |
| BALROG | Puzzles and games | Epoch AI | stale | 18.6 | latest Chinese score 2025-01-20; 0 Chinese models in 12 months |
| Chess Puzzles | Puzzles and games | Epoch AI | counts | 10.1 | 32 Chinese models in 12 months |
| EnigmaEval | Puzzles and games | Epoch AI | stale | 21.8 | latest Chinese score 2026-01-27; 1 Chinese models in 12 months |
| Mystery Game Puzzles | Puzzles and games | Epoch AI | counts | 5.7 | 23 Chinese models in 12 months |

### Left out

- **No Chinese model in the last 12 months:** ANLI, algotune, ARC AI2, BBH, bool_q, CadEval, common_sense_qa_2, DeepResearch Bench, frontiermath_erdos, GeoBench, GSM8K, HellaSwag, LAMBADA, Lech Mazur Writing, live_bench, mindcube, MirrorCode, OpenBookQA, PIQA, ScienceQA, spatialviz_bench, SuperGLUE, TriviaQA, VPCT, Winogrande.
- **Not needed: older or saturated evaluation, or covered by another source:** gpqa, ifbench, terminalbench_hard, artificial_analysis_coding_index, terminalbench_v2_1, tau_banking, aime_25, artificial_analysis_math_index, aime, math_500.
- **Latest Chinese score is older than 6 months:** CL-bench, CL-bench Life.
- **Could not confirm what it measures:** gbaeval, EBR-bench.
- **Forecasting is outside the domain list:** forecastbench, btf3.
- **Only 2 Chinese models so far:** blueprint_bench_2, weirdml_v3.
- **Copy of Arena data; pulled from the Arena dataset instead:** webdev_arena.
- **Copy of Artificial Analysis data; pulled from their API instead:** scicode.
- **Decision-theory multiple choice from the same Conceptual Reasoning Index as LMCA; dropped so one project is not counted twice:** DTBench.
- **Could not confirm what it measures; both countries already at the same top score:** Surface Evolver Bench.
- **Only 3 Chinese models; the Artificial Analysis API covers HLE far better:** HLE.
- **Used only to add Chinese models to the METR historical series:** METR Time Horizons.

### Differences from the original candidate list

- **Not available from any automated source:** GDPval-AA, AA-Briefcase, AA-Omniscience and CritPt are not in the Artificial Analysis API response. CritPt comes from Epoch's copy instead. SWE-bench Pro has a metadata row in Epoch's archive but no data file.
- **API fields that do come back:** intelligence, coding and math indices, `hle`, `scicode`, `lcr`, `terminalbench_v4_0`, `terminalbench_v2_1`, `terminalbench_hard`, `tau2`, `tau_banking`, `gpqa`, `mmlu_pro`, `livecodebench`, `ifbench`, `aime`, `aime_25`, `math_500`.
- **GDPval:** Epoch has it, but with no Chinese model scored.
- **Cyber:** one usable benchmark, ExploitBench, with exactly 3 Chinese models.
- **METR:** METR's own file has no Chinese models, so the series adds the seven Chinese models from Epoch's copy of METR's results.
- **Added:** a "Puzzles and games" area for Epoch's Chess Puzzles and Mystery Game Puzzles.

## What was verified on 2026-10-13, and what changed

| Item | Finding | Source | Change |
|---|---|---|---|
| LMCA | "Language Model Conceptual Argumentation": models rate arguments on decision theory, philosophy and AI safety and are scored against expert ratings. Built by Redwood Research with Anthropic. Neither the site nor the announcement says who runs the evaluations | conceptualreasoning.ai/lmca; alignment.anthropic.com/2026/conceptual-reasoning-index | Kept under reasoning. Source type changed from independent to unknown, so it counts only under "all sources" |
| DTBench | 407 multiple-choice questions on Newcomb-like decision theory, from the same project and index as LMCA | conceptualreasoning.ai/dtbench | Dropped, so one project is not counted twice in one area |
| Furniture Assembly | Epoch's own benchmark: spatial reasoning from a photo of part-built furniture and its PDF manual | epoch.ai/benchmarks/furniture-assembly | Multimodal assignment confirmed; "guess" note removed |
| MiMo-V2.6 Pro | Open weights: Xiaomi says it "fully open-sourced the weights" and links a Hugging Face collection | mimo.mi.com/docs/en-US/news/latest/v2-6 | None; Epoch's "open" was right |
| APEX-Agents | Mercor, the benchmark's maker, runs every model itself at maximum reasoning effort | mercor.com/apex/methodology | Source type changed from unknown to independent, so it now counts in the default view |
| Nanbeige | Lab of BOSS Zhipin, Beijing | huggingface.co/Nanbeige | China (was from memory) |
| Institute of Foundation Models | Part of MBZUAI, Abu Dhabi | MBZUAI announcement of K2 Horizon | UAE (was from memory) |
| Apodex | Redwood City, California | company press release | US (was unknown) |
| Celeris | San Francisco | company press release | US (was unknown) |
| OpenChat | Student team at Tsinghua University | project README | China (was unknown) |
| Nex AGI | Shanghai, per ModelScope and secondary coverage | no primary source found | China, flagged as secondary |
| AI9Stars, RWKV | No source for either team's location | | Still unknown; their models are ignored |
| Phi-4's 0 on tau2 | 22 models score exactly 0 on tau2, including models with no tool calling. Phi-4 also scores exactly 0 on AA-LCR. Artificial Analysis does not say which zeros are failed runs | API response | All 154 exact zeros on 0-to-1 Artificial Analysis evaluations are now ignored. None could set a frontier; they only inflated coverage counts |
| Stanford AI Index 2.7% | The report gives 1,503 against 1,464. Those match Arena's text leaderboard (not style-controlled) of 2026-03-03: Claude Opus 4.6 at 1,503.9 and ByteDance's Dola-Seed-2.0 Preview at 1,464.2, a 2.7% gap | hai.stanford.edu technical performance chapter; Arena dataset | Row re-dated to 2026-03-03; this data now reproduces 2.7% (it gave 1.9% for 31 March) |
| ByteDance on Arena | Finding the Stanford board showed Arena leaves the organisation blank for some ByteDance models on some boards | Arena dataset | Models now take their usual organisation label, which adds ByteDance's models to China's side |
| Mate 60 Pro date | On sale 2023-08-29 | Caixin, 2023-09-05 | Confirmed; flag removed |
| October 2023 chip rule | The rule adds a performance density test to stop workarounds. Nvidia's 8-K of the same day names the A800, H800 and L40S as covered | Federal Register text; Nvidia 8-K | Confirmed; flag removed; description corrected |
| October 2023 Entity List | Names Biren and Moore Thread entities | Federal Register text | Confirmed; flag removed |
| January 2025 Entity List | First rule names Sophgo and affiliates; second names Zhipu entities | Federal Register texts | Confirmed; flag removed |
| September 2025 Entity List | Includes GMC Semiconductor, Jicun Semiconductor, Shanghai Fudan Microelectronics and Sino IC, cited for chips including AI; others are biotech and aerospace | Federal Register text | Confirmed as chip-relevant; flag removed |
| H200 announcement | Truth Social post of 2025-12-08: H200 sales to approved Chinese customers, 25% to the US government | Reuters via Khaleej Times; The Register | Confirmed; flag removed; source replaced |

No event row was dropped.

## DECISIONS

1. **Lags are computed at build time in Python, not in the browser.** One implementation (`gap.py`) serves the page, `benchmarks.csv` and the README. The page does not advance by itself; a build moves it.
2. **Each benchmark belongs to one area.** Terminal-Bench is under Coding only, so no benchmark is counted twice.
3. **"Independent" means not reported by the model's own developer.** Epoch-run evaluations, Artificial Analysis, Arena, METR, Mercor and benchmark maintainers' leaderboards count as independent. Rows whose source is a system card, model card, technical report or announcement are self-reported. Terminal-Bench 2.0 rows where the agent was built by the model's developer are self-reported. Where neither the data nor the maintainer says who ran the evaluation, the type is `unknown` (LMCA, GDPval, Remote Labor Index, PostTrainBench, ARC-AGI-2).
4. **Leaderboards may accept submissions.** I did not check whether each maintainer's leaderboard runs models itself, so "independent" is weaker for those than for Epoch-run or Artificial Analysis results.
5. **The saturated list overrides the 5% rule.** GPQA Diamond, MATH Level 5, OTIS Mock AIME, SWE-bench Verified, LiveCodeBench, ARC-AGI-1 and ARC-AGI-2 are kept out of the current profile even where China's best is not yet within 5% of the ceiling. I added MMLU to that list. They count in the heatmap up to last month. MMMU-Pro and ARC-AGI-3 are not in any source.
6. **The 5% rule also caught tau2-bench** (both countries above 0.95 since February 2026).
7. **Model names are reconciled by normalised matching,** not by hand. Epoch's model groups are the canonical names. Artificial Analysis and Arena names are matched after removing brackets, date stamps and effort tags such as "high" or "thinking". Unmatched models become new rows.
8. **Arena-only models are dated by first appearance on any Arena board** (145 models, flagged "release date approximate"). This is later than the true release date by days or weeks.
9. **Arena scores are each model's most recent rating** on the style-controlled board where one exists (text, vision, document). WebDev, agent and text factuality have no style-controlled variant. Arena search boards are left out because they rate search products.
10. **Arena boards that started recently understate the lag.** A US model that would have matched China's level before the board existed has no rating. This affects Arena agent (June 2026), text factuality (July 2026) and document (March 2026) most.
11. **Where a benchmark exists in two sources, one is used:** HLE and SciCode from the Artificial Analysis API, WebDev from Arena, GPQA from Epoch.
12. **One best score per model per source type.** Reasoning-effort variants and different agent scaffolds are collapsed to the model's best.
13. **Scores are stored in the source's own units.** Ceilings are converted to match.
14. **Standard errors become 95% intervals** (±1.96 SE). ECI's intervals are Epoch's 90% ones, unchanged.
15. **History uses the same coverage rule as of each month,** so early months are blank for most areas instead of showing a lag from one or two models.
16. **Published estimates in a different unit or scope are shown as published.** Stanford's 2.7% is compared with a percentage gap recomputed from Arena's text board. UK AISI's open-versus-closed cyber figure is compared with the China-versus-US cyber lag, labelled as a different quantity.
17. **Fiction.LiveBench uses the 120k-token score** as the long-context measure, not the 16k score Epoch uses for ECI.
18. **The page leads with a timeline, not a months axis.** Each area is placed on the date the US reached China's current level.
19. **The heatmap shows quarter ends with the number in each cell.** Lags are still computed monthly; the History tab shows the monthly line. The current quarter is labelled "to date".
20. **One explorer replaces separate sections.** Selecting an area drives three tabs (History, Benchmarks, Open weights). Recent releases, events and data to check sit under Reference, closed by default.
21. **Low confidence is a fixed rule, not a judgment:** fewer than 3 counted benchmarks, or benchmarks that disagree on direction. It is applied to history as of each month too, so most early heatmap cells are faded.
22. **The headline uses only areas that are not low confidence.** If fewer than two qualify, the page says so instead of naming areas.
23. **For an area whose benchmarks disagree on direction, the page does not say "China is where the US was in month X".** It gives the median and names the benchmarks on each side. This is how long context is described: 1.4 months is the midpoint of AA-LCR (China ahead by 2.9) and GDP.pdf (behind by 5.7).
24. **The fallback estimate is the most recent `assessments.csv` row whose `domain` equals the area and whose unit is months,** shown only when the area has fewer than 2 counted benchmarks. It is drawn as a dashed bracket and never mixed into the area's own number.
25. **The lapse warning fires only when every counted benchmark in an area expires within 30 days.** A single benchmark lapsing in an area with others is not flagged.
26. **Pre-2025 shading is a fixed date (2025-01-01),** set as `THIN_UNTIL` in `build.py`. The data for those years is still shown and still computed the same way.
27. **DTBench was dropped and LMCA kept,** because both come from the Conceptual Reasoning Index and LMCA carries 60% of that index. LMCA's source type is `unknown` because Anthropic co-built it and the site does not say who runs models on it.
28. **Exact zeros on 0-to-1 Artificial Analysis evaluations are ignored** as probable failed runs. I could not confirm this from Artificial Analysis; the reasoning is that 22 models score exactly 0 on tau2, including ones without tool calling.
29. **An Arena model takes its most common non-blank organisation label** across boards.
30. **Lab logos were replaced with lettered badges** before the page was made public, to avoid relying on each lab's trademark terms. The `assets/logos` folder was deleted.
31. **Past headlines are reproduced from git history,** not from raw downloads. `data/raw/` is not committed, so each dated commit of the processed CSVs and `data/profile.json` is the record.
32. **The automatic refresh treats an area gaining or losing its last counted benchmark as a note, not a failure.** Otherwise the expected loss of cyber on 2026-10-20 would block publishing.
33. **Refreshes are made reproducible so the daily commit shows only real changes.** Scores are written with ten significant digits, ties between equal scores are broken by source, and a score keeps the date it was first retrieved.
34. **The `AA_API_KEY` repository secret was set from the key supplied in the session,** using `gh secret set` with the key piped in, so the first run could be verified. It is stored only as an encrypted GitHub secret. Replace it the same way if you rotate the key.

35. **Seven named US companies stand in for the US in chip stock.** Epoch has no US total. Using only named US-headquartered owners understates the US and makes the lag a minimum; adding "Other" would mix in non-US buyers.
36. **Chip stock is measured to Epoch's last complete quarter,** not to today. Quarters Epoch flags as incomplete are dropped, and cumulative figures carry forward for an owner with no row in a quarter.
37. **China's percentile range is the sum of each designer's 5th and 95th percentiles.** That is wider than the true range of the total; it is used only for the bracketed lag range.
38. **The smuggling estimate is off by default,** because Epoch calls it speculative and it starts only in 2024.
39. **Chips are compared on 16-bit performance,** the higher of Epoch's tensor-core and plain FP16 columns, because that is the precision both sides report. All Chinese designers are compared with Nvidia; Huawei is also shown alone because it supplies most Chinese-designed chips in the stock estimate.
40. **Chip performance is a specification, not a production count.** China's best 16-bit figure is Biren's BR100 from 2022, which is not among the chip types in Epoch's China stock. Superseded by 46: the spec-sheet view is now secondary and off the overview.
41. **Training compute uses every model with an Epoch estimate, including ones without benchmark scores.** China's largest is ByteDance's Doubao-pro. The coverage table counts only ECI-scored models.
42. **Cost uses model configurations, not models.** A configuration's index score and price come from the same row, so reasoning-effort variants of one model appear separately.
43. **Price history is a change log,** not a daily snapshot, so it grows only when prices change.
44. **The site is split into six tabs with hash links.** A tab's charts are drawn when it is first shown, so they are sized from a visible container. The policy timeline shows each area's lag at the month end on or after each event, and China's chip stock at the last quarter end on or before it.
45. **The sanity checks also fail a run if the chip-owner, chip-specification or price table is empty, or if China's chip stock changes by more than 50%.** A new quarter of Epoch data would raise the stock by far less than that.
46. **The best-chip measure is the best chip deployed at scale, not the best chip announced.** It uses Epoch's units by chip type, so a chip only counts once one side owns it in volume. The spec-sheet comparison is kept, labelled, as the last compute section.
47. **The deployment threshold is 10,000 cumulative units per owner group.** It is low enough that a chip in its first quarter of real deployment counts, and high enough to exclude pilot quantities. From 1,000 to 100,000 units the 16-bit lag moves between 30.1 and 39.0 months for both China lines, almost entirely through the date the US H100 passes the threshold, so the choice does not change the conclusion. The page and this README show the full table.
48. **Units are summed across the seven US companies before applying the threshold,** the same group as the chip-stock comparison. A type counts for the US once the seven together hold 10,000, even if no single company does.
49. **A chip cannot count as deployed before its release date.** Epoch allocates 12,500 Ascend 910C units to Q1 2024 although Epoch's own hardware table dates the 910C to 2024-10-15; the 910C counts from the first quarter end after release (Q4 2024).
50. **"Chinese-designed" uses the designer's country in `chips.csv`** (the hand-kept `CHINESE_CHIP_MAKERS` list), so the line is Huawei and Cambricon today.
51. **Combined and ambiguous chip types use the conservative specification.** H100/H200 uses the H100 (same 16-bit, lower bandwidth). A100 uses the 80 GB SXM variant (the highest A100 bandwidth, flagged). Ascend 910B uses Epoch's generic 910B row.
52. **The MI308X's bandwidth is left out.** Epoch lists 10.3 TB/s, twice the 5.3 TB/s it gives the MI300X this chip is cut down from; third-party databases give 5.32 TB/s and AMD publishes no datasheet. Its 16-bit figure (654 TFLOP/s) is used. Including Epoch's figure would make China's best deployed bandwidth exceed every US chip's from Q4 2025.
53. **Smuggled chips are not in the deployed view.** Epoch's smuggling estimate has no split by chip type.
54. **Lags for deployed chips are measured to Epoch's last complete quarter (2025-12-31),** like chip stock. A match in Epoch's first quarter (Q1 2022) would be shown as "at least"; none of today's figures are.
55. **The 950PR's release date is the end of the quarter Huawei announced (2026-03-31).** Huawei said in September 2025 it would be available in Q1 2026. Secondary reports (Reuters via RTHK, March 2026) put mass production in March or April 2026; no Huawei shipment announcement was found. No spec was filled from memory: 16-bit performance and memory capacity are blank because Huawei did not publish them, and the 1.6 TB/s bandwidth is Epoch's figure, flagged. For the 960 and 970, Epoch's absolute bandwidths (9.6 and 14.4 TB/s) were not used because the keynote gives only ratios.
56. **The system-scaling note cites Huawei for the 384-chip count and SemiAnalysis for the system comparison.** SemiAnalysis is not a primary source but is the most specific reputable one found; the note attributes the estimate to it.
57. **The training-compute comparison has no months-behind figure anywhere on the page or in the summary table.** The page gives the largest disclosed run on each side and the date a disclosed US run first matched China's largest, each with the disclosure caveat beside it, below the coverage table.
58. **Every chart names its unit on the y axis,** and end-of-line labels get a right margin measured from their text, so they are not clipped at any width.
59. **The overview's cards share four grid rows** (title, introduction, body, link) so they line up. On phones they stack.
60. **Pricing notes are hand-kept per model** (`PRICE_NOTES` in `build.py`) and shown only while that model sets a row of the cost table.

## Spot check

Ten random rows of `scores.csv` (seed 20261013) were compared with freshly downloaded sources through a separate code path: 10 of 10 matched. This confirms values are copied correctly. It does not confirm that each alias was matched to the right model.

A second spot check on 2026-10-13 covered the new tables: 4 random rows of `compute_stock.csv`, 3 of `chips.csv` and 3 of `prices.csv` (seed 1013) against fresh downloads. 10 of 10 matched.

A third, of the deployed-chip table, took 5 random rows of `data/deployed_chips.csv` (seed 20261013) and recomputed each from Epoch's raw `cumulative_by_chip_type.csv` and `ml_hardware.csv` with separate code (pivot by owner, carry forward, sum, find the first quarter at or after release with 10,000 units): US MI300X, US MI355X, China H800, China Ascend 910B and China Ascend 910C. 5 of 5 matched on first deployed quarter, units then, units at the last quarter, 16-bit performance and bandwidth.

## Data points still to check by hand

**Compute and cost**

- **Ascend 950PR.** Release date (2026-03-31) is Huawei's announced quarter, not a confirmed shipment; its 1.6 TB/s bandwidth is from Epoch, citing Tom's Hardware. Not in Epoch's owner data, so not yet in the deployed view.
- **MI308X bandwidth.** Epoch's 10.3 TB/s looks like an error (see DECISIONS 52); left out until AMD or Epoch confirms a figure.
- **Ascend 910B variant mix.** Epoch's owner data does not split 910B variants (280 to 400 TFLOP/s, 0.8 to 1.6 TB/s); the generic row is used. China's headline lines rest on the H800, H20 and 910C, so this does not move them.
- **Huawei before 2024.** Epoch's Huawei and Cambricon estimates start in Q1 2024, so Ascend chips deployed earlier are not dated earlier. This cannot raise China's lines: the 910B (376 TFLOP/s) is below the H800 China already had.
- **CloudMatrix 384 comparison.** The 300 PFLOP/s and 4.1 times power figures are SemiAnalysis estimates, not Huawei's.
- **Chip-maker countries** are a hand-kept list in `scripts/refresh.py` (`CHINESE_CHIP_MAKERS`); a new Chinese designer in Epoch's table would be treated as non-Chinese until added.
- **xAI and CoreWeave** have rows for only some quarters in Epoch's file; their cumulative figures are carried forward between them.
- **Training compute for recent US closed models** is mostly absent, so the largest-disclosed-run comparison and the scatter rest on the few that disclose.

**Capabilities**

1. **Cyber rests on one benchmark that expires on 2026-10-20.** After that the area shows only the UK AISI estimate (tested with `--as-of 2026-10-21`).
2. **LMCA's evaluator.** If Redwood Research runs every model itself, LMCA should be independent, which would move reasoning from 5.7 to 7.3 months in the default view.
3. **Artificial Analysis zeros.** 154 exact-zero scores are ignored as failed runs without confirmation from Artificial Analysis.
4. **Artificial Analysis index history.** The API does not mark which older scores are estimates; the website marks most pre-2026 models that way.
5. **Arena agent's 1.4-month lag.** The board is four months old and its score is not defined in the dataset.
6. **Unrated closed Chinese models in 2023 and 2024.** If any existed that none of the three sources rated, the 2024 peak is overstated.
7. **Lab countries:** AI9Stars and RWKV are unknown; Nex AGI is China on secondary sources only.
8. **Models with no lab in Epoch's metadata** are treated as unknown country and ignored (113 models, mostly small or hosted variants).
9. **Stanford's models.** The board was identified by matching the two ratings. The model names (Claude Opus 4.6, Dola-Seed-2.0 Preview) come from Arena's data for that board and from secondary coverage, not from the report.
10. **UK AISI's 2025 figure** has no single date; it is placed at 30 September 2025.
11. **H200 announcement.** Confirmed through Reuters; the Truth Social post itself was not retrieved.
12. **BIS guidance of 2026-05-31.** Summarised from law-firm write-ups; the PDF was not read.
13. **SEC links** (two Nvidia 8-Ks) block automated checks; open them in a browser to confirm.

## Sources

- Epoch AI, benchmark data and Epoch Capabilities Index, https://epoch.ai/benchmarks (CC BY 4.0).
- Epoch AI, AI chip owners, https://epoch.ai/data/ai-chip-owners, and ML hardware, https://epoch.ai/data/ml_hardware.csv (CC BY 4.0).
- LMArena, leaderboard dataset, https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset (CC BY 4.0). Measures human preference, not capability.
- Artificial Analysis, https://artificialanalysis.ai/ (free API, scores and list prices; attribution required and shown on the page).
- METR, time horizons 1.1, https://metr.org/assets/benchmark_results_1_1.yaml (closed historical series).
- Events and published estimates: linked per row.
