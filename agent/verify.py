"""The verifier (checks that are certain from the facts), carried over from part 1 (graph engineering)."""


def check(d, order, policy, fraud, history=None, review=None):
    """Every rule here is certain from the facts, so a failure always means the answer is wrong."""
    problems = []
    if d.clause not in policy["clauses"]:
        problems.append(f"clause {d.clause} does not exist; valid clauses are {sorted(policy['clauses'])}")
    if not 0 <= d.amount <= order["total"]:
        problems.append(f"amount ${d.amount} is outside $0 to the order total ${order['total']}")
    if d.action == "refund" and d.amount <= 0:
        problems.append("a refund must have an amount above $0")
    if d.action != "refund" and d.amount != 0:
        problems.append(f"action {d.action} must have amount $0")
    if fraud["score"] > 0.7 and d.action != "refuse":
        problems.append(f"fraud score {fraud['score']} is above 0.7, so §4 requires refuse")
    if d.clause == "§1" and (order["minutes_late"] <= 45 or d.amount != order["total"]):
        problems.append(f"§1 needs more than 45 min late ({order['minutes_late']}) and the full total "
                        f"${order['total']}")
    if d.clause == "§6" and order["minutes_late"] > 45:
        problems.append(f"§6 is for 45 minutes late or less; this order was {order['minutes_late']}")
    if (d.clause == "§5") != (order["status"] == "cancelled_after_cooking"):
        problems.append(f"§5 applies exactly when the order was cancelled after cooking "
                        f"(status: {order['status']})")
    if review is not None and review.get("risk") == "high" and d.action != "refuse":
        problems.append("the fraud review found high risk, so §9 requires refuse")
    if history is not None:
        if order["order_id"] in history["refunded_orders"] and d.action == "refund":
            problems.append(f"order {order['order_id']} was already refunded, so §7 requires refuse")
        if d.clause == "§7" and order["order_id"] not in history["refunded_orders"]:
            problems.append(f"§7 is for orders already refunded; {order['order_id']} was not")
    return problems
