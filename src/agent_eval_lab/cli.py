"""Command-line interface for offline agent trace evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .evaluator import evaluate_suite, render_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate recorded AI-agent tool-use traces offline.")
    parser.add_argument("suite", type=Path, help="JSON scenario suite")
    parser.add_argument("traces", type=Path, help="JSON file mapping case IDs to recorded traces")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    suite = json.loads(args.suite.read_text())
    traces = json.loads(args.traces.read_text())
    report = evaluate_suite(suite, traces)
    output = json.dumps(report, indent=2) + "\n" if args.format == "json" else render_markdown(report)
    print(output, end="")
    if report["passed"] != report["total"]:
        sys.exit(1)
