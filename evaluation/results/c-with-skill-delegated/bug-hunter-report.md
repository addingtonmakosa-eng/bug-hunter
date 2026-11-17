# Bug Hunter Report

- **Target:** `.` (whole repository; the application is in `demo-app/`)
- **Date:** 2026-11-16
- **Test command:** `cd demo-app && python3 -m pytest -q`

| Discovered | Confirmed | Fixed | Verified | Unresolved |
| ---------- | --------- | ----- | -------- | ---------- |
| 8          | 8         | 7     | 7        | 1          |

## Executive Summary

The repository holds one application, a transaction manager in `demo-app/`
(three Python modules and one test file). Eight defects were discovered and
all eight were reproduced against the specification. Seven were fixed and
verified. One (BH-008), raised late by the fix review, is unresolved because
its fix needs your approval. The test suite went from 10 passed and 8 failed
(18 tests) at baseline to 107 passed and 0 failed (the 18 original tests
plus 89 new test cases). The run passed verification.

Three things qualify that result. BH-008 is a real, reproduced defect that
is still in the code. The specialists were delegated to through a
fallback, so their read-only limit was an instruction and was checked
afterwards, not enforced by Claude Code. And the fix for BH-007 rests on a
choice the specification does not make; it is listed under Remaining Issues
for confirmation.

## Repository Assessment

- **Language:** Python 3, standard library only. **Tests:** pytest,
  configured by `demo-app/pytest.ini` (`testpaths = tests`, `pythonpath = .`).
- **Structure:** `app.py` (command-line entry point with sample data),
  `transaction_service.py` (`TransactionService`: the store and its
  calculations), `utils.py` (validation, rounding, discount).
- **Expected behaviour:** `demo-app/EXPECTED_BEHAVIOUR.md` is the
  specification and says it overrides the code. Also the existing tests,
  docstrings and `demo-app/README.md`.
- **Linter:** none configured in the project, so none was run.
- **Git state at the start:** clean. No uncommitted user changes.
- **Delegation:** `bug-scout` (one run) and `test-engineer` (design run and
  review run) were each delegated with a fallback: the custom agent types
  could not be loaded in this session, so each agent file was given to a
  general subagent as its role. After the test-design run, a checksum of
  every file in the repository matched the checksum taken before it.

## Bugs Discovered

| ID | Title | File and location | Severity | Found by | Status |
| -- | ----- | ----------------- | -------- | -------- | ------ |
| BH-001 | `find_duplicates` overwrites the store and returns the originals instead of the duplicates | `transaction_service.py`, `find_duplicates` | Critical | bug-scout | Verification passed |
| BH-002 | `total_valid_transactions` adds refunds instead of subtracting them | `transaction_service.py`, `total_valid_transactions` | High | bug-scout | Verification passed |
| BH-003 | `average_transaction_value` raises `ZeroDivisionError` when there are no valid transactions | `transaction_service.py`, `average_transaction_value` | High | bug-scout | Verification passed |
| BH-004 | `get_transaction` raises or returns the wrong record for an invalid index | `transaction_service.py`, `get_transaction` | High | bug-scout | Verification passed |
| BH-005 | `apply_discount` accepts percentages outside 0 to 100 | `utils.py`, `apply_discount` | Medium | bug-scout | Verification passed |
| BH-006 | `validate_transaction` accepts three-character currencies that are not uppercase ASCII letters | `utils.py`, `validate_transaction` | Medium | bug-scout | Verification passed |
| BH-007 | `validate_transaction` raises `OverflowError` for an int amount too large for a float | `utils.py`, `validate_transaction` | Low | bug-scout | Verification passed |
| BH-008 | `average_transaction_value` raises `OverflowError` when valid int amounts sum beyond the float range | `transaction_service.py`, `average_transaction_value` | Low | test-engineer (fix review) | Unresolved |

Four further items were recorded as observations, not defects, because the
specification does not cover them. They are listed under Remaining Issues.

## Severity Assessment

- **Critical, BH-001:** calling a read-only query deletes stored records
  (every duplicate and every invalid record). This is data loss, and every
  later calculation runs on the damaged store.
- **High, BH-002 to BH-004:** a core figure is wrong for any data containing
  a refund (BH-002), and two documented commands crash (`--empty summary`,
  `show 99`).
