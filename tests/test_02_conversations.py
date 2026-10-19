from agent.graph import build, route_after_classify
from agentkit.cases import CASES
from agentkit.platform import Platform
from fakes import ScriptedStructured
from judges import conversation


def turn(g, cid, text, session, n):
    grill = next(c for c in CASES if c["id"] == cid)
    request = {**grill, "message": text, "session_id": session}
    return g.invoke({"request": request}, {"configurable": {"thread_id": f"{session}-{n}"}})


def test_a_follow_up_is_answered_from_the_session_not_refunded_again(platform, tmp_path):
    p = Platform(platform)
    g = build(ScriptedStructured(conversation({"order_id": "A-9310", "amount": 72})), p, db=tmp_path / "lg.db")
    first = turn(g, "late-grill", "Order A-9310 arrived 50 minutes late. Refund please.", "s1", 1)
    second = turn(g, "late-grill", "Why only $72? I also paid delivery.", "s1", 2)
    assert first["payment"]["amount"] == 72
    assert second["reply"]["explanation"]["clause"] == "§1" and "payment" not in second
    assert p.payments("A-9310")["count"] == 1
    roles = [t["role"] for t in p.get_session("s1")["turns"]]
    assert roles == ["customer", "agent", "customer", "agent"]


def test_asking_for_a_person_opens_a_ticket(platform, tmp_path):
    p = Platform(platform)
    g = build(ScriptedStructured(conversation({"order_id": "A-9310", "amount": 72})), p, db=tmp_path / "lg.db")
    turn(g, "late-grill", "Order A-9310 arrived 50 minutes late. Refund please.", "s2", 1)
    state = turn(g, "late-grill", "I want to talk to a person about this.", "s2", 2)
    assert state["reply"]["ticket"]["customer"] == "C-7740"


def test_a_follow_up_without_a_session_goes_to_support():
    """Without earlier turns there is nothing to explain: the message goes to the support loop."""
    assert route_after_classify({"claim": {"kind": "follow_up"}, "session": {"turns": []}}) == "support"
