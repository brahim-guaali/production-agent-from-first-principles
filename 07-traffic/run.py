"""Stage 07: traffic. Hundreds of varied requests, arriving at random, served in parallel.

    make platform                                         # in another terminal
    python 07-traffic/run.py                              # 120 requests (about 40 minutes)
    python 07-traffic/run.py 30 --rate 4 --workers 2      # a shorter batch
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentkit.platform import Platform
from agentkit.traffic import Replayer, plan
from report import load, report

sys.stdout.reconfigure(line_buffering=True)
STAGE = "07 · traffic"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int, nargs="?", default=120)
    ap.add_argument("--rate", type=float, default=6.0, help="arrivals per minute (Poisson)")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--faults", type=float, default=0.05, help="share of runs with an injected service fault")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    platform = Platform()
    platform.check()
    platform.reset()
    batch = time.strftime("%Y-%m-%d-%H%M")
    log = Path(__file__).resolve().parent / "data" / f"{batch}.jsonl"
    requests = plan(a.n, seed=a.seed)
    print(f"=== {len(requests)} requests from {len({r['base'] for r in requests})} cases, {a.rate}/min, "
          f"{a.workers} workers, {a.faults:.0%} with a fault, model RPM limit {os.environ.get('GEMINI_RPM', '8')} ===")
    for r in requests[:6]:
        print(f"  e.g. {r['id']:<28} \"{r['message'][:90]}\"")
    Replayer(platform, STAGE, log, workers=a.workers, rate_per_min=a.rate, seed=a.seed, fault_rate=a.faults).run(
        requests, batch=batch)
    print(f"\n=== Report ({log.relative_to(Path.cwd()) if log.is_relative_to(Path.cwd()) else log}) ===")
    report(load(log))
