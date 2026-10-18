"""Small real-provider capability check on explicitly artificial product inputs."""

import argparse
import json
from pathlib import Path

from catalogbridge_api.model_boundary import InstalledModels
from contracts.catalogbridge import Product


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs=2, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.models[0] == args.models[1]:
        parser.error("new output and distinct models required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for model in args.models:
        try:
            result = InstalledModels().generate_pair(
                Product(id="s", title="Crucial 8GB SODIMM", brand="Crucial"),
                [Product(id="m", title="Crucial 16GB SODIMM", brand="Crucial")],
                model,
                60,
            )
            rows.append(
                {
                    "requested_model": model,
                    "effective_model": result.effective_model,
                    "usage": result.usage.model_dump() if result.usage else None,
                    "audited": result.audited,
                    "elapsed_ms": result.elapsed_ms,
                    "exit_code": result.exit_code,
                    "proposal": json.loads(result.text) if result.text else None,
                }
            )
        except (ValueError, RuntimeError, OSError) as exc:
            rows.append({"requested_model": model, "error_type": type(exc).__name__})
    report = {
        "data": "artificial fixture; not real-world semantic validation",
        "observations": rows,
    }
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {"models": [{k: v for k, v in row.items() if k != "proposal"} for row in rows]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
