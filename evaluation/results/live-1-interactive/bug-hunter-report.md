# Bug Hunter Report

- **Target:** `.` (whole repository; application code in `demo-app/`)
- **Date:** 2026-11-17
- **Test command:** `cd demo-app && python3 -m pytest -q -p no:cacheprovider`

| Discovered | Confirmed | Fixed | Verified | Unresolved |
| ---------- | --------- | ----- | -------- | ---------- |
| 8          | 8         | 8     | 8        | 0          |

## Executive Summary

The Transaction Manager demo app (`demo-app/`) was checked against its own specification,
`demo-app/EXPECTED_BEHAVIOUR.md`. Eight defects were found:
- seven by `bug-scout`
- one by `test-engineer`

Each was reproduced with a failing test before any code was changed. Each was then fixed with a
minimal change in `transaction_service.py` or `utils.py`. The suite went from **10 passed / 8
failed** at baseline to **85 passed / 0 failed** at the end. All 18 original tests now pass, and 67
new regression tests were added.

One fix needed a second attempt. In Phase 4 I wrongly classified BH-008 as a side effect of
BH-007, and the independent review caught that error. Final verification passed. Two decisions the
specification leaves open still need the user to confirm them (see Remaining Issues).

## Repository Assessment

- **Language and frameworks:** Python 3 only. pytest 9.2.0 is installed. The command line uses
  stdlib `argparse`. The only dependency is `pytest>=7.0` in `demo-app/requirements.txt`.
- **Structure:**
  - `demo-app/app.py` is the CLI entry point and contains the sample data.
  - `demo-app/transaction_service.py` contains `TransactionService`.
  - `demo-app/utils.py` contains the validation, rounding and discount helpers.
  - `demo-app/tests/test_app.py` holds the 18 original tests.
- **Test infrastructure:** `demo-app/pytest.ini` sets `testpaths = tests` and `pythonpath = .`.
  There is no conftest, no CI configuration and no linter configuration.
