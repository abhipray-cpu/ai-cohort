"""Engineering-only subprocess crash harness. Never selected by a production setting."""

import argparse
import os

from casecouncil_api.controller import Controller
from casecouncil_api.store import Store
from test_casecouncil_protocol import ControlledProvider

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--fault", default="none")
    args = p.parse_args()
    s = Store(args.root)
    claim = s.claim
    s.claim = lambda: claim(lease=1)
    checkpoint = s.checkpoint

    def capture(job, stage, value):
        checkpoint(job, stage, value)
        if args.fault == stage:
            os._exit(23)

    s.checkpoint = capture
    reserve = s.reserve

    def reservation(*args_, **kwargs):
        aid = reserve(*args_, **kwargs)
        if args.fault == "reservation":
            os._exit(24)
        return aid

    s.reserve = reservation
    Controller(s, ControlledProvider()).once()
