"""HTTP client for the food-delivery platform (services/app.py)."""
import os

import httpx

TIMEOUT = float(os.environ.get("PLATFORM_TIMEOUT", "5"))   # a hung service fails after this


class Platform:
    def __init__(self, url=None, timeout=TIMEOUT):
        self.url = url or os.environ.get("PLATFORM_URL", "http://127.0.0.1:8710")
        self.http = httpx.Client(base_url=self.url, timeout=timeout)

    def _get(self, path, **params):
        r = self.http.get(path, params=params or None)
        r.raise_for_status()
        return r.json()

    def _post(self, path, json=None, headers=None):
        r = self.http.post(path, json=json, headers=headers)
        r.raise_for_status()
        return r.json()

    # reads (slow)
    def get_order(self, order_id):
        return self._get(f"/orders/{order_id}")

    def get_policy(self):
        return self._get("/policy")

    def get_fraud(self, customer):
        return self._get(f"/fraud/{customer}")

    # memory
    def get_history(self, customer):
        return self._get(f"/customers/{customer}/history")

    def add_note(self, customer, run_id, order_id, text):
        return self._post(f"/customers/{customer}/notes", {"run_id": run_id, "order_id": order_id, "text": text})

    # conversations
    def add_turn(self, session_id, customer, role, text, run_id=None):
        return self._post(f"/sessions/{session_id}/turns", {"customer": customer, "role": role,
                                                             "text": text, "run_id": run_id})

    def get_session(self, session_id):
        return self._get(f"/sessions/{session_id}")

    # a person
    def request_approval(self, run_id, order_id, amount, reason):
        return self._post("/approvals", {"run_id": run_id, "order_id": order_id,
                                         "amount": amount, "reason": reason})

    def get_approval(self, approval_id):
        return self._get(f"/approvals/{approval_id}")

    def pending_approvals(self):
        return self._get("/approvals", status="pending")

    def decide_approval(self, approval_id, decision, by="ops-manager"):
        return self._post(f"/approvals/{approval_id}/decision", {"decision": decision, "by": by})

    # money and messages
    def pay(self, order_id, amount, idempotency_key=None):
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self._post("/payments", {"order_id": order_id, "amount": amount}, headers)

    def payments(self, order_id):
        return self._get("/payments", order_id=order_id)

    def notify(self, customer, text):
        return self._post("/notifications", {"customer": customer, "text": text})

    def create_ticket(self, customer, category, priority, summary):
        return self._post("/tickets", {"customer": customer, "category": category,
                                       "priority": priority, "summary": summary})

    # demo controls
    def inject_faults(self, **faults):
        return self._post("/admin/faults", faults)

    def reset(self):
        return self._post("/admin/reset")

    def check(self):
        try:
            self._get("/health")
        except httpx.HTTPError:
            raise SystemExit(f"The platform isn't running at {self.url}. Start it with: make platform")
