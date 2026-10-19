"""Stage 00: the refund agent we start from, and the gaps that make it a toy.

    make platform                                 # in another terminal
    python 00-baseline/run.py                     # all scenes
    python 00-baseline/run.py happy               # or one: happy | twice | support
"""
import sys
import uuid

from langgraph.types import Command

from agent.graph import build, spec
from agentkit.cases import CASES, REFUND
from agentkit.llm import Gemini
from agentkit.platform import Platform
from agentkit.trace import Tracer

sys.stdout.reconfigure(line_buffering=True)
STAGE = "00 · baseline"


def start(title, platform):
    llm = Gemini()
    thread = "b-" + uuid.uuid4().hex[:6]
    tracer = Tracer(STAGE, title, usage=llm.usage, run_id=thread)
    graph = build(llm, platform, tracer)
    tracer.start(spec(graph))
    return graph, tracer, {"configurable": {"thread_id": thread}}, llm


def summary(state):
    d = state.get("decision")
    if state.get("reply", {}).get("ticket"):
        t = state["reply"]["ticket"]
        return f"ticket {t['id']}: {t['category']}, {t['priority']}: {t['summary']}"
    return f"{d['action']} ${d['amount']:g} under {d['clause']}" if d else str(state.get("reply"))


def happy(platform):
    print("\n=== 1. $640 late catering: fan-out, verify, pause for the manager, resume ===")
    graph, tracer, config, llm = start("$640 late catering", platform)
    graph.invoke({"request": REFUND}, config)
    pending = graph.get_state(config)
    print(f"  paused before {pending.next}: {pending.interrupts[0].value['question']}")
    tracer.finished("paused", "waiting for the operations manager")
    platform.decide_approval(pending.interrupts[0].value["approval_id"], "approved")
    state = graph.invoke(Command(resume="approved"), config)
    tracer.finished("done", summary(state))
    print(f"  ✓ {summary(state)}; {llm.usage}")


def twice(platform):
    print("\n=== 2. The same customer asks again the next day: a second run, no memory ===")
    grill = next(c for c in CASES if c["id"] == "late-grill")
    for day in (1, 2):
        graph, tracer, config, llm = start(f"late-grill, day {day}", platform)
        state = graph.invoke({"request": grill}, config)
        tracer.finished("done", summary(state))
        print(f"  day {day}: {summary(state)}  (idempotency key {state['payment']['idempotency_key']})")
    paid = platform.payments("A-9310")
    print(f"  ✗ order A-9310 (a $72 order) was refunded {paid['count']} times, ${paid['total']:g} in total. "
          "Idempotency keys are per run; nothing remembers the customer.")


def support(platform):
    print("\n=== 3. A complaint goes to the support loop ===")
    rude = next(c for c in CASES if c["id"] == "rude-rider")
    graph, tracer, config, llm = start("A complaint: loop inside a node", platform)
    state = graph.invoke({"request": rude}, config)
    tracer.finished("done", summary(state))
    print(f"  ✓ {summary(state)}")


SCENES = {"happy": happy, "twice": twice, "support": support}

if __name__ == "__main__":
    platform = Platform()
    platform.check()
    for name in sys.argv[1:] or SCENES:
        platform.reset()
        SCENES[name](platform)
    print("""
What this agent can't do yet: remember a customer (scene 2 paid twice), hold a conversation
("why only $72?"), cope with a service that answers with an error instead of hanging, or face
real traffic. And when it runs, nobody can say what it did, what it cost, or whether it was
right. Stages 01-05 fix the first list; stages 06-11 the second.""")
