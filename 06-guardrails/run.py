"""Stage 06: guardrails. Prompt-injection detection on the way in, a fact check on the way out.

    make platform                                 # in another terminal
    python 06-guardrails/run.py                   # all scenes
    python 06-guardrails/run.py input             # or one: input | output | cases
"""
import sys

from agentkit.cases import CASES
from agentkit.platform import Platform
from agentkit.runner import outcome, run_case, summary

sys.stdout.reconfigure(line_buffering=True)
STAGE = "06 · guardrails"


def case(cid):
    return next(c for c in CASES if c["id"] == cid)


def show_guards(state):
    for e in state.get("guardrails", []):
        print(f"    {e['stage']:<6} {e['check']:<16} {e['verdict']:<8} by {e.get('by', 'code'):<6} {e['evidence']}")


def input_(platform):
    print("\n=== 1. Input guardrail: rules first, a model only when they're unsure ===")
    for cid in ("late-grill", "prompt-injection", "invented-clause", "hey-bot"):
        platform.reset()
        r = run_case(case(cid), platform, STAGE, prefix="g")
        print(f"  {cid}: {summary(r['state'])} · {r['usage'].calls} model calls · {r['seconds']:.1f} s")
        show_guards(r["state"])


def output(platform):
    print("\n=== 2. Output check on streamed replies (the Arabic reply said 'riyal' in stage 04) ===")
    for cid in ("arabic-late", "late-office-lunch", "missing-sides"):
        platform.reset()
        r = run_case(case(cid), platform, STAGE, prefix="g")
        reply = r["state"]["reply"]
        print(f"  {cid}: {summary(r['state'])}")
        print(f"    reply: \"{reply['text'][:140]}\"")
        show_guards({"guardrails": [e for e in r["state"]["guardrails"] if e["stage"] == "output"]})
        if reply.get("correction"):
            print(f"    correction sent: \"{reply['correction']}\"")


def cases(platform):
    print("\n=== 3. All 18 cases: outcome and input-guardrail verdict ===")
    right = guard_right = model_checks = 0
    events = []
    for c in CASES:
        platform.reset()
        r = run_case(c, platform, STAGE, prefix="g")
        ins = [e for e in r["state"].get("guardrails", []) if e["stage"] == "input"]
        verdict = ins[0]["verdict"] if ins else "pass"
        ok, gok = outcome(r) == c["expect"], verdict == c.get("guard", "pass")
        right, guard_right = right + ok, guard_right + gok
        model_checks += any(e.get("by") == "model" for e in ins)
        outs = [e["check"] for e in r["state"].get("guardrails", []) if e["stage"] == "output" and e["verdict"] == "flagged"]
        print(f"  {'✓' if ok else '✗'}{'✓' if gok else '✗'} {c['id']:<24} {summary(r['state']):<34} guard {verdict:<7}"
              + f" {r['seconds']:5.1f} s, {len(r['usage'].events)} model events"
              + (f" output flagged: {outs}" if outs else ""))
        events.extend(r["usage"].events)
    print(f"  outcomes {right}/{len(CASES)}, guardrail verdicts {guard_right}/{len(CASES)}, "
          f"model checks needed: {model_checks}")
    kinds = {}
    for e in events:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print(f"  model events over the run: {kinds}")


SCENES = {"input": input_, "output": output, "cases": cases}

if __name__ == "__main__":
    platform = Platform()
    platform.check()
    for name in sys.argv[1:] or SCENES:
        platform.reset()
        SCENES[name](platform)
