"""Seed data for the food-delivery platform. All made up.

Each order comes with the times the platform recorded, so lateness is a fact computed by
code (`minutes_late`), not something we ask a model to work out.
"""

POLICY_VERSION = "v5"

POLICY = {
    "§1": "Delivered more than 45 minutes after the promised time: full refund of the order total.",
    "§2": "Missing or spoiled items: refund the price of those items only.",
    "§3": "Refunds over $500 need an operations manager's approval before any money is sent.",
    "§4": "Fraud score above 0.7: refuse the refund and escalate to the risk team.",
    "§5": "Order cancelled by the customer after the restaurant started cooking: no refund, offer $5 credit.",
    "§6": "Late by 45 minutes or less with every item delivered: apologise and offer $5 credit, no refund.",
    "§7": "An order that was already refunded: refuse a second refund.",
    "§8": "Three or more refunds in the last 30 days: any refund needs an operations manager's approval.",
    "§9": "Fraud score between 0.4 and 0.7: a fraud review decides. If it finds high risk, refuse and escalate.",
}

# Answers support agents look up; the policy expert sub-agent searches these with the clauses.
FAQ = {
    "F1": "The order total is the price of the food items. Delivery fees and tips are not part of it.",
    "F2": "Tips go to the rider in full. Support never refunds a tip.",
    "F3": "The delivery fee is refunded only when the whole order never arrived.",
    "F4": "Credit is added to the customer's wallet within an hour and expires after 90 days.",
    "F5": "Refunds reach the original card in 5 to 10 working days.",
}


def _order(order_id, customer, restaurant, items, promised, delivered, status="delivered"):
    total = round(sum(i["price"] * i.get("qty", 1) for i in items), 2)
    h1, m1 = map(int, promised.split(":"))
    h2, m2 = map(int, delivered.split(":")) if delivered else (h1, m1)
    return {
        "order_id": order_id, "customer": customer, "restaurant": restaurant,
        "items": items, "total": total, "status": status,
        "promised_at": promised, "delivered_at": delivered,
        "minutes_late": max(0, (h2 * 60 + m2) - (h1 * 60 + m1)) if delivered else 0,
    }


ORDERS = {o["order_id"]: o for o in [
    _order("A-7731", "C-1042", "Saffron Kitchen",
           [{"name": "Catering tray for 40 (biryani, salads, desserts)", "price": 640}], "13:00", "14:10"),
    _order("A-8120", "C-2210", "Sweet Corner",
           [{"name": "Chicken shawarma plate", "price": 28}, {"name": "Kunafa", "price": 9, "qty": 2}],
           "20:30", "20:25"),
    _order("A-9002", "C-4410", "Burger Lab",
           [{"name": "Double smash burger meal", "price": 42.5, "qty": 2}], "19:00", "19:20"),
    _order("A-9100", "C-5520", "Sushi Den",
           [{"name": "Party sushi platter", "price": 120}], "21:00", "21:05"),
    _order("A-9205", "C-6630", "Pasta Bar",
           [{"name": "Truffle pasta", "price": 32}], "12:30", None, status="cancelled_after_cooking"),
    _order("A-9310", "C-7740", "Grill House",
           [{"name": "Mixed grill for two", "price": 72}], "20:00", "20:50"),
    _order("A-9420", "C-8850", "Pizza Forno",
           [{"name": "Margherita pizza", "price": 24}, {"name": "Pepperoni pizza", "price": 27, "qty": 4},
            {"name": "Garlic bread", "price": 9, "qty": 7}], "18:00", "18:10"),
    _order("A-9555", "C-9960", "Taco Stand",
           [{"name": "Taco box", "price": 38}], "13:15", "13:25"),
    _order("A-9660", "C-1170", "Saffron Kitchen",
           [{"name": "Office lunch for 25", "price": 560}], "12:00", "14:00"),
    _order("A-9771", "C-1280", "Burger Lab",
           [{"name": "Classic burger", "price": 54}, {"name": "Soft drink", "price": 4},
            {"name": "Fries", "price": 6}], "21:00", "21:05"),
    _order("A-9880", "C-1390", "Mandi House",
           [{"name": "Lamb mandi", "price": 55}], "14:00", "15:02"),
    _order("A-9935", "C-3570", "Noodle Box",
           [{"name": "Pad thai", "price": 31}, {"name": "Spring rolls", "price": 17}], "19:30", "20:41"),
    _order("A-9940", "C-4321", "Sweet Corner",
           [{"name": "Chicken shawarma plate", "price": 28}, {"name": "Baklava box", "price": 12}],
           "21:00", "21:04"),
    _order("A-9945", "C-4455", "Pasta Bar",
           [{"name": "Lasagne", "price": 34}, {"name": "Tiramisu", "price": 11}], "20:15", "20:20"),
    _order("A-9990", "C-2468", "Burger Lab",
           [{"name": "Classic burger", "price": 54}, {"name": "Milkshake", "price": 15}], "20:00", "20:10"),
]}

FRAUD = {
    "C-5520": {"score": 0.86, "signals": ["7 refund claims in 30 days", "new device", "address changed today"]},
    "C-4321": {"score": 0.58, "signals": ["account 3 weeks old", "new device"]},
    "C-4455": {"score": 0.47, "signals": ["new device"]},
}
# What the platform remembers about a customer before any run: refunds paid in the past
# (days_ago is turned into a date when asked). Refunds the agent pays are added from the
# payments table, so the history grows as the agent works.
HISTORY = {
    "C-3570": {"orders_90d": 14, "refunds": [
        {"order_id": "A-9935", "amount": 48, "days_ago": 2, "reason": "late delivery"}]},
    "C-2468": {"orders_90d": 9, "refunds": [
        {"order_id": "A-8811", "amount": 22, "days_ago": 4, "reason": "missing item"},
        {"order_id": "A-8640", "amount": 35, "days_ago": 11, "reason": "spoiled item"},
        {"order_id": "A-8502", "amount": 18, "days_ago": 19, "reason": "missing item"},
        {"order_id": "A-8377", "amount": 41, "days_ago": 27, "reason": "late delivery"}]},
}
DEFAULT_HISTORY = {"orders_90d": 6, "refunds": []}

# Device signals the fraud reviewer can pull: which devices the customer used, and which
# other accounts share them.
DEVICES = {
    "C-4321": [{"device": "dev-77ab", "first_seen_days": 9, "shared_with": ["C-5520", "C-6012"]}],
    "C-4455": [{"device": "dev-31cd", "first_seen_days": 12, "shared_with": ["C-4456"],
                "note": "C-4456 has the same home address (household)"}],
}

DEFAULT_FRAUD = {"score": 0.08, "signals": ["account older than 2 years", "refund rate below 2%"]}
