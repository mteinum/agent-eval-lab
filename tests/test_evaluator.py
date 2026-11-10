import json
from pathlib import Path

from agent_eval_lab.evaluator import evaluate_suite, render_markdown


EXAMPLES = Path(__file__).parents[1] / "examples"


def load(name):
    return json.loads((EXAMPLES / name).read_text())


def test_good_fixture_passes_and_renders():
    report = evaluate_suite(load("suite.json"), load("traces.good.json"))
    assert report["passed"] == 3
    assert report["total"] == 3
    assert "3/3 passed" in render_markdown(report)


def test_unsafe_fixture_fails_with_specific_checks():
    report = evaluate_suite(load("suite.json"), load("traces.unsafe.json"))
    assert report["passed"] == 0
    first = report["results"][0]
    failures = {check["name"] for check in first["checks"] if not check["passed"]}
    assert {"forbidden_tools", "outcome", "sensitive_output"} <= failures


def test_missing_trace_fails_expected_tool():
    report = evaluate_suite(load("suite.json"), {})
    assert report["passed"] == 0
