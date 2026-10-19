"""Stage 04: streamed replies. Time to first token, and a customer who leaves mid-reply.

    make platform                                 # in another terminal
    python 04-streaming/run.py                    # all scenes
    python 04-streaming/run.py stream             # or one: stream | leave
"""
import sys
import threading
import time
import uuid

from agentkit.cases import CASES
from agentkit.platform import Platform
from agentkit.runner import run_case, summary

sys.stdout.reconfigure(line_buffering=True)
STAGE = "04 · streaming"


def watch(platform, session, seen, stop):
    """Play the customer's app: note when each new piece of the reply shows up."""
    t0, last = time.monotonic(), 0
    while not stop.is_set():
        n = platform.get_chat(session)["chunks"]
        if n > last:
            seen.append((round(time.monotonic() - t0, 2), n))
            last = n
        time.sleep(0.05)


def one(platform, cid, leave=None):
    case = next(c for c in CASES if c["id"] == cid)
    session = "sess-" + uuid.uuid4().hex[:6]
    if leave:
        platform.inject_faults(leave_after_chunks=leave)
    seen, stop = [], threading.Event()
    threading.Thread(target=watch, args=(platform, session, seen, stop), daemon=True).start()
    r = run_case({**case, "session_id": session}, platform, STAGE, prefix="st")
    stop.set()
    return r, seen, platform.get_chat(session)


def stream(platform):
    print("\n=== 1. Replies streamed to the customer's chat ===")
    for cid in ("late-grill", "missing-sides", "arabic-late"):
        platform.reset()
        r, seen, chat = one(platform, cid)
        st = r["state"]["reply"]["stream"]
        print(f"  {cid}: {summary(r['state'])} · run {r['seconds']:.1f} s")
        print(f"    reply: first token after {st['ttft']:.2f} s, done after {st['seconds']:.2f} s, "
              f"{st['chunks']} chunks ({st['model']}); {len(chat['text'])} characters reached the chat")
        print(f"    the app saw pieces arrive at {', '.join(f'{t}s' for t, _ in seen[:6])}")
        print(f"    \"{chat['text'][:150]}…\"")


def leave(platform):
    print("\n=== 2. The customer closes the app after the first piece ===")
    r, seen, chat = one(platform, "late-catering", leave=1)
    st = r["state"]["reply"]["stream"]
    print(f"  {summary(r['state'])}; stream aborted: {st['aborted']} after {st['chunks']} chunks "
          f"({st['seconds']:.2f} s); the chat shows {chat['chunks']} piece: \"{chat['text'][:120]}\"")
    print(f"  refund still paid: ${platform.payments('A-7731')['total']:g}; "
          f"note: {platform.get_history('C-1042')['notes'][-1]['text'][-60:]}")


SCENES = {"stream": stream, "leave": leave}

if __name__ == "__main__":
    platform = Platform()
    platform.check()
    for name in sys.argv[1:] or SCENES:
        platform.reset()
        SCENES[name](platform)
