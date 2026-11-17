"""Held-out acceptance tests used to score a Bug Hunter run.

These tests are never copied into an evaluation sandbox, so the agent being
evaluated cannot read them. Each test name starts with the planted defect it
checks (b1..b5 are the benchmark defects, s1 is the stretch defect that the
baseline test suite does not expose) or with "regression" for behaviour that
was correct before the run and must stay correct.

Point BUG_HUNTER_TARGET at the demo-app directory to score:

    BUG_HUNTER_TARGET=/path/to/sandbox/demo-app python3 -m pytest evaluation/hidden_tests
"""

import os
import subprocess
import sys

import pytest

TARGET = os.path.abspath(os.environ.get("BUG_HUNTER_TARGET", ""))
if not os.path.isfile(os.path.join(TARGET, "transaction_service.py")):
    raise RuntimeError("Set BUG_HUNTER_TARGET to a demo-app directory")
sys.path.insert(0, TARGET)

from transaction_service import TransactionService  # noqa: E402
from utils import apply_discount, is_valid_transaction, validate_transaction  # noqa: E402


def tx(transaction_id, amount, currency="USD"):
    return {"id": transaction_id, "amount": amount, "currency": currency}


def loaded(*records):
    service = TransactionService()
    service.load(list(records))
    return service


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "app.py", *args], cwd=TARGET, capture_output=True, text=True, timeout=30
    )


# --- B1: average of an empty collection -------------------------------------


def test_b1_average_of_empty_store():
    assert TransactionService().average_transaction_value() == 0.0


def test_b1_average_when_every_record_is_invalid():
    assert loaded(tx("", 10.0), tx("A", 0)).average_transaction_value() == 0.0


def test_b1_cli_empty_summary_does_not_crash():
    result = run_cli("--empty", "summary")
    assert result.returncode == 0, result.stderr
    assert "0.00" in result.stdout


# --- B2: duplicates identified, not removed ---------------------------------


def test_b2_returns_later_occurrences_in_order():
    service = loaded(tx("A", 1.0), tx("B", 2.0), tx("A", 3.0), tx("C", 4.0), tx("A", 5.0))
    assert service.find_duplicates() == [tx("A", 3.0), tx("A", 5.0)]


def test_b2_no_duplicates_is_empty_list():
    assert loaded(tx("A", 1.0), tx("B", 2.0)).find_duplicates() == []


def test_b2_store_is_not_modified():
    service = loaded(tx("A", 1.0), tx("", 9.0), tx("A", 3.0))
    before = service.all_transactions()
    service.find_duplicates()
    assert service.all_transactions() == before
    assert service.count() == 3


def test_b2_invalid_records_are_not_duplicates():
    assert loaded(tx("", 1.0), tx("", 2.0), tx("A", 3.0)).find_duplicates() == []


# --- B3: discount percentage validation --------------------------------------


@pytest.mark.parametrize("percent", [100.01, 150, 1000, -0.5, -10])
def test_b3_rejects_out_of_range_percent(percent):
    with pytest.raises(ValueError):
        apply_discount(200, percent)


@pytest.mark.parametrize("percent, expected", [(0, 80.0), (100, 0.0), (15, 68.0), (12.5, 70.0)])
def test_b3_boundaries_still_work(percent, expected):
    assert apply_discount(80, percent) == expected


# --- B4: retrieval by an invalid index ---------------------------------------


@pytest.mark.parametrize("index", [3, 99, -1, -3, -99])
def test_b4_invalid_integer_index_returns_none(index):
    assert loaded(tx("A", 1.0), tx("B", 2.0), tx("C", 3.0)).get_transaction(index) is None


@pytest.mark.parametrize("index", ["1", 1.0, None])
def test_b4_non_integer_index_returns_none(index):
    assert loaded(tx("A", 1.0), tx("B", 2.0)).get_transaction(index) is None


def test_b4_empty_store_returns_none():
    assert TransactionService().get_transaction(0) is None


def test_b4_cli_show_out_of_range():
    result = run_cli("show", "99")
    assert result.returncode == 0, result.stderr
    assert "No transaction at position 99" in result.stdout


# --- B5: refunds lower the total ---------------------------------------------


def test_b5_refund_lowers_total():
    assert loaded(tx("A", 100.0), tx("B", -30.0), tx("C", 50.0)).total_valid_transactions() == 120.0


def test_b5_only_refunds_gives_negative_total():
    assert loaded(tx("A", -10.0), tx("B", -2.5)).total_valid_transactions() == -12.5


def test_b5_cli_summary_net_total():
    result = run_cli("summary")
    assert result.returncode == 0, result.stderr
    assert "501.25" in result.stdout


# --- S1 (stretch): currency format -------------------------------------------


@pytest.mark.parametrize("currency", ["usd", "Usd", "U$D", "123", "U D"])
def test_s1_rejects_malformed_three_character_currency(currency):
    assert not is_valid_transaction(tx("A", 10.0, currency=currency))


def test_s1_accepts_uppercase_code():
    assert is_valid_transaction(tx("A", 10.0, currency="EUR"))


# --- Regression: behaviour that was already correct --------------------------


def test_regression_validation_messages():
    assert validate_transaction({"id": "A"}) == ["missing field: amount", "missing field: currency"]
    assert validate_transaction("nope") == ["transaction must be a dictionary"]
    assert validate_transaction(tx("A", 10.0)) == []


@pytest.mark.parametrize("amount", ["12.5", None, True, 0, float("nan"), float("inf")])
def test_regression_bad_amounts_are_invalid(amount):
    assert not is_valid_transaction(tx("A", amount))


def test_regression_add_transaction_validates_and_copies():
    service = TransactionService()
    record = tx("A", 10.0)
    service.add_transaction(record)
    record["amount"] = 999
    assert service.get_transaction(0)["amount"] == 10.0
    with pytest.raises(ValueError):
        service.add_transaction(tx("", 5.0))
    assert service.count() == 1


def test_regression_valid_index_and_average_and_total():
    service = loaded(tx("A", 100.0), tx("", 25.0), tx("B", 40.0))
    assert service.get_transaction(0) == tx("A", 100.0)
    assert service.get_transaction(2) == tx("B", 40.0)
    assert service.average_transaction_value() == 70.0
    assert service.total_valid_transactions() == 140.0
    assert service.count() == 3
    assert len(service.valid_transactions()) == 2


def test_regression_discount_and_cli():
    assert apply_discount(200, 15) == 170.0
    assert run_cli("discount", "200", "15").stdout.strip() == "170.00"
    assert "TXN-1003" in run_cli("show", "2").stdout
