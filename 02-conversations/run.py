"""Stage 02: conversations. Every run belongs to a session; follow-ups are answered from it.

    make platform                                 # in another terminal
    python 02-conversations/run.py                # all scenes
    python 02-conversations/run.py chat           # or one: chat | alone
"""
import sys
import time
import uuid

from agent.graph import build, spec
from agentkit.cases import CASES
from agentkit.llm import Gemini
from agentkit.platform import Platform
from agentkit.trace import Tracer

sys.stdout.reconfigure(line_buffering=True)
STAGE = "02 · conversations"
GRILL = next(c for c in CASES if c["id"] == "late-grill")
TURNS = [
    GRILL["message"],
    "Why only $72? I also paid $6 for delivery and a $5 tip.",
    "That's not fair. I want to talk to a person about the tip.",
]


def say(platform, text, session_id, title):
    llm = Gemini()
    run_id = "c-" + uuid.uuid4().hex[:6]
    tracer = Tracer(STAGE, title, usage=llm.usage, run_id=run_id)
    graph = build(llm, platform, tracer)
    tracer.start(spec(graph))
    t0 = time.monotonic()
    state = graph.invoke({"request": {**GRILL, "message": text, "session_id": session_id}},
                         {"configurable": {"thread_id": run_id}})
    reply = state["reply"]
    path = state["claim"]["kind"] + (" → refund" if "payment" in state else "")
    tracer.finished("done", path)
    return run_id, state, reply, path, llm.usage, time.monotonic() - t0


def chat(platform):
    print("\n=== 1. One conversation, three turns, three runs, one session ===")
    session_id = "sess-" + uuid.uuid4().hex[:6]
    for n, text in enumerate(TURNS, 1):
        run_id, state, reply, path, usage, secs = say(platform, text, session_id, f"turn {n}")
        print(f"  customer: {text}")
        print(f"    run {run_id} · {path} · {secs:.1f} s · {usage}")
        print(f"  agent:    {reply['text']}")
        if reply.get("ticket"):
            print(f"    ticket {reply['ticket']['id']} for a colleague")
    turns = platform.get_session(session_id)["turns"]
    runs = sorted({t["run_id"] for t in turns})
    paid = platform.payments("A-9310")
    print(f"  ✓ session {session_id}: {len(turns)} turns from {len(runs)} runs; "
          f"A-9310 paid {paid['count']} time (${paid['total']:g})")


def alone(platform):
    print("\n=== 2. The same follow-up in a new session: nothing to explain ===")
    run_id, state, reply, path, usage, secs = say(platform, TURNS[1], "sess-" + uuid.uuid4().hex[:6],
                                                  "follow-up without a session")
    print(f"  customer: {TURNS[1]}")
    print(f"    classified as {state['claim']['kind']} (order {state['claim'].get('order_id')}) · "
          f"{'support loop' if 'ticket' in reply or 'queue' in reply else path} · {secs:.1f} s")
    print(f"  agent:    {reply['text'][:240]}")


SCENES = {"chat": chat, "alone": alone}

if __name__ == "__main__":
    platform = Platform()
    platform.check()
    for name in sys.argv[1:] or SCENES:
        platform.reset()
        SCENES[name](platform)
