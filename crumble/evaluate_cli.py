# SPDX-License-Identifier: Apache-2.0
import json
import sys
from pathlib import Path

from .evaluation import evaluate


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m crumble.evaluate_cli judged-results.jsonl")
    records = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines() if line.strip()]
    print(json.dumps(evaluate(records), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
