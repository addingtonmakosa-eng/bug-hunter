# Bug Hunter Report

- **Target:** `.` (whole repository; the application is in `demo-app/`)
- **Date:** 2026-11-16
- **Test command:** `cd demo-app && python3 -m pytest`

| Discovered | Confirmed | Fixed | Verified | Unresolved |
| ---------- | --------- | ----- | -------- | ---------- |
| 9          | 8         | 8     | 8        | 1          |

## Executive Summary

The whole repository was investigated; the only application code is the
transaction manager in `demo-app/` (three Python modules, one test file).
Nine defects were entered in the registry. Eight were reproduced against the
specification, fixed with one attempt each, and verified. One (BH-009) is
unresolved because the specification does not say what the result should be.
The test suite went from 10 passed and 8 failed (18 tests) at baseline to 74
passed and 0 failed (the 18 original tests plus 56 new test cases). The run
passed verification: the final full-suite run has no failures and no test
that passed at baseline fails now.

Neither specialist subagent could be used. This session has no Agent or Task
tool, so `bug-scout` and `test-engineer` were not delegated to. Discovery,
test design and fix review were done inline by the orchestrator, following
`.claude/agents/bug-scout.md` and `.claude/agents/test-engineer.md`. No
independent review took place.

## Repository Assessment

- **Languages and frameworks:** Python 3 (interpreter used: 3.13.18; the
  README asks for 3.9 or later). The application uses only the standard
  library (`argparse`, `math`). pytest 9.1.1 is the test framework.
- **Structure:**
  - `demo-app/app.py`: command-line entry point with built-in sample data.
  - `demo-app/transaction_service.py`: `TransactionService`, the in-memory
    store and its calculations.
  - `demo-app/utils.py`: validation, rounding and discount helpers.
  - `demo-app/tests/test_app.py`: the existing test suite, 18 tests.
  - `demo-app/pytest.ini` (`testpaths = tests`, `pythonpath = .`) and
    `demo-app/requirements.txt` (`pytest>=7.0`).
  - `.claude/`: the bug-hunter skill, two agent definitions, a safety hook
    and settings. Tooling, not application code.
- **Entry point:** `python3 app.py <command>` run from `demo-app/`.
- **Test command:** taken from `demo-app/README.md` (`python3 -m pytest`,
  run from `demo-app/`).
- **Sources of expected behaviour:** `demo-app/EXPECTED_BEHAVIOUR.md` (the
  specification, which states that it wins over the code), the README, the
  existing tests and the docstrings.
- **Linter:** none configured.
- **Git state at the start:** a git repository with one commit
  (`4c98768 Baseline: broken demo app`) and a clean working tree. There were
  no uncommitted user changes, so `preexisting_uncommitted_files` is empty.
- **Dependencies:** nothing was installed or upgraded.

## Bugs Discovered

All nine were found by the orchestrator doing the bug-scout investigation
inline. Six of them were already demonstrated by failing tests in
`tests/test_app.py`.

| ID | Title | File and location | Severity | Found by | Status |
| -- | ----- | ----------------- | -------- | -------- | ------ |
| BH-001 | `find_duplicates` destroys stored records | `demo-app/transaction_service.py`, `find_duplicates` (line 54 at baseline) | Critical | orchestrator (inline scout) | Verification passed |
| BH-002 | `find_duplicates` returns the first occurrence of each id instead of the repeats | `demo-app/transaction_service.py`, `find_duplicates` (lines 48-55 at baseline) | High | orchestrator (inline scout) | Verification passed |
| BH-003 | `average_transaction_value` raises `ZeroDivisionError` with no valid transactions | `demo-app/transaction_service.py`, `average_transaction_value` (line 44 at baseline) | High | orchestrator (inline scout) | Verification passed |
| BH-004 | `total_valid_transactions` adds refunds instead of subtracting them | `demo-app/transaction_service.py`, `total_valid_transactions` (line 65 at baseline) | High | orchestrator (inline scout) | Verification passed |
| BH-005 | `get_transaction` raises or returns the wrong record for an invalid index | `demo-app/transaction_service.py`, `get_transaction` (line 59 at baseline) | Medium | orchestrator (inline scout) | Verification passed |
| BH-006 | `apply_discount` accepts a percent below 0 or above 100 | `demo-app/utils.py`, `apply_discount` (lines 50-53 at baseline) | Medium | orchestrator (inline scout) | Verification passed |
| BH-007 | `validate_transaction` accepts any three-character currency | `demo-app/utils.py`, `validate_transaction` (lines 38-40 at baseline) | Medium | orchestrator (inline scout) | Verification passed |
| BH-008 | `validate_transaction` raises `OverflowError` for an int amount too large for a float | `demo-app/utils.py`, `validate_transaction` (line 33 at baseline) | Low | orchestrator (inline scout) | Verification passed |
| BH-009 | `average_transaction_value` raises `OverflowError` when a valid amount is an int too large for a float | `demo-app/transaction_service.py`, `average_transaction_value` (also `total_valid_transactions`, `utils.round_money`) | Low | orchestrator (inline scout) | Unresolved (needs specification) |

