"""Simulated customers rating the replies (stage 08). The traffic is simulated, so the
ratings are too, by a rule stated here rather than hidden in data:

- about half the customers rate at all;
- they start from what they asked for: a refund of the full amount 5, part of it 4, a $5
  credit 3, a referral to a person 3, a refusal 1, a "check the order number" 2;
- a wait of more than 60 s from message to reply costs a star, more than 120 s two;
- a correction message after the reply costs a star (they were told the wrong thing first);
- a little noise (±1 star, one time in five).

The point isn't the rule: it's that ratings arrive after the run, from outside, and have to
be joined back to the run that earned them.
"""
import random

COMMENTS = {5: ["Quick and fair, thanks", "Sorted in a minute", ""], 4: ["Fine", "OK but slow", ""],
            3: ["Meh", "Expected more", ""], 2: ["Took too long", "Not helpful", ""],
            1: ["Useless", "Unfair, I'm leaving the app", "Never ordering again"]}


def rate(record, seed=0):
    """Returns (rating, comment), or None if this customer doesn't rate."""
    rng = random.Random(f"{seed}:{record['id']}")
    if rng.random() < 0.5 or record.get("crashed"):
        return None
    got = record.get("outcome") or {}
    action = got.get("action")
    if action == "refund":
        stars = 5
    elif action == "credit":
        stars = 3
    elif action in ("handoff", "escalate"):
        stars = 2 if any(f.get("kind") == "not_found" for f in record.get("failures", [])) else 3
    else:
        stars = 1
    wait = record.get("seconds", 0) + record.get("queued_s", 0)
    stars -= (wait > 60) + (wait > 120)
    stars -= bool(record.get("output_flags"))
    if rng.random() < 0.2:
        stars += rng.choice([-1, 1])
    stars = max(1, min(5, stars))
    return stars, rng.choice(COMMENTS[stars])