- **Expected behaviour:** `demo-app/EXPECTED_BEHAVIOUR.md` is the authoritative spec ("where the
  code and this document disagree, this document is correct"). The README, docstrings and existing
  tests also describe behaviour.
- **Git state at the start:** the working tree on `main` (commit `a5a3681`) was clean, with no
  uncommitted changes from the user. `.claude/` holds the tooling and was out of scope.

## Bugs Discovered

| ID | Title | File and location | Severity | Found by | Status |
| -- | ----- | ----------------- | -------- | -------- | ------ |
| BH-001 | `find_duplicates` returns originals and overwrites the store | `demo-app/transaction_service.py`, `find_duplicates` | Critical | bug-scout | Verification passed |
| BH-002 | `total_valid_transactions` adds `abs(amount)`, so refunds raise the total | `demo-app/transaction_service.py`, `total_valid_transactions` | High | bug-scout | Verification passed |
| BH-003 | `get_transaction` raises or returns the wrong record for an invalid index | `demo-app/transaction_service.py`, `get_transaction` | High | bug-scout | Verification passed |
| BH-004 | `average_transaction_value` raises `ZeroDivisionError` when there are no valid records | `demo-app/transaction_service.py`, `average_transaction_value` | High | bug-scout | Verification passed |
| BH-005 | `apply_discount` does not reject a percent outside 0–100 | `demo-app/utils.py`, `apply_discount` | Medium | bug-scout | Verification passed |
| BH-006 | The currency check accepts any 3-character string | `demo-app/utils.py`, `validate_transaction` | Medium | bug-scout | Verification passed |
| BH-007 | `validate_transaction` raises `OverflowError` for a huge int amount | `demo-app/utils.py`, `validate_transaction` | Low | bug-scout | Verification passed |
| BH-008 | `average_transaction_value` can raise `OverflowError` for large valid int amounts | `demo-app/transaction_service.py`, `average_transaction_value` | Low | test-engineer | Verification passed |

## Severity Assessment

Defects were handled in this order: Critical, then High, then Medium, then Low.

- **BH-001, Critical.** Calling `find_duplicates` silently deleted stored records, both the
  duplicates and the invalid ones. That is data loss, and the function returned the wrong result.
- **BH-002, BH-003, BH-004, High.** Core reporting was broken:
  - the net total was wrong whenever a refund was present
  - `show 99` and `--empty summary` crashed the CLI
  - `show -1` displayed the wrong record
- **BH-005, BH-006, Medium.** Wrong behaviour only for particular inputs: an out-of-range percent,
  or a malformed currency code.
- **BH-007, BH-008, Low.** These need amounts near or beyond the float range (about 1.8e308), which
  is a rare edge case. They break the spec's "never raises" guarantees.

## Root-Cause Analysis

### BH-001: `find_duplicates` returns originals and overwrites the store

- **Expected:** return every valid record whose id already appeared in an earlier valid record,
  in insertion order, and leave the store unchanged. Ids A,B,A,C,A return the 3rd and 5th records.
  (Source: EXPECTED_BEHAVIOUR.md, `find_duplicates`; CLI table rows `summary` and `duplicates`.)
- **Actual:** it returned the first record for each id. It then ran
  `self._transactions = unique`, which shrank a 4-record store to 3. Through the CLI, `summary`
  reported 4 duplicates and `duplicates` printed 4 lines.
- **Root cause:**
  - the condition was inverted: the code collected ids it had not seen yet, not repeats
  - the code assigned its result back to the store
- **Symptoms and secondary failures:** wrong CLI `summary` and `duplicates` output. Any later
  calculation on the same service would see a reduced store.

### BH-002: `total_valid_transactions` adds `abs(amount)`

- **Expected:** the sum of the signed amounts. 100, -30, 50 gives 120.0, and the sample data's net
  total is 501.25. (Source: EXPECTED_BEHAVIOUR.md, `total_valid_transactions`;
  `test_total_subtracts_refunds`.)
- **Actual:** 100, -30, 50 gave 180.0, and the sample data gave 541.25.
- **Root cause:** `total += abs(tx["amount"])` threw away the sign of each refund.
- **Symptoms and secondary failures:** wrong net total in CLI `summary`.

### BH-003: `get_transaction` with an invalid index

- **Expected:** return `None` when the index is not an integer, is negative, or is ≥ `count()`;
  never raise. (Source: EXPECTED_BEHAVIOUR.md, `get_transaction`; CLI table row `show 99`.)
- **Actual:** `IndexError` for an out-of-range index, the record counted from the end for a
  negative index, and `TypeError` for `"1"`, `1.5` or `None`.
- **Root cause:** the function indexed the list directly, with no type or range check, so Python's
  own list semantics leaked through.
- **Symptoms and secondary failures:** `app.py show 99` crashed with a traceback. `show -1` printed
  the unlabelled receipt.

### BH-004: `average_transaction_value` with no valid records

- **Expected:** return 0.0 when there are no valid transactions. (Source: EXPECTED_BEHAVIOUR.md,
  `average_transaction_value`; CLI table row `--empty summary`.)
- **Actual:** `ZeroDivisionError`.
- **Root cause:** `total / len(valid)` had no guard for an empty list.
- **Symptoms and secondary failures:** `app.py --empty summary` crashed after printing three lines.

### BH-005: `apply_discount` range check

- **Expected:** a percent below 0 or above 100 raises `ValueError`; 0 and 100 are allowed.
  (Source: EXPECTED_BEHAVIOUR.md, `apply_discount`.)
- **Actual:** `apply_discount(200, 150)` returned -100.0, and `apply_discount(200, -10)` returned
  220.0.
- **Root cause:** the function had no range check.
- **Symptoms and secondary failures:** none beyond the function itself.

### BH-006: Currency format

- **Expected:** exactly three uppercase ASCII letters, reported as one problem when the rule is
  broken. (Source: EXPECTED_BEHAVIOUR.md, Data model table and `validate_transaction`.)
- **Actual:** `usd`, `Usd`, `US1`, `ÄBC`, full-width `ＵＳＤ` and `U D` were all accepted.
- **Root cause:** the check tested only that the value was a string of length 3.
- **Symptoms and secondary failures:** invalid records counted as valid in totals, averages and
  duplicate detection, and `add_transaction` accepted them.

### BH-007: `validate_transaction` with a huge int amount

- **Expected:** never raises. (Source: EXPECTED_BEHAVIOUR.md, `validate_transaction`.)
- **Actual:** `validate_transaction({..., "amount": 10**400})` raised `OverflowError: int too large
  to convert to float`.
- **Root cause:** `math.isnan` and `math.isinf` convert their argument to float, which overflows for
  ints beyond the float range.
- **Symptoms and secondary failures:** the error also escaped from `is_valid_transaction`,
  `add_transaction`, `valid_transactions` and every calculation on a store loaded with such a
  record.

### BH-008: `average_transaction_value` overflow with large valid ints

- **Expected:** never raises for a store that holds only dictionaries. (Source:
  EXPECTED_BEHAVIOUR.md, `average_transaction_value`.)
- **Actual:** the amounts `10**308, 10**308, 1.0` are each valid. The average raised
  `OverflowError: int too large to convert to float`.
- **Root cause:** `sum(...)` starts from the int `0`, so leading int amounts add up as an exact int.
  When a float follows, the int total, now above the float range, is converted to float, and that
  raises.
- **Symptoms and secondary failures:** in Phase 4 I classified this as a secondary failure of
  BH-007, and that was **wrong**. The `test-engineer` review found the input above, which passes
  BH-007's validation and still raises. It has its own root cause and its own fix.

## Repairs Implemented

| Defect | Change | Attempts |
| ------ | ------ | -------- |
| BH-001 | Collect a valid record into `duplicates` when its id is already in `seen`, otherwise add the id to `seen`. The `self._transactions = unique` line is removed. | 1 |
| BH-002 | `total += abs(tx["amount"])` becomes `total += tx["amount"]`. | 1 |
| BH-003 | Before indexing, return `None` unless `index` is an `int` with `0 <= index < len(self._transactions)`. This is a real check, not a try/except. | 1 |
| BH-004 | `if not valid: return 0.0` before the division. | 1 |
| BH-005 | `if percent < 0 or percent > 100: raise ValueError(...)` before computing. The bounds are inclusive, as the spec states. | 1 |
| BH-006 | Add `not all("A" <= c <= "Z" for c in currency)` to the existing currency rule, so a bad currency still produces exactly one problem. | 1 |
| BH-007 | New private helper `_converts_to_finite_float`: `math.isfinite(float(amount))` with only `OverflowError` caught, which returns False. The existing "amount must be finite" message is reused. | 1 |
| BH-008 | `sum(tx["amount"] for tx in valid)` becomes `sum((tx["amount"] for tx in valid), 0.0)`. A float sum overflows to `inf` instead of raising. | 2 |

BH-008 history:
- **Attempt 1:** "no separate change; covered by BH-007". The two tests designed for BH-008 passed,
  so I recorded it as *Verification passed*.
- **Why that was wrong:** those tests only used amounts that BH-007 now rejects as invalid.
- **Correction:** after the review, I reproduced the remaining failure myself and set BH-008 to
  *Verification failed*. Attempt 2 fixed the summation itself.

Every change keeps public signatures and return types. No dependencies were added.

## Files Modified

| File | Change | Defects |
| ---- | ------ | ------- |
| `demo-app/transaction_service.py` | Fixes to `find_duplicates`, `total_valid_transactions`, `get_transaction` and `average_transaction_value` | BH-001, BH-002, BH-003, BH-004, BH-008 |
| `demo-app/utils.py` | Currency rule, overflow-safe finiteness check, discount range check | BH-005, BH-006, BH-007 |
| `demo-app/tests/test_bug_hunter_regressions.py` (new) | 67 reproduction, regression and coverage tests | all |
| `reports/*` (new) | registry, test outputs, verification log, diff, this report | — |

No other file was changed. `demo-app/tests/test_app.py`, `app.py`, the docs and `.claude/` are
untouched. Nothing was committed.

## Verification Results

| Stage | Command | Passed | Failed | Errors |
| ----- | ------- | ------ | ------ | ------ |
| Baseline | `cd demo-app && python3 -m pytest -q -p no:cacheprovider` | 10 | 8 | 0 |
| Final | `cd demo-app && python3 -m pytest -q -p no:cacheprovider` | 85 | 0 | 0 |

**Targeted results** (reproduction tests selected by node id from the registry; full log in
`reports/verification-log.txt`):

| Defect | Targeted tests | Full suite after the fix |
| ------ | -------------- | ------------------------ |
| BH-001 | 9 passed | 34 failed / 49 passed |
| BH-002 | 4 passed | 30 failed / 53 passed |
| BH-003 | 13 passed | 18 failed / 65 passed |
| BH-004 | 3 passed | 15 failed / 68 passed |
| BH-005 | 6 passed | 11 failed / 72 passed |
| BH-006 | 14 passed | 4 failed / 79 passed |
| BH-007 | 2 passed | 83 passed |
| BH-008 (attempt 2) | 3 passed | 85 passed |

In every intermediate run, all remaining failures belonged to defects that were not fixed yet. No
test that passed at baseline ever failed.

**CLI check:** I ran the six commands from the spec's CLI table. All outputs match the spec:
`501.25`, `100.25`, 1 duplicate, the `TXN-1002` line, `TXN-1003`,
`No transaction at position 99.`, `170.00`, and the empty summary.

My first two attempts at this check failed because of my own command errors, not the app:
- a `-I` flag that stopped the imports from resolving
- a zsh loop that didn't split the arguments

Both are noted in the log.

**Linter:** none is configured, so none was run.

**Diff review:** every hunk in `reports/changes.diff` maps to a registry defect.

**Independent review:** `test-engineer` reviewed the diff.
- **BH-001 to BH-007:** judged to address their root causes.
- **BH-008:** a must-fix finding, acted on as described above.
- **An observation:** it corrected an observation I had wrong, which is updated in the registry.

## Before-and-After Comparison

| Defect | Before | After | Reproduction tests |
| ------ | ------ | ----- | ------------------ |
| BH-001 | A,B,A,C returned `[A,B,C]` and the store went from 4 to 3 records | returns `[A(3rd)]`, store unchanged; CLI shows 1 duplicate | `test_find_duplicates_*`, `test_cli_duplicates_prints_one_txn_1002_line` |
| BH-002 | 100,-30,50 gave 180.0; the CLI net total was 541.25 | 120.0; CLI 501.25 | `test_total_subtracts_refunds`, `test_total_spec_example`, `test_total_of_only_refunds_is_negative` |
| BH-003 | `get_transaction(10)` raised `IndexError`; `-1` returned the last record; `show 99` crashed | `None`; `show 99` prints `No transaction at position 99.` | `test_get_transaction_*`, `test_cli_show_missing_position` |
| BH-004 | `ZeroDivisionError`; `--empty summary` crashed | 0.0; the CLI prints `0.00` | `test_average_of_empty_store_is_zero`, `test_average_with_only_invalid_records_is_zero`, `test_cli_empty_summary` |
| BH-005 | `apply_discount(200,150)` returned -100.0 | raises `ValueError`; the boundaries 0 and 100 still work | `test_apply_discount_rejects_*`, `test_apply_discount_boundaries` |
| BH-006 | `usd` was valid | invalid, with exactly one problem | `test_validate_rejects_non_uppercase_ascii_currency`, `test_validate_one_problem_per_broken_rule` |
| BH-007 | `OverflowError` from validation | `["amount must be finite"]`, and 10**308 is still valid | `test_validate_huge_int_amount_never_raises`, `test_validate_accepts_large_float_representable_int` |
| BH-008 | `OverflowError` for 10**308, 10**308, 1.0 | returns `inf`, no exception | `test_average_with_huge_valid_int_amounts_followed_by_float_never_raises` |

Diff excerpt (BH-001):

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

**Decisions for the user to confirm.** The spec does not settle these.
1. **BH-003, bool index.**
   - Current behaviour: `get_transaction(True)` and `get_transaction(False)` behave as 1 and 0,
     because Python treats bool as an int.
   - The spec says only "not an integer". The CLI cannot pass a bool.
   - If bool should return `None`, add `isinstance(index, bool) or` to the check.
   - No test pins this choice yet.
2. **BH-007, ints too large for a float.**
   - Current behaviour: such amounts are reported as "amount must be finite", since the spec treats
     amounts as floats. Ints that fit in a float, such as 10**308, are still valid.
   - No test pins the exact message, because this is my decision, not the spec's.

**Observations not treated as defects**
- After BH-005, `python3 app.py discount 200 150` ends in an uncaught `ValueError` traceback. The
  spec does not define CLI behaviour for an out-of-range percent.
- `format_transaction` uses `:>10.2f`. Running `show` on a loaded record with a non-numeric amount
  would raise. The sample data never triggers this.
- `load()` and `__init__` keep references to the caller's dicts. This matches the spec's "as given".
- `apply_discount` with a NaN percent passes the range check. The spec does not define this case.
- `total_valid_transactions` returns `inf` when valid amounts add up beyond the float range, and
  does not raise. The spec has no never-raises clause for it.

**Limitations of this run**
- Both specialists were really delegated.
- `bug-scout` and `test-engineer` cannot run code, so all execution was done by the orchestrator.
- My original BH-008 classification was wrong, and so was one observation; both were caught only by
  the review.

## Final Assessment

**Passed verification.**
- The final full-suite run has 85 passed, 0 failed, 0 errors.
- No test that passed at baseline regressed.
- All 8 original failures now pass.

Counts: **8 discovered, 8 confirmed, 8 fixed, 8 verified**, 0 unresolved. All changes are left
uncommitted for review.
