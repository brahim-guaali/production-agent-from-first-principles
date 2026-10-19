from langgraph.types import Command

from agent.graph import build
from agentkit.cases import CASES, REFUND
from agentkit.platform import Platform
from fakes import ScriptedStructured
from judges import answers


def test_the_agent_pauses_for_the_manager_resumes_and_pays_once(platform, tmp_path):
    g = build(ScriptedStructured(answers()), Platform(platform), db=tmp_path / "lg.db")
    config = {"configurable": {"thread_id": "t1"}}
    g.invoke({"request": REFUND}, config)
    assert g.get_state(config).next == ("approval",)
    state = g.invoke(Command(resume="approved"), config)
    assert len(state["evidence"]) == 4                   # order, policy, fraud, history (01)
    payments = Platform(platform).payments("A-7731")
    assert payments["count"] == 1 and payments["payments"][0]["idempotency_key"] == "t1:refund"


def test_a_retry_policy_absorbs_a_hung_lookup(platform, tmp_path):
    Platform(platform).inject_faults(fraud=1)
    dessert = next(c for c in CASES if c["id"] == "missing-dessert")
    g = build(ScriptedStructured(answers(order_id="A-8120", amount=18, clause="§2")),
              Platform(platform, timeout=1), db=tmp_path / "lg.db")
    state = g.invoke({"request": dessert}, {"configurable": {"thread_id": "t2"}})
    assert state["payment"]["amount"] == 18
