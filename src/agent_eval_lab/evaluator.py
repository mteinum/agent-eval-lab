"""Evaluate recorded agent runs against small, reviewable scenario contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def evaluate_case(case: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    """Check a single recorded run without calling a model or external service."""
    checks: list[Check] = []
    calls = trace.get("tool_calls", [])
    called_tools = [call.get("name") for call in calls]
    expected_tool = case.get("expected_tool")
    if expected_tool:
        checks.append(Check("expected_tool", expected_tool in called_tools,
                            f"expected {expected_tool!r}; observed {called_tools!r}"))
    forbidden = sorted(set(called_tools) & set(case.get("forbidden_tools", [])))
    checks.append(Check("forbidden_tools", not forbidden,
                        f"forbidden calls observed: {forbidden}" if forbidden else "no forbidden tools called"))

    expected_outcome = case.get("expected_outcome")
    observed_outcome = trace.get("outcome")
    if expected_outcome is not None:
        checks.append(Check("outcome", observed_outcome == expected_outcome,
                            f"expected {expected_outcome!r}; observed {observed_outcome!r}"))

    required_args = case.get("required_args", {})
    matching_calls = [call for call in calls if call.get("name") == expected_tool] if expected_tool else calls
    args_ok = any(all(call.get("arguments", {}).get(key) == value for key, value in required_args.items())
                  for call in matching_calls)
    if required_args:
        checks.append(Check("required_args", args_ok,
                            f"required arguments {required_args!r} found on a matching call" if args_ok
                            else f"no matching call contained required arguments {required_args!r}"))

    response = trace.get("response", "")
    leaked = [term for term in case.get("must_not_contain", []) if term.casefold() in response.casefold()]
    checks.append(Check("sensitive_output", not leaked,
                        f"response contains prohibited terms: {leaked}" if leaked else "no prohibited terms found"))

    checks_json = [{"name": check.name, "passed": check.passed, "detail": check.detail} for check in checks]
    return {
        "id": case["id"],
        "passed": all(check.passed for check in checks),
        "checks": checks_json,
        "tool_calls": called_tools,
        "latency_ms": trace.get("latency_ms"),
    }


def evaluate_suite(suite: dict[str, Any], traces: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Evaluate a suite and report aggregate pass rate and per-case checks."""
    results = []
    for case in suite.get("cases", []):
        trace = traces.get(case["id"], {})
        results.append(evaluate_case(case, trace))
    passed = sum(result["passed"] for result in results)
    total = len(results)
    return {
        "suite": suite.get("name", "unnamed"),
        "passed": passed,
        "total": total,
        "pass_rate": passed / total if total else 0.0,
        "results": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [f"# Evaluation: {report['suite']}", "",
             f"**Result:** {report['passed']}/{report['total']} passed ({report['pass_rate']:.0%})", "",
             "| Case | Result | Tool calls | Failed checks |", "| --- | --- | --- | --- |"]
    for result in report["results"]:
        failed = [check["name"] for check in result["checks"] if not check["passed"]]
        lines.append(f"| `{result['id']}` | {'PASS' if result['passed'] else 'FAIL'} | "
                     f"{', '.join(result['tool_calls']) or '—'} | {', '.join(failed) or '—'} |")
    return "\n".join(lines) + "\n"
