# An AI agent can be right every time and still not be ready for production

*Part 2 of 4 in **Building an AI agent from first principles**. [Part 1](https://medium.com/@brahimg/i-rebuilt-one-ai-agent-seven-times-to-understand-graph-engineering-80b9983cd921) built a refund agent from a naive loop into a graph. This part takes it toward production. A real model (Gemini), real code; every image comes from a recorded run.*

---

A pass rate says the answers were right. It doesn't say which model gave them, what the customer waited through, or what happens when requests race. Over eight stages my refund agent stayed right almost every time, and the problems that mattered were elsewhere.

It got 14 cases out of 14 on a model nobody configured, after a silent fallback. It wrote the right refund in a currency it invented. Its first token came after 0.6 seconds; the customer's first word after 15.6. None of that moves a pass rate.

The first problem was the plainest. At the end of part 1 the agent got 12 cases out of 12. Then the same customer sent the same message on two days, and it paid twice.

![Paid twice](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/00-baseline/paid-twice.png)

*Two real runs, two idempotency keys, two payments: $144 for a $72 order.*

The idempotency key from part 1 stops one run from paying twice after a crash. It does nothing for a second run on Tuesday: the agent had no memory. So I added what production demands, one stage at a time. All of it is runnable: **[github.com/brahim-guaali/production-agent-from-first-principles](https://github.com/brahim-guaali/production-agent-from-first-principles)**

## 1. Memory

The platform now remembers each customer: past refunds, and a note each run leaves for the next. Two rules are enforced in code, not trusted to the model: no second refund on one order (§7), and three refunds this month means a manager, even for $15 (§8).

![Without and with memory](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/01-memory/before-after-memory.png)

14 out of 14 right, at a median of 45 seconds a case, and nothing said why. A separate probe did: the project's quota for Gemini 3.5 Flash was **20 requests a day**, and the run was past it. Almost every call got a 429, waited out two back-offs and quietly fell back to Flash-Lite. The model is a dependency that can change under you without failing anything. My client now records which model answered every call.

## 2. Conversations and sub-agents

"Why only $72? I also paid delivery and a tip" is not a new refund request. Every run now belongs to a session, and a follow-up goes to an `explain` step. Its first answer, "fees and tips are excluded", was plausible and not in the policy: the model filled a gap.

So the agent got two specialists with their own tools. A **policy expert** searches the policy and an FAQ before anything is explained, and cites what it found. A **fraud reviewer** takes grey-zone fraud scores.

![The fraud reviewer at work](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/03-sub-agents/fraud-review.png)

For a 0.58 score it pulled the customer's devices, found one shared with an account scored 0.86, and refused. For a 0.47 score it found a device shared within one household and let the refund through. Nobody scripted those steps.

The cost was invisible: one question the policy doesn't cover ("Will you also pay me something for the hour I wasted waiting?") took four searches and 55 seconds.

## 3. Streaming, and whose first token

Chat products stream replies. The usual metric is time to first token. Mine was 0.6 seconds. The customer saw the first word after 15.6.

![First token vs first word](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/04-streaming/first-word.png)

The reply is the last step of the run, so streaming it barely helps. Time to first token is a number about the model; the customer feels the time from *their* message to *their* first word.

## 4. Failures, and "riyal"

Real services answer 500, send half a record, or say 404 because the customer mistyped the order number. The model returns JSON that doesn't fit, or hits a quota. I made every one of those *data*: retried when worth it, recorded when not, and explained to the customer in plain words.

Then guardrails: prompt-injection detection in two layers (cheap rules first, a model check only when they're unsure: one call in 18 messages), and a fact check on the reply. It caught this:

![The riyal reply](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/06-guardrails/riyal.png)

Right decision, right amount, invented currency, because it fit the language. The check runs after the reply is sent (a stream can't be unsent), so a correction follows.

## 5. Traffic

Eighteen messages, one at a time, say nothing about a Friday night. So I built a replayer: each case cloned onto a fresh order and customer, reworded (typos, all caps, an Arabic greeting), arriving at random, three served at once, one customer in twelve sending the same message twice.

The first six requests found a bug.

![Two runs, one order, two refunds](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/07-traffic/race.png)

The same message twice, 0.2 seconds apart: both runs read a history with no refund in it, and both paid. The fix was one idempotency key per *order* instead of per run; the second payment now comes back "already done".

Then the full batch, 120 requests:

![The queue building up](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/07-traffic/queue-building.gif)

A run took 45 seconds at the median. The median customer waited **6.6 minutes** from message to reply, queue and run together. Six requests arrived a minute, each took about three model calls (389 calls for 120 runs), and my client allows twelve model calls a minute, the project's rate limit: about four requests a minute at best, 3.4 measured. Per-run timings never show it. And halfway through, the model changed:

![The model switch](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/07-traffic/model-switch.png)

3.5 Flash-Lite ran out of its daily quota, the client fell back to 3.1, and every answer stayed right. Only time to first token gave it away: 0.76 seconds before, 3 after.

## 6. Signals

A run can't know what the customer thought of it, or exactly what produced it. The last stage adds both: every run is stamped with its versions (a hash of every prompt, the agent's commit, the model that answered, the environment), and a rating arrives later and is stored against the `run_id` it rates.

The customers here are simulated and rate by a fixed rule: start from the outcome (refund 5★, refusal 1★), lose a star for a wait over a minute and another over two. So the chart shows the rule, not real preferences. What the stage tests is the pipeline: all 22 ratings joined to their runs, with the prompt set and model behind each. With real customers, that join is what traces a bad week to a change. And even the rule makes one point: a correct refusal scores 1★, so happiness and correctness are separate measurements.

![Ratings by wait](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/08-signals/ratings.png)

## What I'd tell myself

1. **Memory is a correctness feature.** Without it, "never refund twice" can't even be checked.
2. **Record which model answered.** Fallbacks are silent, even when every answer is right.
3. **Measure what the customer feels**: message to first word, queue included.
4. **Make failures data**, so the run can route on them.
5. **Run traffic, with repeats and concurrency.** Six requests found what eighteen careful cases never could.
6. **Join feedback to runs, and stamp versions on every run**, so a bad week can be traced to a change.

And the uncomfortable one: after eight stages the agent was far better, and I could say *less* about it than ever. Each finding above came from a probe, a run log or luck. Why did one run take 93 seconds instead of 22? Which step, which call? Nothing could say.

That's part 3: giving the agent a camera.

*Built on personal time with made-up data; it isn't based on any employer's systems.*

---

**The series**, *Building an AI agent from first principles*:
1. [Part 1, graph engineering](https://medium.com/@brahimg/i-rebuilt-one-ai-agent-seven-times-to-understand-graph-engineering-80b9983cd921): from a naive loop to a graph ([code](https://github.com/brahim-guaali/graph-engineering-from-first-principles))
2. **Part 2, a production agent** (this article, [code](https://github.com/brahim-guaali/production-agent-from-first-principles))
3. Part 3, observability: the camera *(3 November)*
4. Part 4, evals: the referee *(10 November)*
