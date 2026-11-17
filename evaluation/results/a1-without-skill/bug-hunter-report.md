# Bug hunter report: Transaction Manager (`demo-app/`)

Date: 2026-11-16

## Result

Eight bugs were found and fixed in `demo-app/utils.py` and
`demo-app/transaction_service.py`. The test suite went from 8 failed / 10
passed to 88 passed / 0 failed, and every command in the `app.py` table of
`EXPECTED_BEHAVIOUR.md` now prints the expected output.

Three things were noticed and deliberately left alone; they are listed under
"Not changed" and the first one needs a decision from you.

`EXPECTED_BEHAVIOUR.md` was used as the specification throughout, as it says
it should be.

## Bugs fixed

Six of these were caught by the existing tests. Bugs 7 and 8 were not covered
by any test and were found by reading the code against the specification.

| # | Where | What was wrong | Effect before the fix | Fix |
| - | ----- | -------------- | --------------------- | --- |
| 1 | `TransactionService.average_transaction_value` | Divided by the number of valid records without checking for zero. | `ZeroDivisionError` on an empty store or a store with no valid records. `python3 app.py --empty summary` crashed. | Returns `0.0` when there are no valid records. |
| 2 | `TransactionService.find_duplicates` | Collected the first record for each id instead of the later repeats. | Returned the originals, not the duplicates. `app.py duplicates` listed 4 records instead of 1, and `summary` reported 4 duplicates. | Returns every valid record whose id was already seen in an earlier valid record, in insertion order. |
| 3 | `TransactionService.find_duplicates` | Assigned its result back to the store (`self._transactions = unique`). | Calling it silently deleted every duplicate and every invalid record from the store, so `count()`, `all_transactions()` and later totals changed. | The method no longer writes to the store. |
| 4 | `utils.apply_discount` | No range check on `percent`. | `apply_discount(200, 150)` returned `-100.0` and `apply_discount(200, -10)` returned `220.0` instead of raising. | Raises `ValueError` unless `0 <= percent <= 100`. The check also rejects NaN. `0` and `100` are still accepted. |
| 5 | `TransactionService.get_transaction` | Indexed the list directly. | `IndexError` for an index past the end (`app.py show 99` crashed), `TypeError` for a non-integer, and a negative index returned a record counted from the end (`show -1` printed the last record). | Returns `None` for a non-integer, a negative index, or an index `>= count()`. |
| 6 | `TransactionService.total_valid_transactions` | Summed `abs(amount)`. | Refunds were added instead of subtracted. The sample data totalled `541.25` instead of `501.25`. | Sums the signed amounts. |
| 7 | `utils.validate_transaction` (currency) | Only checked that the currency was a string of length 3. | `usd`, `US1`, `U$D`, `" US"` and `ÄBC` were all accepted as valid, so such records were counted in totals, averages and duplicates. | Requires exactly three characters in `A`-`Z`. |
| 8 | `utils.validate_transaction` (amount) and `average_transaction_value` | `math.isnan` raises `OverflowError` for an int too large to convert to a float, and the average summed ints before mixing in floats. | `validate_transaction` raised for an amount such as `10**400`, which also made `valid_transactions`, the totals and `find_duplicates` raise. The average raised for a store such as `10**308, 10**308, 1.5`. Both functions are specified as "never raises". | An int that cannot be represented as a float is reported as `amount must be finite`. The average converts each amount to a float before summing. |

## Decisions I made that you may want to review

- **Bug 8, very large ints.** The specification says an amount must be
  "finite" and that "amounts are floats". An int such as `10**400` is finite
  as a number but cannot be a float, so no float average or total exists for
  it. I treat it as invalid. The alternative (accept it) would leave the
  average unable to return a value.
- **Bug 5, `bool` as an index.** `get_transaction(True)` now returns `None`.
  Python treats `True` as the integer 1, and the specification only says "not
  an integer". I rejected it because the specification rejects `bool` for
  amounts and a boolean position is almost certainly a caller mistake. This is
  a one-line change if you want the other reading.