- **Medium, BH-005 and BH-006:** wrong results only for invalid input that
  should have been rejected.
- **Low, BH-007 and BH-008:** crashes that need amounts at or beyond the
  edge of the float range.

Defects were repaired in this order: BH-001, BH-002, BH-003, BH-004,
BH-005, BH-006, BH-007. BH-008 was found after the repairs and was not
repaired.

## Root-Cause Analysis

### BH-001: `find_duplicates` overwrites the store and returns the originals

- **Expected:** every valid record whose id appeared in an earlier valid
  record, in insertion order; the store is not changed (source:
  `EXPECTED_BEHAVIOUR.md`, `find_duplicates`; two existing tests).
- **Actual:** for ids A, B, A, C it returned the first A, B and C, and the
  store shrank from 4 records to 3.
- **Root cause:** two wrong decisions in one loop. The condition kept a
  record when its id had *not* been seen, which builds the de-duplicated
  list, the opposite of what is asked. Then `self._transactions = unique`
  assigned that list to the store, turning a query into a destructive update.
- **Symptoms and secondary failures:** `app.py summary` reported 4
  duplicates and `duplicates` printed four lines. After a call, `count()`,
  totals and averages were computed on the shrunken store.

### BH-002: refunds are added to the total

- **Expected:** the sum of signed amounts; a refund lowers the total
  (source: specification, `total_valid_transactions`, with the example
  100, -30, 50 = 120).
- **Actual:** 180.0 for that example; `summary` printed 541.25, not 501.25.
- **Root cause:** `total += abs(tx["amount"])` discards the sign that marks
  a refund.
- **Symptoms:** the wrong net total on the command line.

### BH-003: the average divides by zero

- **Expected:** `0.0` when there are no valid transactions, including an
  empty store; never raises (source: specification,
  `average_transaction_value`).
- **Actual:** `ZeroDivisionError`, for an empty store and for a store
  holding only invalid records.
- **Root cause:** `total / len(valid)` with no check for an empty list. The
  divisor is the number of *valid* records, so a guard on the store size
  would not be enough.
- **Symptoms:** `app.py --empty summary` crashed after three lines.

### BH-004: invalid indexes

- **Expected:** `None` when the index is not an integer, is negative, or is
  `>= count()`; never raises (source: specification, `get_transaction`).
- **Actual:** `IndexError` past the end, `TypeError` for other types, a
  record counted from the end for a negative index, and a list for a slice.
- **Root cause:** the caller's value went straight to list indexing, so
  Python's list rules applied in place of the specified rule.
- **Symptoms:** `app.py show 99` crashed; the `is None` branch in
  `cmd_show` could never run.

### BH-005: discount percentage is not validated

- **Expected:** `ValueError` for a percent below 0 or above 100 (source:
  specification, `apply_discount`).
- **Actual:** `apply_discount(200, 150)` returned `-100.0`.
- **Root cause:** missing validation. The arithmetic is valid for any
  number, so out-of-range input produced negative or inflated amounts.

### BH-006: currency content is not checked

- **Expected:** exactly three uppercase ASCII letters (source:
  specification, data model table).
- **Actual:** `usd`, `US1`, `U$D`, three spaces and non-ASCII letters were
  all valid.
- **Root cause:** the check covered only the type and the length; the
  content rule was never implemented. No baseline test checked it, which is
  why the baseline suite did not expose this defect.
- **Secondary failures:** such records counted in totals, averages and
  duplicate detection.

### BH-007: oversized int amounts crash validation

- **Expected:** `validate_transaction` never raises (source: specification).
- **Actual:** `OverflowError` for `10**400`.
- **Root cause:** `math.isnan` and `math.isinf` convert their argument to a
  float first, and an int beyond the float range cannot be converted.
- **Secondary failures:** `valid_transactions`, the average, the total and
  `find_duplicates` all call the validator and raised with it.

### BH-008: the average overflows on large valid ints (not fixed)

- **Expected:** never raises; the mean of 10**308, 10**308 and 1.0 is about
  6.67e307, which a float can hold (source: specification,
  `average_transaction_value`).
- **Actual:** `OverflowError`. All three records are valid.
- **Root cause:** the amounts are summed as ints before any conversion, so
  a partial sum leaves the float range although each amount and the mean
  are inside it. Present at baseline; not caused by this run.

## Repairs Implemented

