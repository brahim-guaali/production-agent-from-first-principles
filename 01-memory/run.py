"""Stage 01: the agent remembers the customer.

    make platform                                 # in another terminal
    python 01-memory/run.py                       # all scenes
    python 01-memory/run.py twice                 # or one: twice | frequent | cases
"""
import sys
import time
import uuid

from langgraph.types import Command

from agent.graph import build, spec
from agentkit.cases import CASES
from agentkit.llm import Gemini
from agentkit.platform import Platform
from agentkit.trace import Tracer

sys.stdout.reconfigure(line_buffering=True)
STAGE = "01 · memory"


def run_case(case, platform, title=None, manager="approved"):
    """One run from message to reply; a manager answers if the run pauses for one."""
    llm = Gemini()
    thread = "m-" + uuid.uuid4().hex[:6]
    tracer = Tracer(STAGE, title or case["id"], usage=llm.usage, run_id=thread)
    graph = build(llm, platform, tracer)
    tracer.start(spec(graph))
    config = {"configurable": {"thread_id": thread}}
    t0 = time.monotonic()
    state = graph.invoke({"request": case}, config)
    asked = bool(graph.get_state(config).next)
    if asked:
        platform.decide_approval(state["approval_request"]["id"], manager)
        state = graph.invoke(Command(resume=manager), config)
    tracer.finished("done", summary(state))
    return state, asked, llm.usage, time.monotonic() - t0


def summary(state):
    d = state.get("decision")
    if state.get("reply", {}).get("queue") == "support-escalations":
        return f"escalated: {state['reply']['why']}"
    if state.get("reply", {}).get("ticket"):
        return f"ticket: {state['reply']['ticket']['category']}"
    return f"{d['action']} ${d['amount']:g} under {d['clause']}" if d else str(state.get("reply"))


def case(cid):
    return next(c for c in CASES if c["id"] == cid)


def twice(platform):
    print("\n=== 1. The same $72 request on two days: the second run reads the history ===")
    for day in (1, 2):
        state, _, usage, secs = run_case(case("late-grill"), platform, f"late-grill, day {day}")
        h = state["history"]
        print(f"  day {day}: {summary(state)}  (history before: refunded orders {h['refunded_orders']}, "
              f"{len(h['notes'])} notes)  {secs:.1f} s, {usage.calls} model calls")
        if day == 2:
            print(f"    reason: {state['decision']['reason']}")
    paid = platform.payments("A-9310")
    print(f"  ✓ order A-9310 refunded {paid['count']} time, ${paid['total']:g} (stage 00: twice, $144)")
    notes = platform.get_history("C-7740")["notes"]
    print(f"  notes left for the next run: {[n['text'][:60] for n in notes]}")


def frequent(platform):
    print("\n=== 2. A $15 missing milkshake from a customer with 4 refunds this month ===")
    state, asked, usage, secs = run_case(case("frequent-claimer"), platform)
    print(f"  {summary(state)}; manager asked: {asked} (amount under $500, but §8: "
          f"{state['history']['refunds_30d']} refunds in 30 days)  {secs:.1f} s")


def cases(platform):
    print("\n=== 3. All 14 cases (12 from before, 2 that need memory) ===")
    right, calls, tokens, seconds = 0, 0, 0, []
    for c in CASES:
        platform.reset()
        state, asked, usage, secs = run_case(c, platform)
        d = state.get("decision") or {}
        got = {"action": "handoff" if state.get("reply", {}).get("ticket") else d.get("action"),
               "amount": d.get("amount", 0) if d.get("action") == "refund" else 0, "approval": asked}
        ok = got == c["expect"]
        right += ok
        calls, tokens = calls + usage.calls, tokens + usage.input_tokens + usage.output_tokens
        seconds.append(secs)
        print(f"  {'✓' if ok else '✗'} {c['id']:<24} {summary(state):<34} {secs:5.1f} s"
              + ("" if ok else f"   expected {c['expect']}"))
    print(f"  {right}/{len(CASES)} right, {calls} model calls, {tokens:,} tokens, "
          f"median {sorted(seconds)[len(seconds) // 2]:.1f} s per case")


SCENES = {"twice": twice, "frequent": frequent, "cases": cases}

if __name__ == "__main__":
    platform = Platform()
    platform.check()
    for name in sys.argv[1:] or SCENES:
        platform.reset()
        SCENES[name](platform)
