# Bug Hunter Report

- **Target:** <directory>
- **Date:** <date of the run>
- **Test command:** `<command>`

| Discovered | Confirmed | Fixed | Verified | Unresolved |
| ---------- | --------- | ----- | -------- | ---------- |
| 0          | 0         | 0     | 0        | 0          |

## Executive Summary

<Three to six sentences: what was investigated, how many defects were found
and fixed, the before and after test totals, and whether verification passed.>

## Repository Assessment

<Languages, frameworks, structure, entry points, test infrastructure, where
expected behaviour is documented, git state at the start (including any
uncommitted user changes).>

## Bugs Discovered

<Every defect in the registry, including unconfirmed ones.>

| ID | Title | File and location | Severity | Found by | Status |
| -- | ----- | ----------------- | -------- | -------- | ------ |

## Severity Assessment

<Why each defect has its severity, and the order in which they were handled.>

## Root-Cause Analysis

<One subsection per confirmed defect.>

### BH-001: <title>

- **Expected:** <behaviour> (source: <spec section, test or docstring>)
- **Actual:** <behaviour observed in the reproduction>
- **Root cause:** <why the code does this>
- **Symptoms and secondary failures:** <where it surfaced>

## Repairs Implemented

<One entry per fix: what changed and why this is the minimal change. Include
the number of attempts.>

## Files Modified

| File | Change | Defects |
| ---- | ------ | ------- |

<State explicitly whether any file outside the fixes, tests and reports/ was
changed.>

## Verification Results

| Stage | Command | Passed | Failed | Errors |
| ----- | ------- | ------ | ------ | ------ |
| Baseline | | | | |
| Final | | | | |

<Per-defect targeted test results, linter results if a linter was available,
and the outcome of the diff review.>

## Before-and-After Comparison

<For each fixed defect: the failing behaviour before and the passing
behaviour after, with the reproduction test name. A short diff excerpt is
welcome.>

## Remaining Issues

<Unresolved defects with the reason, confirmed defects left unfixed, failed
tests, observations that were not treated as defects, items needing the
user's decision, and limitations of this run (for example a specialist that
could not be delegated to).>

## Final Assessment

<"Passed verification" or "Did not pass verification", and why. Restate the
four counts: discovered, confirmed, fixed, verified.>
