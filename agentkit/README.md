# agentkit

What every stage shares, so the stage folders hold only the idea they teach.

| File | What it is |
|---|---|
| `platform.py` | HTTP client for the [platform](../services/). A hung service fails after `PLATFORM_TIMEOUT` (5 s) |
| `llm.py` | Gemini client. `chat()` gives the model tools (for the loop); `structured()` asks one narrow question and gets a typed pydantic answer back (for graph nodes). It stays under the free tier's rate limit (`GEMINI_RPM`), retries 429/503, tries `gemini-3.5-flash-lite` then `gemini-3.1-flash-lite` (3.5 Flash allows only 20 free requests a day; see stage 01) and skips a model whose daily quota is spent, records which model answered in `Usage.models`, and counts calls, tokens and an illustrative cost in `Usage` |
| `cases.py` | `REFUND`, the running example, and `CASES`: 14 customer messages (late, missing items, fraud, a prompt injection, Arabic, an order already refunded, a frequent claimer) with the outcome the policy requires |
