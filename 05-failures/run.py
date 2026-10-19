"""Stage 05: failures. Services that answer 500, bad data or 404; broken model output; 429s.

    make platform                                 # in another terminal
    python 05-failures/run.py                     # all scenes
    python 05-failures/run.py flaky               # or one: flaky | down | bad | typo | invalid | ratelimit
"""
import sys

from agentkit.cases import CASES
from agentkit.llm import Gemini
from agentkit.platform import Platform
from agentkit.runner import run_case, summary

sys.stdout.reconfigure(line_buffering=True)
STAGE = "05 · failures"
GRILL = next(c for c in CASES if c["id"] == "late-grill")


def show(r):
    s = r["state"]
    print(f"  → {summary(s)} · {r['seconds']:.1f} s · {r['usage']}")
    for e in s.get("evidence", []):
        if "attempts" in e or "FAILED" in e:
            print(f"    evidence: {e}")
    for f in s.get("failures", []):
        print(f"    failure: {f['service']} {f['kind']} after {f['attempts']} attempts ({f['detail'][:70]})")
    for e in r["usage"].events:
        print(f"    model event: {e}")
    if s.get("failures") or s.get("attempts", 1) > 1:
        print(f"    customer was told: \"{s['reply']['text'][:170]}\"")


def flaky(platform):
    print("\n=== 1. The order service answers 500 twice, then works ===")
    platform.inject_faults(**{"orders:500": 2})
    show(run_case(GRILL, platform, STAGE, "orders 500 ×2", prefix="f"))


def down(platform):
    print("\n=== 2. The order service is down (500 every time) ===")
    platform.inject_faults(**{"orders:500": 10})
    show(run_case(GRILL, platform, STAGE, "orders down", prefix="f"))


def bad(platform):
    print("\n=== 3. A broken order record and a fraud score on the wrong scale ===")
    platform.inject_faults(**{"orders:bad": 1, "fraud:bad": 1})
    show(run_case(GRILL, platform, STAGE, "bad data", prefix="f"))


def typo(platform):
    print("\n=== 4. The customer types an order number that doesn't exist ===")
    show(run_case({**GRILL, "message": "Order A-9301 arrived 50 minutes late. Refund please."},
                  platform, STAGE, "unknown order", prefix="f"))


def invalid(platform):
    print("\n=== 5. The model's decision comes back as broken JSON (injected once) ===")
    llm = Gemini()
    llm.corrupt = {"Decision": 1}
    r = run_case(GRILL, platform, STAGE, "invalid model output", prefix="f", llm=llm)
    print(f"  decide ran {r['state']['attempts']} times")
    show(r)


def ratelimit(platform):
    print("\n=== 6. A real 429: Flash first (free quota: 20 requests a day), Flash-Lite as fallback ===")
    llm = Gemini(models=["gemini-3.5-flash", "gemini-3.5-flash-lite"])
    show(run_case(GRILL, platform, STAGE, "429 and fallback", prefix="f", llm=llm))


SCENES = {"flaky": flaky, "down": down, "bad": bad, "typo": typo, "invalid": invalid, "ratelimit": ratelimit}

if __name__ == "__main__":
    platform = Platform()
    platform.check()
    for name in sys.argv[1:] or SCENES:
        platform.reset()
        SCENES[name](platform)
