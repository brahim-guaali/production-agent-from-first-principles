"""Scripted answers for the two judgments, keyed by schema name."""


def answers(kind="refund_request", order_id="A-7731", action="refund", amount=640, clause="§1"):
    def answer(schema, prompt):
        if schema == "Classification":
            return {"kind": kind, "order_id": order_id, "items_claimed": []}
        if schema == "InjectionCheck":
            return {"injection": "pretend" in prompt, "evidence": "pretend" if "pretend" in prompt else ""}
        return {"action": action, "amount": amount, "clause": clause,
                "reason": "late", "customer_message": "Your refund is on its way."}
    return answer


def conversation(first=None, follow_up=None):
    """Turn 1 is a refund request; later turns are follow-ups that get an explanation."""
    base = answers(**(first or {}))

    def answer(schema, prompt):
        later = "Conversation so far" in prompt
        if schema == "Classification" and later:
            return {"kind": "follow_up", "order_id": None, "items_claimed": []}
        if schema == "Explanation":
            return {"answer": "The refund covers the order total under §1.", "clause": "§1",
                    "wants_person": "person" in prompt, **(follow_up or {})}
        return base(schema, prompt)
    return answer
