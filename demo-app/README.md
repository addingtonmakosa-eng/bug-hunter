# Transaction Manager

A small command-line application that keeps a collection of financial
transactions in memory and reports on them.

## What it does

- Validates transaction records.
- Calculates the average transaction value and the net total.
- Identifies duplicate transactions.
- Applies percentage discounts.
- Retrieves a transaction by position.

## Layout

| File                     | Purpose                                             |
| ------------------------ | --------------------------------------------------- |
| `app.py`                 | Command-line entry point with built-in sample data. |
| `transaction_service.py` | `TransactionService`: the store and its calculations. |
| `utils.py`               | Validation, rounding and discount helpers.          |
| `EXPECTED_BEHAVIOUR.md`  | The specification for every function.               |
| `tests/test_app.py`      | Test suite (pytest).                                |

## Setup

Python 3.9 or later. The only dependency is pytest, for the tests:

```bash
python3 -m pip install -r requirements.txt
```

## Usage

Run from this directory:

```bash
python3 app.py summary
python3 app.py duplicates
python3 app.py show 2
python3 app.py discount 200 15
python3 app.py validate
python3 app.py --empty summary
```

## Tests

```bash
python3 -m pytest
```
