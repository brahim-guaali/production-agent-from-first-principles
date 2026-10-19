"""Stage 08: outside signals. Customer ratings joined to runs; every run tagged with its versions.

    make platform                                         # in another terminal
    python 08-signals/run.py                              # 40 requests with ratings (about 15 minutes)
    python 08-signals/run.py --report 08-signals/data/<batch>.jsonl
"""
import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "07-traffic"))

from agent.versions import run_meta
from agentkit.platform import Platform
from agentkit.traffic import Replayer, plan
from report import load, pct

sys.stdout.reconfigure(line_buffering=True)
STAGE = "08 · signals"


def avg(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def signals(rows, platform=None, show=print):
    rated = [r for r in rows if r.get("rating")]
    show(f"  {len(rated)} of {len(rows)} customers rated ({len(rated) / len(rows):.0%}); "
         f"average {avg([r['rating'] for r in rated]):.2f} stars")
    if platform is not None:                     # the ratings live on the platform, not in our log
        stored = {f["run_id"]: f["rating"] for f in platform.feedback()}
        joined = sum(1 for r in rated if stored.get(r["run_id"]) == r["rating"])
        show(f"  joined back to their runs by run_id: {joined}/{len(rated)}")
    groups = {
        "by outcome": lambda r: (r.get("outcome") or {}).get("action"),
        "by wait (message to reply)": lambda r: "under 60 s" if r["seconds"] + r["queued_s"] <= 60
        else "60-120 s" if r["seconds"] + r["queued_s"] <= 120 else "over 120 s",
        "by prompt set": lambda r: (r.get("meta") or {}).get("prompt_set"),
        "by environment": lambda r: (r.get("meta") or {}).get("environment"),
    }
    for title, key in groups.items():
        g = defaultdict(list)
        for r in rated:
            g[key(r)].append(r["rating"])
        show(f"  {title}: " + ", ".join(f"{k} {avg(v):.1f}★ ({len(v)})" for k, v in sorted(g.items(), key=str)))
    worst = sorted(rated, key=lambda r: (r["rating"], -r["seconds"]))[:5]
    show("  lowest rated runs:")
    for r in worst:
        show(f"    {r['rating']}★ \"{r.get('comment', '')}\" run {r['run_id']} · {r['summary']} · "
             f"{r['seconds'] + r['queued_s']:.0f} s wait · prompts {r['meta']['prompt_set']} · agent {r['meta']['agent']} "
             f"· {', '.join(r.get('model_versions', []))}")
    versions = {(r["meta"]["agent"], r["meta"]["prompt_set"], r["meta"]["environment"]) for r in rows if r.get("meta")}
    show(f"  versions seen in this batch: {sorted(versions)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int, nargs="?", default=40)
    ap.add_argument("--report")
    a = ap.parse_args()
    platform = Platform()
    if a.report:
        signals(load(a.report))
        sys.exit()
    platform.check()
    platform.reset()
    batch = time.strftime("%Y-%m-%d-%H%M")
    log = Path(__file__).resolve().parent / "data" / f"{batch}.jsonl"
    meta = run_meta("staging")
    print(f"=== {a.n} requests, environment staging, agent {meta['agent']}, prompt set {meta['prompt_set']} ===")
    print("  prompts: " + ", ".join(f"{k} {v}" for k, v in meta["prompts"].items()))
    Replayer(platform, STAGE, log, workers=3, rate_per_min=4, seed=11, fault_rate=0.05, ratings=True,
             environment="staging").run(plan(a.n, seed=11), batch=batch)
    print("\n=== Ratings joined to runs ===")
    signals(load(log), platform)
