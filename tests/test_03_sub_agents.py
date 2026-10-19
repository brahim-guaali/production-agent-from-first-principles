from agent.graph import build, grey_zone
from agentkit.cases import CASES
from agentkit.platform import Platform
from fakes import ScriptedStructured, finish
from judges import answers


def case(cid):
    return next(c for c in CASES if c["id"] == cid)


def run(platform, tmp_path, cid, model):
    g = build(model, Platform(platform), db=tmp_path / "lg.db")
    return g.invoke({"request": case(cid)}, {"configurable": {"thread_id": cid}})


def test_only_grey_scores_go_to_the_fraud_review():
    assert grey_zone({"score": 0.58}) and not grey_zone({"score": 0.86}) and not grey_zone({"score": 0.08})


def test_the_fraud_reviewer_uses_its_tools_and_its_verdict_is_enforced(platform, tmp_path):
    """The reviewer looks at devices, finds a shared one, says high risk. The main model says
    refund anyway; the verifier holds it to §9 and the run escalates without paying."""
    reviewer = [[("get_devices", {"customer": "C-4321"})],
                [("get_fraud_score", {"customer": "C-5520"})],
                finish(risk="high", evidence=["dev-77ab shared with C-5520 (score 0.86)"])]
    model = ScriptedStructured(answers(order_id="A-9940", amount=12, clause="§2"),
                               {"fraud analyst": reviewer, "refund policy": []})
    state = run(platform, tmp_path, "grey-shared-device", model)
    review = state["handoffs"][0]
    assert review["from"] == "refund_agent" and review["to"] == "fraud_review"
    assert [s["tool"] for s in review["steps"]] == ["get_devices", "get_fraud_score"]
    assert "C-5520" in review["steps"][0]["result"]
    assert "§9" in state["problems"][0] and "payment" not in state


def test_a_low_risk_review_lets_the_refund_through(platform, tmp_path):
    state = run(platform, tmp_path, "grey-household",
                ScriptedStructured(answers(order_id="A-9945", amount=11, clause="§2")))
    assert state["fraud_review"]["risk"] == "low" and state["payment"]["amount"] == 11


def test_policy_search_finds_the_faq_on_tips(platform):
    hits = Platform(platform).search_policy("Is the tip refunded?")["results"]
    assert hits[0]["id"] == "F2"
