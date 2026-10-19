import httpx

from agent import versions
from agent.graph import build
from agentkit import customers, judgments
from agentkit.cases import CASES
from agentkit.platform import Platform
from fakes import ScriptedStructured
from judges import answers


def test_changing_one_prompt_changes_the_prompt_set(monkeypatch):
    before = versions.run_meta()
    monkeypatch.setattr(judgments, "COMPOSE", judgments.COMPOSE + " Mention the clause.")
    after = versions.run_meta()
    assert before["prompts"]["compose"] != after["prompts"]["compose"]
    assert before["prompts"]["decide"] == after["prompts"]["decide"]
    assert before["prompt_set"] != after["prompt_set"]


def test_every_run_carries_its_versions(platform, tmp_path):
    grill = next(c for c in CASES if c["id"] == "late-grill")
    g = build(ScriptedStructured(answers(order_id="A-9310", amount=72)), Platform(platform), db=tmp_path / "lg.db")
    state = g.invoke({"request": grill}, {"configurable": {"thread_id": "v1"}})
    assert set(state["meta"]) == {"agent", "prompt_set", "prompts", "environment"}


def test_ratings_are_stored_against_the_run(platform):
    p = Platform(platform)
    p.rate("run-1", "C-7740", 4, "OK but slow")
    assert p.feedback("run-1")[0]["rating"] == 4
    assert httpx.post(f"{platform}/feedback", json={"run_id": "x", "customer": "c", "rating": 9}).status_code == 422


def test_the_simulated_customer_follows_its_rule():
    fast_refund = {"id": "a", "outcome": {"action": "refund"}, "seconds": 20, "queued_s": 0}
    slow_refusal = {"id": "b", "outcome": {"action": "refuse"}, "seconds": 130, "queued_s": 10}
    ratings = [customers.rate({**fast_refund, "id": f"a{i}"}) for i in range(40)]
    rated = [r[0] for r in ratings if r]
    assert 10 < len(rated) < 30 and min(rated) >= 4
    assert all(r is None or r[0] == 1 for r in (customers.rate({**slow_refusal, "id": f"b{i}"}) for i in range(20)))