Each fix took one attempt, except BH-004, which took two.

| Defect | Change | Why it is minimal |
| ------ | ------ | ----------------- |
| BH-001 | Collect records whose id *has* been seen; remove the assignment to `self._transactions`. | Same loop and same validity filter; only the condition and the write are changed. |
| BH-002 | `total += tx["amount"]`. | One call removed. |
| BH-003 | Return `0.0` when the list of valid transactions is empty. | Two lines, placed on the list that is the divisor. |
| BH-004 | Return `None` unless the index is an `int` with `0 <= index < count`. | Four lines before the existing lookup. Attempt 1 also rejected `bool` indexes; the fix review pointed out that the specification does not ask for that and that it changed baseline behaviour, so attempt 2 removed the clause. |
| BH-005 | Raise `ValueError` unless `0 <= percent <= 100`. | Two lines; `0` and `100` stay valid. |
| BH-006 | Also require every character to be between `A` and `Z`. | One condition added to the existing check, so the rule still produces one problem. |
| BH-007 | New private helper `_is_finite`, which treats an int that cannot be converted to a float as not finite. | The existing "amount must be finite" branch is reused. See Remaining Issues. |

No public function changed its signature. No dependency was added.

## Files Modified

| File | Change | Defects |
| ---- | ------ | ------- |
| `demo-app/transaction_service.py` | 13 lines added, 7 removed | BH-001, BH-002, BH-003, BH-004 |
| `demo-app/utils.py` | 12 lines added, 2 removed | BH-005, BH-006, BH-007 |
| `demo-app/tests/test_bug_hunter_regressions.py` | New file, 89 test cases | BH-001 to BH-007, plus coverage |
| `reports/` | Registry, report, test outputs, verification log, diff | |

No other file was changed. `demo-app/tests/test_app.py` and `demo-app/app.py`
are untouched. Nothing was committed.

## Verification Results

| Stage | Command | Passed | Failed | Errors |
| ----- | ------- | ------ | ------ | ------ |
| Baseline (18 tests) | `cd demo-app && python3 -m pytest -q` | 10 | 8 | 0 |
| Reproduction (105 test cases, code unchanged) | same | 56 | 49 | 0 |
| After the seventh fix (105 test cases) | same | 105 | 0 | 0 |
| Final, after acting on the fix review (107 test cases) | same | 107 | 0 | 0 |

Per-defect results, from `reports/verification-log.txt`:

| Defect | Targeted tests after the fix | Full suite after the fix |
| ------ | ---------------------------- | ------------------------ |
| BH-001 | 10 passed | 39 failed, 66 passed |
| BH-002 | 8 passed | 34 failed, 71 passed |
| BH-003 | 8 passed (see note) | 31 failed, 74 passed |
| BH-004 | 15 passed; attempt 2: 17 passed | 19 failed, 86 passed; attempt 2: 107 passed |
| BH-005 | 10 passed | 13 failed, 92 passed |
| BH-006 | 19 passed | 3 failed, 102 passed |
| BH-007 | 14 passed | 105 passed |

After every fix, the set of failing tests was compared with the set before
it. No test that passed before a fix failed after it.

**Note on BH-003.** Its first targeted run reported 1 failed, 8 passed, and
the defect was recorded as *Verification failed*. The cause was the
orchestrator's test selection: the keyword `average` also matched
`test_average_does_not_raise_for_int_too_large_for_float`, which belongs to
BH-007 and was not fixed yet. The fix was not changed. Re-run with BH-003's
own tests, 8 passed. The BH-004 fix had already been applied by then, which
is out of order; the two fixes are in different methods.

- **Linter:** not run; the project has none configured.
- **Diff review:** `git status` shows two modified source files, one new
  test file and `reports/`. Every hunk in `reports/changes.diff` maps to a
  defect above.
