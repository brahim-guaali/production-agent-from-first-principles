# A production agent from first principles

A course in runnable code. A refund agent for a food-delivery app works on twelve hand-written messages. This course takes it, one stage at a time, to what production would throw at it: customers it has seen before, conversations, work too open-ended for one step, streamed replies, services that fail, people who try to trick it, real traffic, and customers who rate it.

Every stage is real: Gemini (free tier) with real tool calls and structured output, a real HTTP platform (orders, refund policy, fraud scoring, payments with idempotency keys, manager approvals), SQLite, and a test suite. Each stage README ends with real-run numbers and **where it breaks**. And at almost every stage the real runs found something nobody planned:

| Stage | What the real run found |
|---|---|
| 00 | The same $72 request on two days was refunded twice: **$144 for a $72 order** |
| 01 | **14/14 right on a model nobody configured**: the free tier's 20 requests a day ran out and every call fell back to another model, silently |
| 03 | A fraud-review sub-agent found a device shared with a known fraud account by itself; an uncovered question cost 4 searches and 55 s |
| 04 | The model's first token came after 0.6 s; **the customer's first word after 15.6 s** |
| 04, 06 | A reply told a customer their refund was in **riyals**, for a dollar order |
| 06 | Two layers of prompt-injection detection: 18/18 verdicts, 1 model call out of 18 messages |
| 07 | **Six requests of traffic found a double refund**: the same message twice, 0.2 s apart, paid twice |
| 07 | Run p50 45 s, **customer wait p50 6.6 minutes**: the queue, not the agent |
| 08 | A correct refusal rated **1★**; a wait over 2 minutes cost more stars than any decision |

The agent comes from [graph engineering from first principles](https://github.com/brahim-guaali/graph-engineering-from-first-principles) (part 1), where it was built from a naive loop into a LangGraph graph. What comes next: [agent observability from first principles](https://github.com/brahim-guaali/agent-observability-from-first-principles), where this agent gets a camera.

## The stages

| # | Folder | What it adds | Where it breaks |
|---|---|---|---|
| 00 | [`00-baseline/`](00-baseline/) | The agent we start from | No memory: paid twice |
| 01 | [`01-memory/`](01-memory/) | The customer's history: past refunds, notes, no second refund on one order (§7), frequent claimers to a manager (§8) | One turn only |
| 02 | [`02-conversations/`](02-conversations/) | Sessions over several turns ("why only $72?") | One agent does everything; answers say more than the facts |
| 03 | [`03-sub-agents/`](03-sub-agents/) | A fraud reviewer for grey-zone scores, a policy expert that searches before the agent explains | Sub-agents multiply invisible work |
| 04 | [`04-streaming/`](04-streaming/) | Replies streamed to the chat; time to first token; the customer who leaves mid-reply | Services only hang; real ones fail differently |
| 05 | [`05-failures/`](05-failures/) | 500s, bad data, 404s, invalid model output, 429s and model fallback, all as data | Injection handled by luck |
| 06 | [`06-guardrails/`](06-guardrails/) | Prompt-injection detection (rules, a model when unsure) and a fact check on the reply | Measured one run at a time |
| 07 | [`07-traffic/`](07-traffic/) | A replayer: reworded requests, random arrivals, parallel workers, a run log | Nobody knows what customers thought, or which version answered |
| 08 | [`08-signals/`](08-signals/) | Ratings joined to runs; prompt, agent, model and environment versions on every run | We can say less about the agent than ever: next, the camera |

The agent lives in [`agent/`](agent/) and grows stage by stage; each stage is tagged (`stage-01`, …) so you can check it out as it was.

## Run it

```bash
make setup                      # Python 3.11+, creates .venv
export GEMINI_API_KEY=...       # free: https://aistudio.google.com/apikey
make platform                   # terminal 1: the food-delivery API on :8710
.venv/bin/python 01-memory/run.py        # terminal 2: any stage
make test                       # the tests need no key
```

Open http://127.0.0.1:8710/ui while a stage runs to watch it live.

## Layout

| Folder | What it is |
|---|---|
| [`agent/`](agent/) | The refund agent (LangGraph): graph, verifier, sub-agents, guardrails, lookups, versions |
| [`agentkit/`](agentkit/) | Gemini client, platform client, cases, judgments, traffic replayer, simulated customers |
| [`services/`](services/) | The food-delivery platform (FastAPI + SQLite) and the live run viewer |
| [`tests/`](tests/) | Run without a key: a scripted model stands in for Gemini |

MIT licensed. All data is made up.
