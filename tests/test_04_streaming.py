from agent.graph import build
from agentkit.cases import CASES
from agentkit.platform import Platform
from fakes import ScriptedStructured
from judges import answers

GRILL = next(c for c in CASES if c["id"] == "late-grill")


def run(platform, tmp_path, session):
    g = build(ScriptedStructured(answers(order_id="A-9310", amount=72)), Platform(platform), db=tmp_path / "lg.db")
    return g.invoke({"request": {**GRILL, "session_id": session}}, {"configurable": {"thread_id": session}})


def test_the_reply_reaches_the_chat_piece_by_piece(platform, tmp_path):
    state = run(platform, tmp_path, "st1")
    chat = Platform(platform).get_chat("st1")
    assert chat["chunks"] == 4 and chat["text"] == state["reply"]["text"]
    assert state["reply"]["stream"]["aborted"] is False


def test_a_customer_who_leaves_stops_the_stream_and_the_note_says_so(platform, tmp_path):
    p = Platform(platform)
    p.inject_faults(leave_after_chunks=2)
    state = run(platform, tmp_path, "st2")
    assert state["reply"]["stream"]["aborted"] is True
    assert state["reply"]["stream"]["chunks"] == 3          # the third piece got a 409: generation stopped
    assert p.get_chat("st2")["chunks"] == 2
    assert "left before the reply finished" in p.get_history("C-7740")["notes"][0]["text"]
    assert state["payment"]["amount"] == 72                 # the refund itself is not undone