- **Bug 7, message wording.** The currency problem text changed from
  `currency must be a three-letter code` to
  `currency must be three uppercase letters`, because the old text was
  misleading for a value like `usd`. The specification does not fix this
  wording. Anything that matches on the old text would need updating; nothing
  in this repository does.

## Not changed

1. **`app.py discount` with an out-of-range percentage now ends in a
   traceback.** `python3 app.py discount 200 150` used to print the wrong
   answer `-100.00`. With bug 4 fixed it exits with status 1 and an uncaught
   `ValueError: percent must be between 0 and 100, got 150.0`. That is correct
   for the function, but the specification does not say how the command line
   should report it, so I did not invent a behaviour. A clean one-line error
   and a non-zero exit code would be a small change to `cmd_discount` and
   `main`. Tell me if you want it.
2. **Negative zero.** `apply_discount(-50, 100)` returns `-0.0`, which
   compares equal to `0.0` but prints as `-0.00` on the command line.
   `round_money` behaves the same way for tiny negative values. The
   specification says results use Python's `round(value, 2)` and puts decimal
   precision out of scope, so I left it.
3. **`app.format_transaction` assumes a numeric amount.** It raises
   `ValueError` for a stored record whose amount is not a number (for example
   `"12.50"`). This cannot happen with the built-in sample data, which is the
   only data the command line loads, so it is a latent problem rather than a
   live one.

Also note: the tests must be run from `demo-app/`, as the README says.
Running `pytest` from the repository root fails at import, because
`pytest.ini` lives in `demo-app/`. That is how the project is documented, not
a defect.

## Files changed

| File | Change |
| ---- | ------ |
| `demo-app/utils.py` | Bugs 4, 7, 8. Two small private helpers added (`_is_finite`, `_is_currency_code`). |
| `demo-app/transaction_service.py` | Bugs 1, 2, 3, 5, 6, 8. |
| `demo-app/tests/test_regressions.py` | New. 70 test cases for the fixes, the specification's examples and the `app.py` output table. |
| `reports/bug-hunter-report.md` | This report. |

`demo-app/tests/test_app.py`, `demo-app/app.py`, `EXPECTED_BEHAVIOUR.md` and
the README are unchanged. Nothing was committed; the changes are in the
working tree.

## Verification

All commands were run from `demo-app/` with Python 3.13.18.

| Check | Before | After |
| ----- | ------ | ----- |
| Original suite (`tests/test_app.py`, 18 tests) | 8 failed, 10 passed | 18 passed |
| Full suite (`python3 -m pytest`, 88 test cases) | n/a | 88 passed, 0 failed |
| New tests run against the original source | 39 of the 70 fail | all 70 pass |

The last row is a check on the tests themselves: with the two source files
temporarily put back to the baseline, the full suite gave 47 failed / 41
passed (the 8 original failures plus 39 new ones). The 31 new cases that pass
on the baseline guard behaviour that already worked.

Command-line output against the table in `EXPECTED_BEHAVIOUR.md`:

| Command | Before | After |
| ------- | ------ | ----- |
| `summary` | net total `541.25`, 4 duplicates | 6 records, 5 valid, net total `501.25`, average `100.25`, 1 duplicate |
| `duplicates` | 4 lines (the non-duplicates) | 1 line, the second `TXN-1002` record |
| `show 2` | the `TXN-1003` refund | unchanged |
| `show 99` | `IndexError` traceback | `No transaction at position 99.` |
| `show -1` | printed the last record | `No transaction at position -1.` |
| `discount 200 15` | `170.00` | unchanged |
| `--empty summary` | `ZeroDivisionError` traceback | 0 records, 0 valid, net total `0.00`, average `0.00`, 0 duplicates |

Not verified: Python 3.9, the minimum version the README names. Only Python
3.13 was available. The fixes use nothing newer than 3.9.