## Severity Assessment

Defects were handled in this order: BH-001, BH-002, BH-003, BH-004, BH-005,
BH-006, BH-007, BH-008. BH-009 was not repaired.

- **BH-001, Critical:** data loss. A method that is meant to be a query
  deletes records from the store: every invalid record and every duplicate
  is removed, and all later results are computed on what is left.
- **BH-002, High:** a headline feature ("identifies duplicate
  transactions") returns the wrong records for every input.
- **BH-003, High:** a crash on documented input. An empty store, and
  `app.py --empty summary`, raise instead of reporting `0.0`.
- **BH-004, High:** the net total is wrong whenever the data contains a
  refund, which the sample data does.
- **BH-005, Medium:** wrong only for an invalid index (out of range,
  negative or non-integer); valid positions work.
- **BH-006, Medium:** wrong only for a percent outside 0 to 100.
- **BH-007, Medium:** wrong only for a three-character currency that is not
  three uppercase ASCII letters; such records are then counted as valid.
- **BH-008, Low:** a rare edge case, an int amount beyond the float range
  (about 1.8e308).
- **BH-009, Low:** the same rare input, reaching the calculations.

## Root-Cause Analysis

No defects were merged. BH-001 and BH-002 are in the same function but have
different wrong lines and different failing tests.

### BH-001: `find_duplicates` destroys stored records

- **Expected:** the stored records are not changed in any way; `count()`
  and `all_transactions()` return the same results before and after the call
  (source: `EXPECTED_BEHAVIOUR.md`, `find_duplicates()`, third bullet).
- **Actual:** after the call, a store of 4 records (ids `A`, empty, `A`,
  `B` with a zero amount) reported `count() == 1`.
- **Root cause:** the line `self._transactions = unique` wrote the method's
  working list back over the store.
- **Symptoms and secondary failures:** `count()`, `all_transactions()` and
  every later calculation change after any call. The CLI `summary` calls
  `find_duplicates` last, so its own figures were not affected by this.

### BH-002: `find_duplicates` returns the first occurrence of each id

- **Expected:** every valid record whose id already appeared in an earlier
  valid record, in insertion order; the first record with an id is not
  returned; ids `A, B, A, C, A` return the third and fifth records; no
  duplicates gives `[]` (source: `EXPECTED_BEHAVIOUR.md`,
  `find_duplicates()`).
- **Actual:** the first valid record of each id was returned. The spec
  example returned the first `A`, `B` and `C`; a store without duplicates
  returned all its records.
- **Root cause:** the loop collected a record when its id had *not* been
  seen, and that list was returned. Records whose id had been seen were
  never collected.
- **Symptoms and secondary failures:** `Duplicate records: 4` in the CLI
  `summary` and four lines from the CLI `duplicates` command.

### BH-003: `average_transaction_value` raises `ZeroDivisionError`

- **Expected:** with no valid transactions, including an empty store, it
  returns `0.0`; it never raises for a store that holds only dictionaries
  (source: `EXPECTED_BEHAVIOUR.md`, `average_transaction_value()`; app.py
  table row `--empty summary`).
- **Actual:** `ZeroDivisionError: division by zero` at
  `transaction_service.py:44` for an empty store and for a store holding
  only invalid records.
- **Root cause:** `total / len(valid)` had no guard for an empty list of
  valid transactions.
- **Symptoms and secondary failures:** `app.py --empty summary` printed
  three lines and then ended with a traceback.

### BH-004: `total_valid_transactions` adds refunds

- **Expected:** the sum of the signed amounts; a refund lowers the total;
  `100.0, -30.0, 50.0` total `120.0` (source: `EXPECTED_BEHAVIOUR.md`,
  `total_valid_transactions()`; app.py table row `summary`, net total
  `501.25`).
- **Actual:** `180.0` for the spec example, `280.0` instead of `220.0` in
  the existing test, `25.5` instead of `-25.5` for two refunds.
- **Root cause:** `total += abs(tx["amount"])` discarded the sign that
  marks a refund.
- **Symptoms and secondary failures:** CLI `summary` printed net total
  `541.25` instead of `501.25`.

### BH-005: `get_transaction` with an invalid index

- **Expected:** `None` when the index is not an integer, is negative, or is
  greater than or equal to `count()`; never raises (source:
  `EXPECTED_BEHAVIOUR.md`, `get_transaction(index)`; app.py table row
  `show 99`).
- **Actual:** `IndexError` for index 10, for an index equal to `count()`,
  for index 0 on an empty store and for index -5; index -1 returned the last
  record; `'1'`, `1.5`, `None` and `[0]` raised `TypeError`.
- **Root cause:** the list was indexed directly, so Python list semantics
  applied instead of the specified `None`.
- **Symptoms and secondary failures:** `app.py show 99` ended with an
  `IndexError` traceback.

### BH-006: `apply_discount` accepts an out-of-range percent

- **Expected:** a percent below 0 or above 100 raises `ValueError`; 0
  returns the amount unchanged and 100 returns `0.0` (source:
  `EXPECTED_BEHAVIOUR.md`, `apply_discount(amount, percent)`).
- **Actual:** no exception for 150, -10, 100.01, 1000, -0.01 and -100; a
  result was returned.
- **Root cause:** the range rule was not implemented; the function computed
  straight away.
- **Symptoms and secondary failures:** negative or inflated prices from the
  function and from `app.py discount`.

### BH-007: `validate_transaction` accepts any three-character currency

- **Expected:** currency is exactly three uppercase ASCII letters; each
  broken rule adds one problem (source: `EXPECTED_BEHAVIOUR.md`, data model
  table and `validate_transaction`).
- **Actual:** `[]` for currencies `usd`, `Usd`, `123`, `U$D`, `US ` and
  `ÄÖÜ`. A record with currency `usd` was returned by
  `valid_transactions()` and stored by `add_transaction`.
- **Root cause:** the check covered only the type and the length; the
  "uppercase ASCII letters" part of the rule was missing.
- **Symptoms and secondary failures:** malformed records entered totals,
  averages and duplicate detection.

### BH-008: `validate_transaction` raises `OverflowError`

- **Expected:** never raises; an int amount is always finite, so a non-zero
  int breaks no rule and the result is `[]` (source:
  `EXPECTED_BEHAVIOUR.md`, `validate_transaction` "Never raises" and the
  data model `amount` row).
- **Actual:** `OverflowError: int too large to convert to float` at
  `utils.py:33` for `10**400` and `-(10**400)`.
- **Root cause:** `math.isnan` and `math.isinf` were called on ints as well
  as floats. They convert the argument to a C double, which overflows for a
  very large int.
- **Symptoms and secondary failures:** the same exception from everything
  that validates: `is_valid_transaction`, `add_transaction`,
  `valid_transactions` and all calculations.

BH-009 is not confirmed and has no root-cause entry; see Remaining Issues.

## Repairs Implemented

Each fix took one attempt. No retries were needed.

- **BH-001** (`transaction_service.py`): removed the line
  `self._transactions = unique`. Minimal because the method needs no write
  to the store at all.
- **BH-002** (`transaction_service.py`): the loop now collects a record
  when its id is already in `seen`, otherwise it remembers the id, and the
  collected list is returned. The local list was renamed from `unique` to
  `duplicates` because it no longer holds unique records. That is the only
  rename in the run.
- **BH-003** (`transaction_service.py`): `if not valid: return 0.0` before
  the division. A guard on the cause, not a caught exception.
- **BH-004** (`transaction_service.py`): `abs(tx["amount"])` became
  `tx["amount"]`.
- **BH-005** (`transaction_service.py`): `get_transaction` returns `None`
  unless `index` is an `int` with `0 <= index < len(self._transactions)`.
- **BH-006** (`utils.py`): `if not 0 <= percent <= 100: raise
  ValueError(...)` before computing. Written this way, a NaN percent is
  rejected too.
- **BH-007** (`utils.py`): the currency condition also requires
  `currency.isascii() and currency.isalpha() and currency.isupper()`. The
  problem message is unchanged.
- **BH-008** (`utils.py`): the NaN/infinity check applies only when the
  amount is a `float`.

No public signature or return type changed, and no dependency was added.

## Files Modified

| File | Change | Defects |
| ---- | ------ | ------- |
| `demo-app/transaction_service.py` | Modified: `average_transaction_value`, `find_duplicates`, `get_transaction`, `total_valid_transactions` | BH-001, BH-002, BH-003, BH-004, BH-005 |
| `demo-app/utils.py` | Modified: `validate_transaction`, `apply_discount` | BH-006, BH-007, BH-008 |
| `demo-app/tests/test_bug_hunter_regressions.py` | New: 56 reproduction, regression and coverage test cases | BH-001 to BH-008 |
| `reports/bug-registry.json` | New: registry | all |
| `reports/baseline-test-output.txt` | New: raw baseline output | |
| `reports/reproduction-test-output.txt` | New: raw output of the new tests against unchanged code | |
| `reports/final-test-output.txt` | New: raw final output | |
| `reports/bug-hunter-report.md` | New: this report | |

No file outside the fixes, the tests and `reports/` was changed.
`demo-app/tests/test_app.py` was not edited. Running the tests created the
ignored cache directories `demo-app/.pytest_cache/`, `demo-app/__pycache__/`
and `demo-app/tests/__pycache__/`. Nothing was committed, staged or pushed.

## Verification Results

| Stage | Command | Passed | Failed | Errors |
| ----- | ------- | ------ | ------ | ------ |
| Baseline | `cd demo-app && python3 -m pytest` | 10 | 8 | 0 |
| Final | `cd demo-app && python3 -m pytest` | 74 | 0 | 0 |

The baseline ran 18 tests. The final run has 74: those 18 plus 56 new test
cases. All 10 tests that passed at baseline still pass, and the 8 that
failed at baseline now pass.

The new test file was also run against the unchanged code before any fix:
33 failed (the reproductions) and 23 passed (coverage tests for rules that
already held). Output: `reports/reproduction-test-output.txt`.

Per-defect results, each run straight after its fix:

| Defect | Targeted tests | Full suite after the fix |
| ------ | -------------- | ------------------------ |
| BH-001 | 2 passed | 35 passed, 39 failed; no baseline-passing test failed |
| BH-002 | 5 passed | 41 passed, 33 failed; no baseline-passing test failed |
| BH-003 | 3 passed | 44 passed, 30 failed; no baseline-passing test failed |
| BH-004 | 4 passed | 48 passed, 26 failed; no baseline-passing test failed |
| BH-005 | 10 passed | 58 passed, 16 failed; no baseline-passing test failed |
| BH-006 | 6 passed | 64 passed, 10 failed; no baseline-passing test failed |
| BH-007 | 8 passed | 72 passed, 2 failed; no baseline-passing test failed |
| BH-008 | 2 passed | 74 passed, 0 failed |

The failures remaining after each step were reproductions of defects not
yet fixed at that point.

- **Linter:** not run. The project has no linter or static-analysis
  configuration, and none was installed.
- **Diff review:** `git status --short` shows two modified tracked files and
  two untracked paths (the new test file and `reports/`). Every hunk of
  `git diff` maps to a defect in the registry. Nothing had to be undone.
- **Command-line check:** the documented commands were run after the fixes
  and match the specification's table: `summary` (6, 5, 501.25, 100.25, 1),
  `duplicates` (one `TXN-1002` line), `show 2` (the `TXN-1003` refund),
  `show 99` (`No transaction at position 99.`), `discount 200 15`
  (`170.00`) and `--empty summary` (0, 0, 0.00, 0.00, 0).
- **Fix review:** done inline by the orchestrator, not by the
  `test-engineer` subagent. Verdict for all eight fixes: addresses root
  cause. No missing regression test was identified. Three points were
  recorded and are listed under Remaining Issues.

## Before-and-After Comparison

| Defect | Reproduction test | Before | After |
| ------ | ----------------- | ------ | ----- |
| BH-001 | `test_bh001_find_duplicates_keeps_duplicate_and_invalid_records_in_the_store` | `count()` was 1 after the call on a 4-record store | `count()` is 4 and `all_transactions()` is unchanged |
| BH-002 | `test_bh002_find_duplicates_spec_example_returns_third_and_fifth_records` | returned the first `A`, `B`, `C` | returns the third and fifth records |
| BH-003 | `tests/test_app.py::test_average_of_empty_store_is_zero` | `ZeroDivisionError` | `0.0` |
| BH-004 | `test_bh004_total_spec_example` | `180.0` | `120.0` |
| BH-005 | `tests/test_app.py::test_get_transaction_out_of_range_returns_none` | `IndexError` | `None` |
| BH-006 | `tests/test_app.py::test_apply_discount_rejects_percent_above_100` | no exception | `ValueError` |
| BH-007 | `test_bh007_validate_rejects_currency_that_is_not_three_uppercase_ascii_letters[usd]` | `[]` (record valid) | one problem (record invalid) |
| BH-008 | `test_bh008_validate_does_not_raise_for_an_int_too_large_for_a_float[positive]` | `OverflowError` | `[]` |

Command line, sample data, `python3 app.py summary`:

| Line | Before | After |
| ---- | ------ | ----- |
| Net total | 541.25 | 501.25 |
| Duplicate records | 4 | 1 |

Diff excerpt for `find_duplicates` (BH-001 and BH-002):

```diff
         seen = set()
-        unique = []
+        duplicates = []
         for tx in self.valid_transactions():
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

**Unresolved defect**

- **BH-009, Low, Unresolved (needs specification).** With a stored record
  whose amount is a non-zero int beyond the float range (for example
  `10**400`), `average_transaction_value()` raises `OverflowError` at
  `transaction_service.py:46` and `total_valid_transactions()` raises it at
  line 69. This was observed with a one-off snippet after the BH-008 fix; at
  baseline the same calls failed earlier, inside `validate_transaction`. The
  specification says the average never raises for a store of dictionaries,
  but gives no value to return when the mean cannot be a float, and says
  nothing about whether the total may raise. No test was added and no code
  was changed for it.

**Decisions for you**

1. BH-008 and BH-009 together: the BH-008 fix follows the letter of the
   data model, so a very large non-zero int is a valid amount. The other
   reading, reporting an amount that cannot be a float as a problem, also
   satisfies "never raises" and would remove BH-009. Say which you want.
2. `python3 app.py discount 200 150` now ends with an uncaught `ValueError`
   traceback, because `apply_discount` raises as specified. The
   specification's command table does not define the CLI output for an
   out-of-range percent.
3. `get_transaction(True)` returns the record at position 1, because `bool`
   is a subclass of `int`. The specification excludes `bool` for `amount`
   but says only "not an integer" for `index`.
4. `apply_discount` now raises `ValueError` for a NaN percent. The
   specification does not mention NaN.

**Confirmed defects left unfixed:** none. **Failed tests:** none.

**Observations not treated as defects**

- `format_transaction` in `app.py` would raise for a record with a
  non-numeric amount. The CLI only loads the built-in sample data, which
  has no such record.
- `TransactionService.__init__` accepts a `transactions` argument that the
  specification does not describe.
- `find_duplicates`, `all_transactions`, `valid_transactions` and
  `get_transaction` return the stored dictionaries themselves, so a caller
  that mutates one changes the store. The specification asks for a new list,
  not for copies.
- Before this run `app.py` had no tests, and several rules that hold were
  untested. Coverage tests were added in the new test file.

**Limitations of this run**

- `bug-scout` and `test-engineer` were not delegated to; there is no Agent
  or Task tool in this session. The same agent that wrote the fixes also
  reviewed them.
- No linter was available.
- Tests ran on Python 3.13.18 only.
- The registry's "Fix implemented" entries were written together with each
  defect's verification result, straight after the verification run, not as
  a separate step before it.

## Final Assessment

**Passed verification.** The final full-suite run (`cd demo-app && python3
-m pytest`) reports 74 passed, 0 failed and 0 errors, and none of the 10
tests that passed at baseline regressed.

Discovered 9, confirmed 8, fixed 8, verified 8. One defect (BH-009) is
unresolved and needs a specification decision. All changes are uncommitted.
