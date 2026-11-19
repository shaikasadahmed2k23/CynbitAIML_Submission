# 🔍 BitReview AI

**AI first-pass PR reviewer and mentor-triage queue for Cynbit's BitElevate internship: every daily PR gets scored, explained and prioritised in seconds, so mentors only deep-review what needs a human.**

- **Live demo:** _<add Streamlit Community Cloud URL here>_
- **Reports:** [AI Opportunity Report](docs/AI_Opportunity_Report.md) · [Technical Approach](docs/Technical_Approach.md) · [Evaluation results](eval/results.md)

## Screenshots

| Review (intern view) | Mentor queue | How it works |
|---|---|---|
| _<placeholder: docs/img/review.png>_ | _<placeholder: docs/img/queue.png>_ | _<placeholder: docs/img/how.png>_ |

The production UI is a React + Tailwind app themed on Cynbit's brand (tokens in [`frontend/src/theme.ts`](frontend/src/theme.ts)), served by a FastAPI backend. The original Streamlit demo is kept as a fallback (see below).

## Why

BitElevate interns submit a PR every day and senior mentors review each one. With 1000+ interns that does not scale. BitReview AI reviews every PR first, gives the intern immediate feedback, flags copied work, and hands mentors a prioritised queue. Modelled savings: ≈ 5,000+ mentor-hours per 60-day cohort (assumptions in the [report](docs/AI_Opportunity_Report.md#roi-math-all-inputs-are-assumptions)).

## Features

- **Input:** public GitHub PR URL (REST API, optional token) or pasted diff, plus track and roadmap-week selectors.
- **Deterministic checks:** hardcoded secrets, SQL injection, debug leftovers, TODOs, missing tests, N+1 queries, unlocked thread state, huge PRs, bad commit messages.
- **LLM rubric review** (correctness, code quality, security, testing, roadmap alignment) with strict, pydantic-validated JSON, inline comments with suggestions, and triage `AUTO_APPROVE | NEEDS_MENTOR | BLOCKER`. Groq (llama-3.3-70b) → Gemini fallback → **deterministic mock mode**, so the demo never breaks.
- **Hallucination guard:** comments pointing at lines that are not in the diff are dropped.
- **Copy detection:** TF-IDF char n-grams over normalized code (survives variable renaming).
- **Mentor dashboard:** priority-sorted queue, triage badges, copy flags, estimated mentor-minutes saved.
- **Evaluation + tests:** labeled samples, `eval/run_eval.py`, 37 pytest tests (core + API).

## Quickstart: React frontend + FastAPI (recommended)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scriptsctivate
pip install -r requirements.txt

# Option A: one process (build the frontend once, FastAPI serves it at http://localhost:8000)
cd frontend && npm ci && npm run build && cd ..
uvicorn api.server:app --port 8000

# Option B: hot-reload development (two terminals)
uvicorn api.server:app --reload --port 8000     # backend
cd frontend && npm run dev                      # http://localhost:5173, Vite proxies /api to :8000
```

Interactive API docs: `http://localhost:8000/docs`. Endpoints: `POST /api/review`, `GET /api/queue`, `GET /api/stats`, `GET /api/samples[/{id}]`, `GET /api/reviews/{id}`, `GET /api/health`, `POST /api/reset`.

With no API keys the app runs in **DEMO mode** (header badge) and is fully usable. The mentor queue is preloaded with 10 sample PRs.

## Streamlit fallback demo

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/main.py
```

With no API keys the app runs in **MOCK** mode and is fully usable. The dashboard is preloaded with 10 sample PRs.

```bash
pytest -q                      # unit tests
python eval/run_eval.py        # evaluation (live LLM if a key is set, else mock) -> eval/results.md
python eval/run_eval.py --mock # force deterministic mock
python data/build_samples.py   # regenerate sample diffs
```

## Environment variables

Read from the environment or `.streamlit/secrets.toml` (see [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example)). All optional.

| Name | Purpose |
|---|---|
| `GROQ_API_KEY` | Primary LLM (llama-3.3-70b-versatile) |
| `GEMINI_API_KEY` | Fallback LLM |
| `GITHUB_TOKEN` | Higher GitHub API rate limit when fetching PR URLs |

## Project structure

```
api/server.py           FastAPI: REST API + serves frontend/dist (SPA fallback)
frontend/               Vite + React + TypeScript + Tailwind app (src/theme.ts = Cynbit tokens)
Dockerfile, render.yaml one-service deploy on Render
app/
  main.py               Streamlit fallback UI (Intern view + Mentor dashboard)
  core/
    diff_parser.py      unified diff -> files / hunks / lines / languages
    static_checks.py    heuristic checks
    llm_reviewer.py     prompt, schema, Groq/Gemini/mock, guardrails
    similarity.py       copy detection
    triage.py           priority score + safety rails
    pipeline.py         orchestration + submission store
    github.py           PR fetching
    rubric.py           tracks, roadmap stages, rubric text
data/samples/           10 labeled sample diffs + manifest.json
data/build_samples.py   sample generator
eval/                   run_eval.py, results.md
tests/                  pytest suite
docs/                   AI_Opportunity_Report.md, Technical_Approach.md
```

## Deploy on Render (React + FastAPI, one service)

1. Push the repo to GitHub.
2. In Render choose **New → Blueprint** and select the repo. `render.yaml` defines one Docker web service (the [`Dockerfile`](Dockerfile) builds the frontend with `npm ci && npm run build`, installs the Python requirements, and starts `uvicorn api.server:app --host 0.0.0.0 --port $PORT`).
3. When prompted, set `GROQ_API_KEY`, `GEMINI_API_KEY` and `GITHUB_TOKEN` (all optional; without them the service runs in demo mode).
4. After the deploy, check `https://<service>.onrender.com/api/health` and paste the URL at the top of this README. Free instances sleep when idle, so the first request can take about a minute.

The public endpoint limits each IP to 30 reviews per hour to protect your LLM quota. Set `VITE_REPO_URL` at build time to show a GitHub link on the "How it works" page.

## Deploy the Streamlit fallback (Streamlit Community Cloud)

1. Push this repo to GitHub. 2. On share.streamlit.io choose **New app**, pick the repo, branch `main`, main file `app/main.py`. 3. (Optional) In **Advanced settings → Secrets** paste your keys in the format of `secrets.toml.example`. 4. Deploy, then paste the URL at the top of this README.

## Known limitations

The mock reviewer is rule-based; committed evaluation numbers measure the deterministic layers on 10 hand-written samples, not live-LLM accuracy. See [Technical Approach §6 and §10](docs/Technical_Approach.md).
