from langgraph.types import Command

from agent.graph import build
from agentkit.cases import CASES
from agentkit.platform import Platform
from fakes import ScriptedStructured
from judges import answers


def case(cid):
    return next(c for c in CASES if c["id"] == cid)


def test_history_includes_seeded_refunds_payments_and_notes(platform):
    p = Platform(platform)
    assert p.get_history("C-2468")["refunds_30d"] == 4
    p.pay("A-9310", 72, idempotency_key="r1:refund")
    p.add_note("C-7740", "r1", "A-9310", "refund $72 under §1")
    h = p.get_history("C-7740")
    assert h["refunded_orders"] == ["A-9310"] and h["notes"][0]["text"] == "refund $72 under §1"


def test_a_second_run_cannot_refund_the_same_order(platform, tmp_path):
    """The model keeps saying refund; the verifier, reading the history, never lets it pay twice."""
    grill = case("late-grill")
    model = ScriptedStructured(answers(order_id="A-9310", amount=72))
    for day in (1, 2):
        g = build(model, Platform(platform), db=tmp_path / "lg.db")
        state = g.invoke({"request": grill}, {"configurable": {"thread_id": f"day{day}"}})
    assert Platform(platform).payments("A-9310")["count"] == 1
    assert "already refunded" in state["problems"][0]
    assert state["reply"]["queue"] == "support-escalations"


def test_a_frequent_claimer_needs_a_manager_even_for_15_dollars(platform, tmp_path):
    g = build(ScriptedStructured(answers(order_id="A-9990", amount=15, clause="§2")),
              Platform(platform), db=tmp_path / "lg.db")
    config = {"configurable": {"thread_id": "fc"}}
    g.invoke({"request": case("frequent-claimer")}, config)
    assert g.get_state(config).next == ("approval",)
    state = g.invoke(Command(resume="approved"), config)
    assert state["payment"]["amount"] == 15
