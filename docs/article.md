# My AI agent passed every test. Then I gave it a memory, a queue and real customers

*Part 2 of 4 in **Building an AI agent from first principles**. [Part 1](https://medium.com/@brahimg/i-rebuilt-one-ai-agent-seven-times-to-understand-graph-engineering-80b9983cd921) built a refund agent from a naive loop into a graph. This part takes it to what production throws at it. Real model, real code, real numbers; every image comes from a recorded run.*

---

At the end of part 1, my refund agent got 12 hand-written cases out of 12 right. It ran its lookups in parallel, survived crashes, waited days for a manager and never paid twice.

Then I asked the same customer to send the same message on two different days, and it paid twice.

![Paid twice](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/00-baseline/paid-twice.png)

*Two real runs, two idempotency keys, two payments: $144 for a $72 order.*

The idempotency key from part 1 stops one run from paying twice after a crash. It does nothing for a second run on Tuesday. The agent had no memory of the customer at all.

That was the first of many things a clean test set never shows. So I spent eight stages giving the agent what production would demand, one at a time, and let real runs on a free Gemini key show me what broke. All of it is runnable: **[github.com/brahim-guaali/production-agent-from-first-principles](https://github.com/brahim-guaali/production-agent-from-first-principles)**

## 1. Memory

The platform now remembers each customer: past refunds, how many in the last 30 days, and a one-line note every run leaves for the next. The agent reads it before deciding, and two rules are enforced in code, not trusted to the model: an order that was already refunded can't be refunded again (§7), and a customer with three refunds this month needs a manager even for $15 (§8).

![Without and with memory](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/01-memory/before-after-memory.png)

14 cases out of 14 right. But each case took 45 seconds, and nothing in the output said why. A separate probe did: Gemini 3.5 Flash's free tier allows **20 requests a day**, and we were past it. Every call got a 429, waited out two back-offs, and quietly fell back to Flash-Lite. Fourteen right answers from a model I never chose. My client now records which model answered every call, and I never write a model name in a result without checking it.

## 2. Conversations and sub-agents

"Why only $72? I also paid delivery and a tip" is not a new refund request. Every run now belongs to a session, and a follow-up goes to an `explain` step that answers from the conversation. Its first answer was "fees and tips are excluded". Plausible, and not in the policy: the model filled a gap.

So I gave the agent two specialists with their own tools. A **policy expert** searches the policy and an FAQ before anything is explained (now the answer cites the FAQ entry it found). A **fraud reviewer** takes the cases where the fraud score is neither clearly fine nor clearly bad.

![The fraud reviewer at work](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/03-sub-agents/fraud-review.png)

For a 0.58 score it pulled the customer's devices, saw one shared with two other accounts, checked both, found one at 0.86, and refused. For a 0.47 score it found a device shared within one household and let the refund through. Nobody scripted those steps.

The cost was invisible: one uncovered question ("will you pay me for the hour I waited?") took four searches and 55 seconds.

## 3. Streaming, and whose first token

Chat products stream replies, so the customer sees words appear. The usual metric is time to first token. Mine was 0.6 seconds. The customer saw the first word after 15.6.

![First token vs first word](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/04-streaming/first-word.png)

The reply is the last step of the run, so streaming it doesn't help much. Time to first token is a number about the model. What the customer feels is the time from *their* message to *their* first word.

## 4. Failures, and "riyal"

Real services don't just hang. They answer 500, send half a record, or say 404 because the customer mistyped the order number. The model returns JSON that doesn't fit, or hits a quota. I made every one of those *data*: retried when it's worth retrying, recorded when not, and explained to the customer in plain words ("we couldn't load your order details just now; a colleague will pick this up today").

Then a guardrail stage: prompt-injection detection in two layers (cheap rules on every message, a model check only when the rules are unsure: one model call in 18 messages), and a fact check on the reply. It caught this:

![The riyal reply](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/06-guardrails/riyal.png)

The decision was right, the amount was right, and the currency was invented, because it fit the language. The check runs after the reply is sent (a stream can't be unsent), so a short correction follows.

## 5. Traffic

Eighteen messages, one at a time, say almost nothing about a Friday night. So I built a replayer: each case cloned onto a fresh order and customer, reworded (typos, all caps, an Arabic greeting in front of English), arriving at random, three served at once, and one customer in twelve sending the same message twice.

The first six requests found a real bug.

![Two runs, one order, two refunds](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/07-traffic/race.png)

A customer sent the same message twice, 0.2 seconds apart. Both runs read a history with no refund in it, and both paid. The fix was one idempotency key per *order* instead of per run; the second payment now comes back "already done" and that customer is told so.

Then the full batch, 120 requests:

![The queue building up](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/07-traffic/queue-building.gif)

The agent took 45 seconds at the median. Customers waited **six minutes**, because six arrived a minute and my client allows itself twelve model calls a minute, to stay under the free tier. And halfway through, the model changed:

![The model switch](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/07-traffic/model-switch.png)

3.5 Flash-Lite ran out of its daily quota, the client fell back to 3.1, and every answer stayed right. Only the time to first token gave it away: 0.76 seconds before, 3 after.

## 6. Signals

The last stage asked customers what they thought, and stamped every run with the versions that produced it (a hash of every prompt, the agent's commit, the model that answered, the environment). Two lessons from 22 ratings. A correct refusal still gets 1★: ratings measure happiness, not correctness, and you need both. And waiting costs more stars than any decision:

![Ratings by wait](https://raw.githubusercontent.com/brahim-guaali/production-agent-from-first-principles/main/08-signals/ratings.png)

## What I'd tell myself

1. **Memory is a correctness feature**, not a nice-to-have. Without it, safety rules like "never refund twice" can't even be checked.
2. **Record which model answered.** Fallbacks happen silently, even when every answer is right.
3. **Measure what the customer feels**: message to first word, queue included.
4. **Make failures data**, so the run can route on them and the customer hears what happened.
5. **Run traffic, with repeats and concurrency**, before trusting any result. Six requests found what eighteen careful cases never could.
6. **Ask the customer**, and keep the versions on every run so a bad week can be traced to a change.

And the uncomfortable one: after eight stages, the agent was far better, and I could say *less* about it than ever. Each finding above came from a probe, a run log or luck. Why did one run take 93 seconds instead of 22? Which step, which call, which retry? Nothing could say.

That's part 3: giving the agent a camera.

---

**The series**, *Building an AI agent from first principles*:
1. [Graph engineering](https://medium.com/@brahimg/i-rebuilt-one-ai-agent-seven-times-to-understand-graph-engineering-80b9983cd921): from a naive loop to a graph ([code](https://github.com/brahim-guaali/graph-engineering-from-first-principles))
2. **A production agent** (this article, [code](https://github.com/brahim-guaali/production-agent-from-first-principles))
3. Observability: the camera *(coming)*
4. Evals: the referee *(coming)*
