#!/usr/bin/env python3
"""Score a finished Bug Hunter run in an evaluation sandbox.

    python3 evaluation/score_run.py <sandbox> [--json out.json]

Objective checks only. Detection accuracy and root-cause accuracy need a
person to read the report against the answer key in docs/EVALUATION.md.

What is measured:
  * Repairs: held-out acceptance tests per planted defect (b1..b5, s1).
  * Regressions: held-out regression tests plus the sandbox's own test suite.
  * Unrelated modifications: files changed since the `baseline` tag that are
    outside the files with planted defects, the test directory and reports/.
  * Report completeness: required sections in reports/bug-hunter-report.md.
  * Bug registry: reports/bug-registry.json parses and uses known statuses.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIDDEN_TESTS = HERE / "hidden_tests"

DEFECTS = {
    "b1": "Average crashes on an empty collection",
    "b2": "find_duplicates removes duplicates instead of identifying them",
    "b3": "apply_discount accepts invalid percentages",
    "b4": "get_transaction mishandles invalid indexes",
    "b5": "Total adds refunds instead of subtracting them",
    "s1": "Currency format not validated (stretch, not in baseline tests)",
}

ALLOWED_CHANGES = (
    re.compile(r"^demo-app/utils\.py$"),
    re.compile(r"^demo-app/transaction_service\.py$"),
    re.compile(r"^demo-app/tests/"),
    re.compile(r"^reports/"),
)

REQUIRED_SECTIONS = [
    "Executive Summary",
    "Repository Assessment",
    "Bugs Discovered",
    "Severity Assessment",
    "Root-Cause Analysis",
    "Repairs Implemented",
    "Files Modified",
    "Verification Results",
    "Before-and-After Comparison",
    "Remaining Issues",
    "Final Assessment",
]

KNOWN_STATUSES = {
    "Discovered",
    "Under investigation",
    "Reproduced",
    "Confirmed",
    "Fix proposed",
    "Fix implemented",
    "Verification passed",
    "Verification failed",
    "Unresolved",
}


def run(cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False)


def junit_results(xml_path):
    results = {}
    for case in ET.parse(xml_path).getroot().iter("testcase"):
        failed = any(child.tag in ("failure", "error") for child in case)
        results[case.get("name")] = not failed
    return results


def score_hidden_tests(demo_app):
    env = dict(os.environ, BUG_HUNTER_TARGET=str(demo_app), PYTHONDONTWRITEBYTECODE="1")
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "hidden.xml"
        proc = run(
            [sys.executable, "-m", "pytest", str(HIDDEN_TESTS), "-q", "-p", "no:cacheprovider",
             f"--junitxml={xml_path}", f"--rootdir={HIDDEN_TESTS}"],
            cwd=tmp,
            env=env,
        )
        if not xml_path.exists():
            return {"error": (proc.stdout + proc.stderr)[-2000:]}
        results = junit_results(xml_path)

    groups = {}
    for name, passed in results.items():
        prefix = name.split("_")[1] if name.startswith("test_") else "other"
        group = groups.setdefault(prefix, {"passed": 0, "failed": 0, "failures": []})
        if passed:
            group["passed"] += 1
        else:
            group["failed"] += 1
            group["failures"].append(name)
    return groups


def score_own_suite(demo_app):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=demo_app, env=env)
    lines = proc.stdout.strip().splitlines()
    return {"exit_code": proc.returncode, "summary": lines[-1] if lines else proc.stderr.strip()[-300:]}


def changed_files(sandbox):
    if run(["git", "rev-parse", "--verify", "baseline"], cwd=sandbox).returncode != 0:
        return None
    tracked = run(["git", "diff", "--name-status", "baseline"], cwd=sandbox).stdout.splitlines()
    untracked = run(["git", "ls-files", "--others", "--exclude-standard"], cwd=sandbox).stdout.splitlines()
    changes = [line.split("\t") for line in tracked if line.strip()]
    changes += [["A", path] for path in untracked if path.strip()]
    return [(status, path[-1] if isinstance(path, list) else path) for status, *path in changes]


def score_report(sandbox):
    report = sandbox / "reports" / "bug-hunter-report.md"
    if not report.is_file():
        return {"exists": False, "missing_sections": REQUIRED_SECTIONS}
    headings = [
        line.lstrip("#").strip().lower()
        for line in report.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.startswith("#")
    ]
    missing = [s for s in REQUIRED_SECTIONS if not any(s.lower() in h for h in headings)]
    return {"exists": True, "missing_sections": missing}


def score_registry(sandbox):
    path = sandbox / "reports" / "bug-registry.json"
    if not path.is_file():
        return {"exists": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return {"exists": True, "valid_json": False, "error": str(exc)}
    bugs = data.get("bugs", []) if isinstance(data, dict) else []
    statuses = {}
    for bug in bugs:
        status = bug.get("status", "?") if isinstance(bug, dict) else "?"
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "exists": True,
        "valid_json": True,
        "bug_count": len(bugs),
        "statuses": statuses,
        "unknown_statuses": sorted(set(statuses) - KNOWN_STATUSES),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sandbox")
    parser.add_argument("--json", dest="json_out")
    args = parser.parse_args()

    sandbox = Path(args.sandbox).resolve()
    demo_app = sandbox / "demo-app"
    if not demo_app.is_dir():
        sys.exit(f"error: {demo_app} not found")

    hidden = score_hidden_tests(demo_app)
    if "error" in hidden:
        sys.exit("error: could not run the held-out tests:\n" + hidden["error"])
    own = score_own_suite(demo_app)
    changes = changed_files(sandbox)
    report = score_report(sandbox)
    registry = score_registry(sandbox)

    unrelated = None
    if changes is not None:
        unrelated = [path for _status, path in changes if not any(p.search(path) for p in ALLOWED_CHANGES)]

    benchmark = ["b1", "b2", "b3", "b4", "b5"]
    repaired = {key: hidden.get(key, {}).get("failed", 1) == 0 for key in DEFECTS}
    regression = hidden.get("regression", {"passed": 0, "failed": 0, "failures": []})

    result = {
        "sandbox": str(sandbox),
        "repairs": repaired,
        "benchmark_repaired": sum(repaired[k] for k in benchmark),
        "stretch_repaired": repaired["s1"],
        "hidden_test_groups": hidden,
        "held_out_regression": regression,
        "own_test_suite": own,
        "files_changed": changes,
        "unrelated_files_modified": unrelated,
        "report": report,
        "registry": registry,
    }

    print(f"Sandbox: {sandbox}\n")
    print("| Check | Result |")
    print("| --- | --- |")
    for key, label in DEFECTS.items():
        group = hidden.get(key, {"passed": 0, "failed": 0})
        verdict = "repaired" if repaired[key] else "NOT repaired"
        print(f"| {key.upper()} {label} | {verdict} ({group['passed']}/{group['passed'] + group['failed']} held-out tests) |")
    print(f"| Benchmark repairs (B1-B5) | {result['benchmark_repaired']}/5 |")
    total_reg = regression["passed"] + regression["failed"]
    print(f"| Held-out regression tests | {regression['passed']}/{total_reg} passing |")
    print(f"| Sandbox's own test suite | {own['summary']} |")
    if unrelated is None:
        print("| Unrelated files modified | unknown (no `baseline` tag) |")
    else:
        print(f"| Unrelated files modified | {len(unrelated)}{': ' + ', '.join(unrelated) if unrelated else ''} |")
    if report["exists"]:
        missing = report["missing_sections"]
        print(f"| Report sections | {len(REQUIRED_SECTIONS) - len(missing)}/{len(REQUIRED_SECTIONS)}{' (missing: ' + ', '.join(missing) + ')' if missing else ''} |")
    else:
        print("| Final report generated | No |")
    if registry.get("exists"):
        print(f"| Bug registry | {registry.get('bug_count', 0)} bugs, statuses {registry.get('statuses', {})} |")
    else:
        print("| Bug registry | not present |")

    if changes:
        print("\nFiles changed since baseline:")
        for status, path in changes:
            print(f"  {status}  {path}")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    main()
