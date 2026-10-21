"""Owned deterministic provider in a real child, exclusively for engineering tests."""

import argparse
import json
import os

from contracts.shelfproof import CorrectionPlan, Draft, PlanItem
from shelfproof_api.store import Store
from shelfproof_api.workflow import Worker
from test_shelfproof_core import evaluation


class Controlled:
    last_receipt = None

    def generate(self, *, prompt, schema):
        context = json.loads(prompt)
        facts = context["facts"]
        if context["role"] == "independent listing evaluator":
            result = evaluation(2 if "700 g" in context["draft"]["title"] else 4)
        elif context["role"] == "correction planner":
            result = CorrectionPlan(
                items=[
                    PlanItem(
                        finding_id=key,
                        operation="replace_from_fact",
                        rationale="Use approved package facts",
                        refs=["net_quantity"],
                    )
                    for key, value in context["findings"].items()
                    if value["severity"] != "minor"
                ]
            )
        else:
            quantity = "700" if context["role"] == "producer" else facts["net_quantity"]
            result = Draft(
                title=f"{facts['brand']} {facts['name']} {quantity} {facts['net_unit']}",
                description=facts["ingredients"],
            )
        self.last_receipt = {"audited": True, "input_tokens": 10, "output_tokens": 5}
        return result.model_dump_json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--fault")
    args = parser.parse_args()
    store = Store(args.root)
    checkpoint = store.checkpoint
    reserve = store.reserve

    def save(task, lease, kind, body):
        checkpoint(task, lease, kind, body)
        if kind == "stages" and body["stage"] == args.fault:
            os._exit(23)

    def charge(*values, **kwargs):
        attempt = reserve(*values, **kwargs)
        if args.fault == "reservation":
            os._exit(24)
        return attempt

    store.checkpoint = save
    store.reserve = charge
    Worker(store, Controlled()).run_once()


if __name__ == "__main__":
    main()
