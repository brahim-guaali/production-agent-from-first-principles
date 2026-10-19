"""Stage 03: sub-agents. The main agent hands work to a fraud reviewer and a policy expert.

    make platform                                 # in another terminal
    python 03-sub-agents/run.py                   # all scenes
    python 03-sub-agents/run.py grey              # or one: grey | policy | cases
"""
import sys
import uuid

from agentkit.cases import CASES
from agentkit.platform import Platform
from agentkit.runner import run_case, score_cases, summary

sys.stdout.reconfigure(line_buffering=True)
STAGE = "03 · sub-agents"


def show_handoff(h):
    print(f"    hand-off {h['from']} → {h['to']} ({h.get('seconds', '?')} s): {h['task'][:110]}")
    for st in h["steps"]:
        print(f"      {st['tool']}({', '.join(f'{k}={v}' for k, v in st['args'].items())}) → {st['result'][:90]}")
    print(f"      result: {h['result']}")


def grey(platform):
    print("\n=== 1. Two grey-zone fraud scores: the fraud_review sub-agent decides ===")
    for cid in ("grey-shared-device", "grey-household"):
        platform.reset()
        case = next(c for c in CASES if c["id"] == cid)
        r = run_case(case, platform, STAGE, prefix="s")
        print(f"  {cid} (score {r['state']['fraud']['score']}): {summary(r['state'])}  "
              f"{r['seconds']:.1f} s · {r['usage']}")
        for h in r["state"].get("handoffs", []):
            show_handoff(h)


def policy(platform):
    print("\n=== 2. Follow-ups answered with the policy_expert sub-agent ===")
    grill = next(c for c in CASES if c["id"] == "late-grill")
    session = "sess-" + uuid.uuid4().hex[:6]
    for text in [grill["message"], "Why only $72? I also paid $6 for delivery and a $5 tip.",
                 "Will you also pay me something for the hour I wasted waiting?"]:
        r = run_case({**grill, "message": text, "session_id": session}, platform, STAGE, title=text[:40], prefix="s")
        print(f"  customer: {text}")
        print(f"  agent:    {r['state']['reply']['text']}")
        for h in r["state"].get("handoffs", []):
            show_handoff(h)


def cases(platform):
    print("\n=== 3. All 16 cases ===")
    score_cases(CASES, platform, STAGE)


SCENES = {"grey": grey, "policy": policy, "cases": cases}

if __name__ == "__main__":
    platform = Platform()
    platform.check()
    for name in sys.argv[1:] or SCENES:
        platform.reset()
        SCENES[name](platform)
