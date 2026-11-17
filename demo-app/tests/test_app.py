"""Baseline tests for the transaction manager.

Expected results come from EXPECTED_BEHAVIOUR.md.
"""

import pytest

from transaction_service import TransactionService
from utils import apply_discount, is_valid_transaction, validate_transaction


def tx(transaction_id, amount, currency="USD", description=""):
    return {"id": transaction_id, "amount": amount, "currency": currency, "description": description}


@pytest.fixture
def service():
    svc = TransactionService()
    svc.load(
        [
            tx("A", 100.0),
            tx("B", 50.0),
            tx("A", 100.0),
            tx("C", -30.0),
        ]
    )
    return svc


# --- validation -----------------------------------------------------------


def test_validate_accepts_a_good_record():
    assert validate_transaction(tx("A", 10.0)) == []
    assert is_valid_transaction(tx("A", 10.0))


def test_validate_reports_missing_fields():
    assert validate_transaction({"id": "A"}) == ["missing field: amount", "missing field: currency"]


def test_validate_rejects_non_numeric_amount():
    assert not is_valid_transaction(tx("A", "12.50"))


def test_validate_rejects_zero_amount():
    assert not is_valid_transaction(tx("A", 0))


def test_validate_rejects_wrong_length_currency():
    assert not is_valid_transaction(tx("A", 10.0, currency="US"))


def test_add_transaction_rejects_invalid_record():
    svc = TransactionService()
    with pytest.raises(ValueError):
        svc.add_transaction(tx("", 10.0))
    assert svc.count() == 0


# --- average --------------------------------------------------------------


def test_average_of_valid_transactions(service):
    assert service.average_transaction_value() == 55.0


def test_average_of_empty_store_is_zero():
    assert TransactionService().average_transaction_value() == 0.0


# --- duplicates -----------------------------------------------------------


def test_find_duplicates_returns_the_repeated_record(service):
    assert service.find_duplicates() == [tx("A", 100.0)]


def test_find_duplicates_leaves_the_store_unchanged(service):
    before = service.all_transactions()
    service.find_duplicates()
    assert service.all_transactions() == before


# --- discounts ------------------------------------------------------------


def test_apply_discount():
    assert apply_discount(200, 15) == 170.0


def test_apply_discount_rejects_percent_above_100():
    with pytest.raises(ValueError):
        apply_discount(200, 150)


def test_apply_discount_rejects_negative_percent():
    with pytest.raises(ValueError):
        apply_discount(200, -10)


# --- retrieval by index ---------------------------------------------------


def test_get_transaction_by_valid_index(service):
    assert service.get_transaction(1) == tx("B", 50.0)


def test_get_transaction_out_of_range_returns_none(service):
    assert service.get_transaction(10) is None


def test_get_transaction_negative_index_returns_none(service):
    assert service.get_transaction(-1) is None


# --- totals ---------------------------------------------------------------


def test_total_ignores_invalid_records():
    svc = TransactionService()
    svc.load([tx("A", 100.0), tx("", 25.0), tx("B", 40.0)])
    assert svc.total_valid_transactions() == 140.0


def test_total_subtracts_refunds(service):
    assert service.total_valid_transactions() == 220.0
