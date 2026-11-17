# Bug Hunter Report: Transaction Manager (`demo-app/`)

Date: 2026-11-16

## Summary

I found and fixed 10 defects in `demo-app/`, measured against `EXPECTED_BEHAVIOUR.md`, which the
repository names as the authority where code and document disagree.

- Six are plain violations of the specification. They caused the 8 failing tests in the original suite.
- One more (currency validation) is a plain violation that no original test covered.
- Three are edge cases that the specification implies but does not spell out. Each involves a
  judgment call, listed under "Decisions for you to confirm".

The test suite went from 8 failed / 10 passed to 62 passed / 0 failed. Every command in the
specification's `app.py` table now prints the expected output. Nothing is committed.

## Bugs found and fixed

| # | Location | What was wrong | Fix |
| - | -------- | -------------- | --- |
| 1 | `transaction_service.py`, `average_transaction_value` | Divided by zero when there were no valid transactions. `python3 app.py --empty summary` crashed with `ZeroDivisionError`. | Returns `0.0` when there are no valid transactions. |
| 2 | `transaction_service.py`, `find_duplicates` | Returned the unique records, not the duplicates. The sample data reported 4 duplicates where the specification says 1. | Returns every valid record whose `id` already appeared in an earlier valid record, in insertion order. |
| 3 | `transaction_service.py`, `find_duplicates` | Overwrote the store with the unique valid records, so a call silently deleted the duplicates and every invalid record. `count()` changed after the call. | The method no longer assigns to the store. |
| 4 | `transaction_service.py`, `get_transaction` | Indexed the list directly. An out-of-range index raised `IndexError` (`show 99` crashed), a negative index returned a record counted from the end, and a non-integer index raised `TypeError`. | Returns `None` for a non-integer, negative or out-of-range index. |
| 5 | `transaction_service.py`, `total_valid_transactions` | Summed `abs(amount)`, so refunds raised the total. The sample data gave `541.25` where the specification says `501.25`. | Sums the signed amounts. |
| 6 | `utils.py`, `apply_discount` | Did not check `percent`. `apply_discount(200, 150)` returned `-100.0`, and a negative percentage raised the price. | Raises `ValueError` unless `0 <= percent <= 100`. A NaN percentage is rejected too. |
| 7 | `utils.py`, `validate_transaction` | The currency check only tested for a length of three. `usd`, `US1`, `12$`, three spaces and non-ASCII letters all passed. | The currency must match exactly three uppercase ASCII letters (`[A-Z]{3}`). |
| 8 | `utils.py`, `validate_transaction` | Raised `OverflowError` for an `int` amount too large to convert to a float (for example `10**400`), although the specification says it never raises. Because the service validates on every calculation, one such record in the store crashed `valid_transactions`, the average, the total and `find_duplicates`. | Such an amount is reported as `amount must be finite`. See decision 1. |
| 9 | `transaction_service.py`, `average_transaction_value` | Raised `OverflowError` for valid data mixing large ints with a float, for example amounts `10**308, 10**308, 1.5`: the int sum grew past the float range and could not then be added to the float. The specification says this method never raises. | Each amount is converted to a float before summing. |
| 10 | `utils.py`, `round_money` | Could return negative zero, which prints as `-0.00`. `python3 app.py discount -50 100` printed `-0.00`; the specification says a 100 per cent discount returns `0.0`. | Negative zero is normalised to `0.0`. Other values are unaffected. |

### Related change in `app.py`

Fix 6 makes `apply_discount` raise for an out-of-range percentage, which would have turned
`python3 app.py discount 200 150` into a Python traceback. `cmd_discount` now catches the
`ValueError`, prints `error: percent must be between 0 and 100, got 150.0` to standard error and
exits with status 2. `main` returns the command's status. The specification does not cover this
case, so say if you want different behaviour.

## Decisions for you to confirm

These go beyond the letter of the specification. Each is small and easy to reverse.

1. **Huge integer amounts are invalid (bug 8).** The specification allows any finite `int`, and
   `10**400` is finite as an integer. It also says amounts are floats and that the calculations
   never raise, and no float result exists for such a value. I resolved the conflict by treating an
   int that does not fit in a float as failing the "finite" rule. The alternative is to accept it
   and have the calculations return infinity.
2. **`get_transaction(True)` returns `None` (bug 4).** Python treats `bool` as a subclass of `int`,
   so `True` would otherwise act as index 1. I treated a boolean as "not an integer", matching how
   the data model excludes `bool` from amounts.
3. **Validation message wording.** The currency message changed from `currency must be a
   three-letter code` to `currency must be three uppercase ASCII letters`. The specification fixes
   only the `missing field: <name>` wording, but anything matching the old text would need updating.

## Verification

All commands were run from `demo-app/` with Python 3.13.18 and pytest.

- **Before the fixes:** `python3 -m pytest` gave 8 failed, 10 passed.
- **After the fixes:** `python3 -m pytest` gives 62 passed, 0 failed (the 18 original tests plus 44
  new cases).
- **The new tests detect the bugs:** run against the original source files, the extended suite
  gives 39 failed, 23 passed.
- **Command line, checked against the specification table:**

| Command | Before | After |
| ------- | ------ | ----- |
| `summary` | net total `541.25`, 4 duplicates | 6 records, 5 valid, net total `501.25`, average `100.25`, 1 duplicate |
| `duplicates` | four lines (the unique records) | one line, the second `TXN-1002` |
| `show 2` | the `TXN-1003` refund | unchanged |
| `show 99` | `IndexError` traceback | `No transaction at position 99.` |
| `discount 200 15` | `170.00` | unchanged |
| `--empty summary` | `ZeroDivisionError` traceback | 0 records, 0 valid, `0.00`, `0.00`, 0 duplicates |
| `discount 200 150` | `-100.00` | error message, exit status 2 |

Not verified: the README states Python 3.9 or later. Only 3.13 had pytest installed, so the tests
ran on 3.13 alone. The three source files compile on 3.11 and 3.12, and the changes use no syntax
or library feature newer than 3.9, but I did not run them on 3.9.

## Files changed

- `demo-app/utils.py`: bugs 6, 7, 8, 10.
- `demo-app/transaction_service.py`: bugs 1, 2, 3, 4, 5, 9.
- `demo-app/app.py`: error handling for the `discount` command.
- `demo-app/tests/test_app.py`: 21 new test functions (44 cases) appended; the original tests are
  untouched. They cover the currency rule, unusable amounts, the "never raises" guarantees,
  duplicate ordering, index handling, discount boundaries and every command in the specification
  table.
- `reports/bug-hunter-report.md`: this report.

## Noticed but not changed

- **Float overflow gives infinity.** With valid amounts near the float limit (around `1e308`), the
  total and the average can come out as `inf`, for example the average of `1e308` and `1e308`.
  Neither method raises. The specification places decimal precision out of scope, so I left it.
- **`description` is not validated.** The data model lists it as optional "free text". I read that
  as no rule to enforce, so a non-string description is still accepted.
- **`format_transaction` in `app.py` assumes a numeric amount.** It would raise on a record whose
  amount is not a number. The built-in sample data has no such record, so no command can reach it
  today; it would matter if the app ever loaded outside data.
- **`load` stores the caller's dictionaries, not copies.** This matches the specification
  ("appends every record as given"), but a caller that later edits a record changes the store.