- **Fix review by test-engineer:** all seven fixes were judged "addresses
  root cause", with no broad exception handlers, special-cased inputs or
  weakened assertions, and every hunk mapped to a defect. The reviewer had
  not run anything. Its points, and what was done:

  | Point raised | Action |
  | ------------ | ------ |
  | The average can still raise for valid ints whose sum leaves the float range. | Reproduced with a one-off script (`OverflowError`). Registered as BH-008, unresolved. |
  | BH-004's `bool` clause decides something the specification does not. | Clause removed (attempt 2); re-verified. |
  | "Store unchanged" tests compare against a shallow copy. | Added `test_find_duplicates_does_not_modify_record_contents` (deep copy). Passes. |
  | Nothing pins an integer-valued float index. | Added `test_get_transaction_integer_valued_float_index_returns_none`. Passes. |
  | Nothing pins that a NaN percent raises. | Not added: the specification names only "below 0 or above 100". Listed below. |
  | BH-007's classification of `10**400` is a decision, and unpinned. | Left unpinned until the decision is confirmed. Listed below. |

## Before-and-After Comparison

| Defect | Before | After | Reproduction test |
| ------ | ------ | ----- | ----------------- |
| BH-001 | ids A, B, A, C: returned 3 records; store went from 4 to 3 | returns the second A; store unchanged | `test_find_duplicates_returns_the_repeated_record`, `test_find_duplicates_leaves_the_store_unchanged` |
| BH-002 | `summary` net total `541.25` | `501.25` | `test_total_subtracts_refunds`, `test_cli_summary_net_total` |
| BH-003 | `--empty summary`: `ZeroDivisionError` | average `0.00` | `test_average_of_empty_store_is_zero`, `test_cli_empty_summary` |
| BH-004 | `show 99`: `IndexError` | `No transaction at position 99.` | `test_get_transaction_out_of_range_returns_none`, `test_cli_show_out_of_range_prints_message` |
| BH-005 | `apply_discount(200, 150)` returned `-100.0` | raises `ValueError` | `test_apply_discount_rejects_percent_above_100` |
| BH-006 | currency `usd` valid | one problem reported | `test_validate_rejects_lowercase_currency` |
| BH-007 | amount `10**400`: `OverflowError` | one problem reported, no exception | `test_validate_does_not_raise_for_int_too_large_for_float` |

```diff
-            if tx["id"] not in seen:
+            if tx["id"] in seen:
+                duplicates.append(tx)
+            else:
                 seen.add(tx["id"])
-                unique.append(tx)
-        self._transactions = unique
-        return unique
+        return duplicates
```

## Remaining Issues

**Decision to confirm (BH-007).** The specification says validation never
raises, but not whether an int such as `10**400` is a valid amount. The fix
treats it as invalid ("amount must be finite"). That is the only option
found that also keeps `average_transaction_value` from raising, because a
valid amount of that size cannot be averaged as a float. If you would
prefer such amounts to be accepted, the average and total need a
specification first.

**Observations, not treated as defects (no specification):**

- `app.py discount 200 150` now ends in an uncaught `ValueError` traceback.
  The specification does not say what the command line should print for an
  invalid percentage, so `app.py` was not changed.
- `apply_discount(200, float("nan"))` now raises `ValueError`, because NaN
  is not between 0 and 100. The specification names only "below 0 or above
  100".
- `get_transaction(True)` returns the record at position 1, as it did at
  baseline, because Python treats a boolean as an integer. The
  specification does not say.
- `app.py validate` reports a lowercase currency as "currency must be a
  three-letter code", which does not mention the uppercase rule. The
  message text is not specified, so it was left as it was.
- `format_transaction` in `app.py` would raise for a loaded record with a
  non-numeric amount. It is not reachable with the sample data.
- `load` stores the caller's dictionaries by reference, which matches the
  specification's wording ("as given").

**Limitations of this run:**

- The specialists ran through the fallback path. Their tool limits were
  not enforced by Claude Code.
- The run was started in one session and resumed in a later one from the
  registry after Phase 2. The bug-scout's findings were taken from the
  registry on resume.
- BH-003's verification was briefly recorded as failed for the reason
  given above.
- Tests ran on one Python version (3.13).

**Unresolved defect: BH-008.** Reproduced, cause known, not fixed. A
correct fix changes how every average is summed, which could change
rounding for ordinary data, and the specification puts decimal precision
out of scope. It needs your approval of an approach. Its reproduction is in
`reports/verification-log.txt`; no failing test was left in the suite.

**Failing tests:** none.

## Final Assessment

**Passed verification.** The final full-suite run has 107 passed and 0
failed, and no test that passed at baseline fails now. Discovered 8,
confirmed 8, fixed 7, verified 7, unresolved 1 (BH-008). One fix (BH-007)
includes a choice that needs the user's confirmation.
