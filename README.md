# Agent observability from first principles

A course in runnable code. We take a real refund agent from a food-delivery app, make it behave like production (memory, conversations, failing services, traffic, customer feedback), then give it a **camera** (traces, cost, a budget meter) and a **referee** (evals, an LLM judge checked against a person, a release gate in CI).

- **Observability is the camera:** every model call, tool call and memory read leaves a span with its timing, tokens and cost, so you can see what a run did and what it spent.
- **Evals are the referee:** checks in code, a model acting as judge, and people decide whether a run was good enough, and a release gate ships only what passes.

The agent comes from [graph engineering from first principles](https://github.com/brahim-guaali/graph-engineering-from-first-principles), where it was built step by step from a naive loop into a LangGraph graph. Everything is real: Gemini (free tier) with real tool calls and structured output, a real HTTP platform (orders, refund policy, fraud scoring, payments with idempotency keys, manager approvals), SQLite, and a test suite. Every stage README ends with real-run numbers and **where it breaks**.

## The stages

| # | Folder | What it adds |
|---|---|---|
| 00 | [`00-baseline/`](00-baseline/) | The refund agent we start from, and why it's still a toy |
| | **Part 1 · A realistic agent** | |
| 01 | `01-memory/` | The customer's history as a tool: past refunds, a fraud signal, no second refund on one order |
| 02 | `02-conversations/` | Sessions over several turns ("why only $72?") |
| 03 | `03-tool-failures/` | Services that answer 500, bad data or 404, not only hang |
| 04 | `04-traffic/` | A replayer: the cases hundreds of times with variations |
| 05 | `05-outside-signals/` | Customer ratings; the prompt and model version on every run |
| | **Part 2 · The camera** | |
| 06 | `06-traces/` | OpenTelemetry GenAI spans written by hand, a timeline, customer data redacted |
| 07 | `07-meter/` | A metering proxy: budget check before each call, cost after, a budget stop |
| | **Part 3 · The referee** | |
| 08 | `08-evals/` | Deterministic evals read from traces |
| 09 | `09-judge/` | An LLM judge, calibrated against labels a person wrote |
| 10 | `10-release-gate/` | GitHub Actions blocks a change that makes the agent worse |
| 11 | `11-platforms/` | The same spans in Phoenix and Langfuse: what a platform adds |

The agent lives in [`agent/`](agent/) and grows stage by stage; each stage is tagged (`stage-01`, …) so you can check out the agent as it was.

## Run it

```bash
make setup                      # Python 3.11+, creates .venv
export GEMINI_API_KEY=...       # free: https://aistudio.google.com/apikey
make platform                   # terminal 1: the food-delivery API on :8710
.venv/bin/python 00-baseline/run.py      # terminal 2: any stage
make test                       # the tests need no key
```

Open http://127.0.0.1:8710/ui while a stage runs to watch it live.

## Layout

| Folder | What it is |
|---|---|
| [`agent/`](agent/) | The refund agent (LangGraph): graph, verifier, support loop |
| [`agentkit/`](agentkit/) | Gemini client, platform client, test cases, the two model judgments, the live viewer's tracer |
| [`services/`](services/) | The food-delivery platform (FastAPI + SQLite) and the live run viewer |
| [`tests/`](tests/) | Runs without a key: a scripted model stands in for Gemini |

MIT licensed. All data is made up.
