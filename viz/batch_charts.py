"""Charts for stages 04, 07 and 08, drawn from their real run logs (no numbers typed in).

    python viz/batch_charts.py

  07-traffic/model-switch.png   which model answered each run of the 120-run batch, and its time to first token
  07-traffic/queue.png          every run of that batch: the time it queued and the time it ran
  07-traffic/race.png           the six-request smoke test: the two runs that both refunded one order
  04-streaming/first-word.png   the model's first token vs the customer's first word, per case
  08-signals/ratings.png        average rating by how long the customer waited
"""
import json
import re
from pathlib import Path
from statistics import mean, median

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e9e8e4"
BLUE, ORANGE, RED = "#2a78d6", "#d9730d", "#d03b3b"          # blue/orange: a validated categorical pair


def load(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def axes(figsize=(9, 4.4)):
    fig, ax = plt.subplots(figsize=figsize, dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8.5)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    return fig, ax


def save(fig, path, title, note):
    fig.suptitle(title, x=0.01, ha="left", fontsize=11.5, color=INK)
    import textwrap
    wrapped = textwrap.fill(note, width=int(fig.get_figwidth() * 17))
    lines = wrapped.count("\n") + 1
    fig.text(0.01, 0.01, wrapped, fontsize=8, color=INK2, ha="left", va="bottom", linespacing=1.4)
    fig.tight_layout(rect=(0, 0.035 + 0.035 * lines, 1, 0.95))
    fig.savefig(ROOT / path if not Path(path).is_absolute() else path, facecolor=SURFACE)
    plt.close(fig)


def model_of(r):
    m = r.get("models") or {}
    if m.get("gemini-3.1-flash-lite") and not m.get("gemini-3.5-flash-lite"):
        return "3.1"
    if m.get("gemini-3.5-flash-lite") and not m.get("gemini-3.1-flash-lite"):
        return "3.5"
    return "both"


def model_switch():
    rows = sorted([r for r in load(ROOT / "07-traffic/data/2026-10-20-0137.jsonl") if r.get("ttft")],
                  key=lambda r: r["finished"])
    t0 = rows[0]["finished"]
    fig, ax = axes()
    for label, colour, name in (("3.5", BLUE, "3.5 Flash-Lite (configured)"), ("3.1", ORANGE, "3.1 Flash-Lite (fallback)")):
        rs = [r for r in rows if model_of(r) == label]
        ax.scatter([(r["finished"] - t0) / 60 for r in rs], [r["ttft"] for r in rs], s=26, color=colour,
                   label=f"{name}: median first token {median(r['ttft'] for r in rs):.2f} s, {len(rs)} runs",
                   edgecolors=SURFACE, linewidths=0.8, zorder=3)
    first = next(r for r in rows if model_of(r) == "3.1")
    ax.axvline((first["finished"] - t0) / 60, color=INK2, linestyle=(0, (3, 3)), linewidth=1)
    ax.text((first["finished"] - t0) / 60 + 0.3, ax.get_ylim()[1] * 0.92, "3.5's daily free quota runs out:\n"
            "the client falls back, silently", fontsize=8.5, color=INK2, va="top")
    ax.set_xlabel("minutes into the batch", color=INK2, fontsize=8.5)
    ax.set_ylabel("time to first token of the reply (s)", color=INK2, fontsize=8.5)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK2, loc="upper left")
    save(fig, "07-traffic/model-switch.png", "The model changed in the middle of the batch, and every answer stayed right",
         "Stage 07's 120-run batch, from its run log: each dot is a run's streamed reply, coloured by the model that "
         "answered it (runs where both answered are left out).")


def queue(upto=None, out="07-traffic/queue.png"):
    every = sorted(load(ROOT / "07-traffic/data/2026-10-20-0137.jsonl"), key=lambda r: r["arrived"])
    rows = every[:upto] if upto else every
    fig, ax = axes((9.5, 4.4))
    ax.set_xlim(0, len(every) + 1)
    ax.set_ylim(0, max(r["queued_s"] + r["seconds"] for r in every) / 60 * 1.08)
    xs = range(1, len(rows) + 1)
    ax.bar(xs, [r["queued_s"] / 60 for r in rows], color=ORANGE, width=0.85, label="waiting in the queue")
    ax.bar(xs, [r["seconds"] / 60 for r in rows], bottom=[r["queued_s"] / 60 for r in rows], color=BLUE, width=0.85,
           label="the agent working")
    ax.set_xlabel("request, in order of arrival", color=INK2, fontsize=8.5)
    ax.set_ylabel("minutes from message to reply", color=INK2, fontsize=8.5)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK2, loc="upper left")
    med_q, med_r = median(r["queued_s"] for r in rows) / 60, median(r["seconds"] for r in rows) / 60
    ax.text(2, ax.get_ylim()[1] * 0.78, f"median: {med_q:.1f} min waiting, {med_r:.1f} min working",
            ha="left", va="top", fontsize=9, color=INK)
    save(fig, out, "What customers felt was the queue, not the agent",
         "Stage 07's 120 requests from its run log: 6 arriving a minute, 3 workers, a 12-requests-a-minute model limit.")


