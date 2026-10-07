# Corvane Fleet — AI Visibility & Accuracy Tracker

An offline-runnable Python tool and dashboard that shows whether AI assistants (ChatGPT, Perplexity, Google AI Overviews) **recommend, ignore, or misrepresent** Corvane Fleet when fleet buyers ask for software recommendations.

It analyzes a 6-week dataset of raw AI answers to 15 buyer questions and produces:

- Brand mentions, position, and stance (tone) per answer
- Detected factual errors (contradictions with ground truth)
- A single normalized **0–100 Visibility Score** for executives
- A two-persona Streamlit dashboard (CEO view + Marketing inspector)

> **Runs fully offline.** No paid APIs, no subscriptions, no external services. Standard local hardware is enough.

---

## Table of Contents

1. [Background](#background)
2. [Quickstart](#quickstart)
3. [Data Pack Placement](#data-pack-placement)
4. [Usage](#usage)
5. [Dashboard Screens](#dashboard-screens)
6. [How It Works](#how-it-works)
7. [Visibility Score Formula](#visibility-score-formula)
8. [Assumptions & Priorities](#assumptions--priorities)
9. [Manual Accuracy Check](#manual-accuracy-check-15-random-answers)
10. [AI Coding Tools Note](#ai-coding-tools-note)
11. [Scaling to 20 Clients Daily](#scaling-to-20-clients-daily)

---

## Background

**Client:** Corvane Fleet (fictional) — GPS tracking and ELD compliance software for trucking and field-service fleets of 20–500 vehicles. Based in Columbus, Ohio, founded 2014.

**Problem:** Buyers increasingly ask AI tools instead of Google. Corvane can't tell whether AI is recommending them, ignoring them, or saying something wrong.

**Two audiences, two views:**

| Stakeholder | Need |
|---|---|
| **Marcus Hale (CEO)** | A 2-minute Monday-morning read: are we winning or losing in AI, why did the score change, which competitors are taking share, and what is AI getting wrong about us? |
| **Priya Nair (Marketing Head)** | Prompt-level detail: which questions we appeared on, the exact answer AI gave, and which sources it cited. |

---

## Quickstart

**Prerequisites:** Python 3.10+ and Git.

```bash
# 1. Clone the repository
git clone https://github.com/krishnaprajapati2020-hue/corvane-ai-visibility-tracker.git
cd corvane-ai-visibility-tracker

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Place the data pack (see next section), then generate exports
python export_csvs.py

# 5. Run the tests
python -m pytest

# 6. Launch the dashboard
streamlit run app.py
```

The dashboard opens at **http://localhost:8501**.

---

## Data Pack Placement

The tool expects a data pack of four files. **They are intentionally not committed to this repository** (they are listed in `.gitignore`), so you must add them yourself.

| File | Contents |
|---|---|
| `prompts.csv` | 15 buyer questions, each with a buying stage (`early_research`, `comparing_options`, `specific_company`) and a priority (1–3) |
| `responses.jsonl` | 518 raw AI answers across ChatGPT, Perplexity, and Google AI Overviews — 2 runs per question per week, weeks 1–6 |
| `brands.json` | The 6 companies to detect |
| `facts.json` | Ground-truth facts about Corvane Fleet |

Place the files in the data folder expected by the scripts (by default `data/` — adjust if your layout differs).

**Brands**

- **Tracked:** corvane, trakvia, routelyne, gridwell
- **Detect-only:** fleetora, novahaul

**Ground truth (`facts.json`):** starting price $29/mo · dashcams: no · ELD compliance: yes · QuickBooks integration: yes · HQ: Columbus, Ohio.

---

## Usage

### Generate scoring exports

```bash
python export_csvs.py
```

Processes all 518 responses and writes:

| Output | Description |
|---|---|
| `mentions.csv` | 3,108 rows (518 responses × 6 brands): mention, position, stance per brand per answer |
| `wrong_facts.csv` | 25 detected contradictions with ground truth |

### Run the tests

```bash
python -m pytest
```

Expected output:

```
============================== 3 passed ==============================
```

The three tests cover: Corvane Logistics exclusion, Corvane Fleet detection, and tone classification.

### Launch the dashboard

```bash
streamlit run app.py
```

---

## Dashboard Screens

1. **Marcus's Monday View** — Visibility Score KPIs, week-over-week change (Δ), and a 6-week trend chart.
2. **Priya's Marketing Inspector** — Filter by week, engine, and buying stage; drill down into each AI answer with its citations.
3. **Hallucination Alerts** — Table of every answer that contradicts ground truth.

---

## How It Works

All core logic lives in `src/tracker.py`.

### Schema drift handling

The data format changed mid-study. The parser normalizes both versions:

| | Weeks 1–3 | Week 4 onward |
|---|---|---|
| Answer text | `response_text` | `answer` |
| Run number | `run` | `run_number` |
| Citations | `citations` | `sources` |

Engine names are also inconsistent (`chatgpt` vs `ChatGPT`, `AI Overview`), so they are normalized to one canonical form.

### Mention detection and disambiguation

- **Corvane Logistics is a different company** (a Midwest freight firm) and is never counted as Corvane Fleet. Before matching, any "Corvane Logistics" text is **masked** so it can't produce a false mention.
- Remaining brand-name variants are matched with regex.
- **Position** is the order in which brands first appear in the answer text (rank 1, 2, 3…). Citations/sources do **not** count as mentions.

### Tone classifier

A rule-based, sentence-level keyword classifier assigns one of four stances: `recommended`, `neutral`, `negative`, `not_recommended`. When an answer is mixed, the **final sentence / verdict** decides the stance.

### Fact checking

Claims in each answer are compared against `facts.json`. **Only direct contradictions are flagged** — for example, saying Corvane offers AI dashcams, quoting a starting price of $45 or $49, or claiming it lacks ELD compliance. Anything not covered by `facts.json` is not flagged.

---

## Visibility Score Formula

A single 0–100 number for executives:

$$
\text{Score} = \left( \frac{\sum \left(\text{Position Weight} \times \text{Tone Multiplier} \times \text{Prompt Priority}\right)}{\text{Max Available Weekly Priority} \times 1.3} \right) \times 100
$$

| Position Weight | | Tone Multiplier | | Prompt Priority | |
|---|---|---|---|---|---|
| Rank 1 | 1.00 | Recommended | 1.3 | Priority 3 | 3.0 |
| Rank 2 | 0.75 | Neutral | 1.0 | Priority 2 | 2.0 |
| Rank 3 | 0.50 | Negative | 0.5 | Priority 1 | 1.0 |
| Rank 4+ | 0.25 | Not recommended | 0.0 | | |
| Unmentioned | 0 | | | | |

**Normalization:** the denominator uses the prompt priority actually *available* that week, not a fixed total. This prevents missing data from looking like a drop in visibility (see Week 5 below).

---

## Assumptions & Priorities

- **Corvane Logistics ≠ Corvane Fleet.** It is masked before any matching (see above).
- **Week 4 schema drift** is normalized at parse time, so all six weeks are analyzed uniformly.
- **Week 5 missing data.** Perplexity data for Week 5 is incomplete (60 responses instead of the expected 90). The score divides by the priority available that week rather than counting raw mentions, so the gap does not produce a false decline.
- **Precision over recall for facts.** Only direct contradictions with `facts.json` are flagged, to avoid false alarms in front of executives.
- **Offline-first.** Rule-based detection keeps the tool free, fast, and reproducible, with no API keys.

---

## Manual Accuracy Check (15 Random Answers)

A manual hand-audit of 15 randomly selected answers against the tool's output:

| Metric | Result |
|---|---|
| Mention accuracy | **100%** |
| Tone accuracy | **93.3%** (14 of 15) |

Tone is the harder task because mixed-opinion answers are subjective; the final-verdict rule resolves most but not all of them.

---

## AI Coding Tools Note

Claude and Cursor were used to accelerate development. Regex errors and the schema-drift handling were **corrected manually by a human** after review, and results were verified through unit tests and the manual audit above.

---

## Scaling to 20 Clients Daily

To run roughly **1,800 queries per day** (about 20 clients × 90 queries each):

| Layer | Approach |
|---|---|
| Scheduling & workers | AWS ECS with Celery workers running daily jobs |
| Structured storage | Postgres / TimescaleDB for time-series scores and mentions |
| Raw archive | S3 for raw JSONL responses |
| Validation | Pydantic models to catch schema drift at ingestion |
| Cost | Estimated compute under **$35/month** |

---

## Contributing & License

Issues and pull requests are welcome. Add a `LICENSE` file of your choice (e.g., MIT) before sharing publicly.
