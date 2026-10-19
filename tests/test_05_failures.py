from agent.graph import build
from agentkit.cases import CASES
from agentkit.platform import Platform
from fakes import ScriptedStructured
from judges import answers

GRILL = next(c for c in CASES if c["id"] == "late-grill")


def run(platform, tmp_path, request=GRILL, model=None, tid="f"):
    g = build(model or ScriptedStructured(answers(order_id="A-9310", amount=72)), Platform(platform),
              db=tmp_path / "lg.db")
    return g.invoke({"request": request}, {"configurable": {"thread_id": tid}})


def test_two_500s_are_retried_and_the_run_carries_on(platform, tmp_path):
    Platform(platform).inject_faults(**{"orders:500": 2})
    state = run(platform, tmp_path)
    assert state["payment"]["amount"] == 72
    assert any("after 3 attempts" in e for e in state["evidence"])


def test_a_service_that_keeps_failing_escalates_and_the_reply_says_why(platform, tmp_path):
    Platform(platform).inject_faults(**{"orders:500": 5})
    state = run(platform, tmp_path)
    assert state["failures"] == [{"service": "orders", "kind": "http_500", "attempts": 3,
                                  "detail": state["failures"][0]["detail"]}]
    assert "payment" not in state and "couldn't load your order details" in state["reply"]["text"]


def test_bad_data_is_caught_by_the_schema_not_retried(platform, tmp_path):
    Platform(platform).inject_faults(**{"orders:bad": 1, "fraud:bad": 1})
    state = run(platform, tmp_path)
    kinds = {(f["service"], f["kind"], f["attempts"]) for f in state["failures"]}
    assert kinds == {("orders", "bad_data", 1), ("fraud", "bad_data", 1)}


def test_an_unknown_order_asks_the_customer_to_check_the_number(platform, tmp_path):
    state = run(platform, tmp_path, model=ScriptedStructured(answers(order_id="A-0000", amount=72)))
    assert state["failures"][0]["kind"] == "not_found" and "check the order number" in state["reply"]["text"]


def test_invalid_model_output_is_sent_back_to_decide(platform, tmp_path, monkeypatch):
    model = ScriptedStructured(answers(order_id="A-9310", amount=72))
    real, calls = model.structured, {"n": 0}

    def flaky(system, prompt, schema):
        if schema.__name__ == "Decision" and calls["n"] == 0:
            calls["n"] += 1
            return schema.model_validate_json('{"action": "refu')
        return real(system, prompt, schema)
    monkeypatch.setattr(model, "structured", flaky)
    state = run(platform, tmp_path, model=model)
    assert state["attempts"] == 2 and state["payment"]["amount"] == 72