def race():
    rows = load(ROOT / "07-traffic/data/2026-10-20-0134-first-6.jsonl")
    t0 = min(r["arrived"] for r in rows)
    fig, ax = axes((9, 3.4))
    ax.grid(False)
    for i, r in enumerate(sorted(rows, key=lambda r: r["arrived"])):
        start = r["arrived"] + r["queued_s"]
        twin = r["base"] == "missing-sides"
        colour = RED if twin else "#c9c8c2"
        ax.barh(i, (start - r["arrived"]), left=r["arrived"] - t0, color="#efe3d3", height=0.55)
        ax.barh(i, r["finished"] - start, left=start - t0, color=colour, height=0.55)
        ax.text(r["finished"] - t0 + 1, i, f"{r['id']} · {r['summary']}", va="center", fontsize=8.5,
                color=INK if twin else INK2)
    ax.set_yticks([])
    ax.invert_yaxis()
    ax.set_xlabel("seconds since the first request", color=INK2, fontsize=8.5)
    ax.set_xlim(0, max(r["finished"] for r in rows) - t0 + 45)
    save(fig, "07-traffic/race.png", "Six requests of traffic, and one order refunded twice",
         "Stage 07's first six requests, from their run log. Red: one customer's message and the same message 0.2 s "
         "later; both ran at once, both read no refund in the history, both paid $10. Beige: time in the queue.")


def first_word():
    text = (ROOT / "04-streaming/output.txt").read_text()
    cases = re.findall(r"  (\S+): .*?· run ([\d.]+) s\n    reply: first token after ([\d.]+) s.*?\n.*?arrive at ([\d.]+)s",
                       text)
    fig, ax = axes((8.5, 3.6))
    names = [c[0] for c in cases]
    model = [float(c[2]) for c in cases]
    customer = [float(c[3]) for c in cases]
    ys = range(len(cases))
    ax.barh([y + 0.18 for y in ys], customer, height=0.34, color=ORANGE, label="the customer's first word (from their message)")
    ax.barh([y - 0.18 for y in ys], model, height=0.34, color=BLUE, label="the model's first token (from its own call)")
    for y, m, c in zip(ys, model, customer):
        ax.text(m + 0.4, y - 0.18, f"{m:.2f} s", va="center", fontsize=8.5, color=INK)
        ax.text(c + 0.4, y + 0.18, f"{c:.1f} s", va="center", fontsize=8.5, color=INK)
    ax.set_yticks(list(ys), names, color=INK2, fontsize=8.5)
    ax.invert_yaxis()
    ax.grid(axis="x", color=GRID)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("seconds", color=INK2, fontsize=8.5)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK2, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    save(fig, "04-streaming/first-word.png", "Time to first token is a number about the model, not about the customer",
         "Stage 04's three streamed replies, from its output: the reply is the run's last step, so streaming it starts late.")


def ratings():
    rows = [r for f in sorted((ROOT / "08-signals/data").glob("*.jsonl")) for r in load(f) if r.get("rating")]
    buckets = [("under 1 min", 0, 60), ("1-2 min", 60, 120), ("over 2 min", 120, 1e9)]
    fig, ax = axes((7, 3.6))
    vals = []
    for label, lo, hi in buckets:
        rs = [r["rating"] for r in rows if lo <= r["seconds"] + r["queued_s"] < hi]
        vals.append((label, mean(rs) if rs else 0, len(rs)))
    ax.bar([v[0] for v in vals], [v[1] for v in vals], color=BLUE, width=0.55)
    for i, (label, m, n) in enumerate(vals):
        ax.text(i, m + 0.08, f"{m:.1f}★ ({n})", ha="center", fontsize=9, color=INK)
    ax.set_ylim(0, 5)
    ax.set_ylabel("average rating", color=INK2, fontsize=8.5)
    ax.set_xlabel("wait, from message to reply", color=INK2, fontsize=8.5)
    save(fig, "08-signals/ratings.png", "Waiting costs stars",
         "Stage 08's 22 rated runs (simulated customers, by the rule in agentkit/customers.py), from its run log.")


def queue_frames(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("f*.png"):
        f.unlink()
    for i, upto in enumerate(range(4, 121, 4)):
        queue(upto, str(out / f"f{i:03d}.png"))


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["queue-frames"]:
        queue_frames(sys.argv[2])
        sys.exit()
    model_switch()
    queue()
    race()
    first_word()
    ratings()
