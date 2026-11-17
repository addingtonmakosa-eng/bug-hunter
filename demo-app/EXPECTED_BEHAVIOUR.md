# Transaction Manager: Expected Behaviour

This document is the specification for the transaction manager. Where the
code and this document disagree, this document is correct.

## Data model

A transaction is a dictionary:

| Field         | Required | Rule                                                             |
| ------------- | -------- | ---------------------------------------------------------------- |
| `id`          | yes      | Non-empty string (not only whitespace).                          |
| `amount`      | yes      | `int` or `float`, not `bool`. Finite and not zero.               |
| `currency`    | yes      | Exactly three uppercase ASCII letters, for example `USD`.        |
| `description` | no       | Free text.                                                       |

Purchases have a positive amount. Refunds have a negative amount.

Out of scope: currency conversion (all calculations assume one currency) and
decimal precision (amounts are floats, and results are rounded with Python's
built-in `round(value, 2)`).

## `utils.py`

### `round_money(value)`

Returns `value` as a float rounded to two decimal places.

### `validate_transaction(transaction)`

Returns a list of problem descriptions. An empty list means the record is valid.

- A value that is not a dictionary returns one problem.
- Each missing required field is reported as `missing field: <name>`. When
  fields are missing, no further checks are made.
- Otherwise every rule in the data model table is checked, and each rule that
  is broken adds one problem.
- Never raises.

### `is_valid_transaction(transaction)`

Returns `True` exactly when `validate_transaction` returns an empty list.

### `apply_discount(amount, percent)`

Returns `amount` reduced by `percent` per cent, rounded with `round_money`.

- `percent` must be between 0 and 100 inclusive. `0` returns the amount
  unchanged and `100` returns `0.0`.
- A `percent` below 0 or above 100 raises `ValueError`.
- `amount` is not validated by this function.

Examples: `apply_discount(200, 15)` is `170.0`. `apply_discount(80, 0)` is `80.0`.

## `transaction_service.py`: `TransactionService`

The service stores records in insertion order. `add_transaction` validates;
`load` does not, so the store can contain invalid records. Calculations use
the valid records only.

### `add_transaction(transaction)`

Stores a copy of a valid record. An invalid record raises `ValueError` and is
not stored.

### `load(records)`

Appends every record as given, without validation.

### `count()`

Number of stored records, valid and invalid.

### `all_transactions()`

A new list containing every stored record in insertion order.

### `valid_transactions()`

A new list of the stored records that pass validation, in insertion order.

### `average_transaction_value()`

The mean of the amounts of the valid transactions, rounded with `round_money`.
Refunds count as negative amounts.

- With no valid transactions (including an empty store) it returns `0.0`.
- Never raises for a store that holds only dictionaries.

### `find_duplicates()`

Two valid transactions are duplicates when they have the same `id`.

- Returns a list of the duplicate records: every valid record whose `id`
  already appeared in an earlier valid record. The first record with a given
  `id` is the original and is not returned.
- The result is in insertion order. With no duplicates it is an empty list.
- The stored records are not changed in any way. `count()` and
  `all_transactions()` return the same results before and after the call.

Example: ids `A, B, A, C, A` return the third and fifth records.

### `get_transaction(index)`

Returns the record at the zero-based position `index` among all stored
records.

- If `index` is not an integer, is negative, or is greater than or equal to
  `count()`, it returns `None`.
- Never raises.

### `total_valid_transactions()`

The net total of the valid transactions, rounded with `round_money`: the sum
of their signed amounts. A refund lowers the total. Invalid records are
ignored. An empty store returns `0.0`.

Example: amounts `100.0, -30.0, 50.0` total `120.0`.

## `app.py`

A command-line wrapper over the functions above. With the built-in sample
data:

| Command                 | Expected output                                           |
| ----------------------- | --------------------------------------------------------- |
| `summary`               | 6 records, 5 valid, net total `501.25`, average `100.25`, 1 duplicate |
| `duplicates`            | One line: the second `TXN-1002` record.                   |
| `show 2`                | The `TXN-1003` refund.                                    |
| `show 99`               | `No transaction at position 99.`                          |
| `discount 200 15`       | `170.00`                                                  |
| `--empty summary`       | 0 records, 0 valid, net total `0.00`, average `0.00`, 0 duplicates |
