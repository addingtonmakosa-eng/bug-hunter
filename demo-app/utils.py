"""Helper functions shared by the transaction manager."""

import math

REQUIRED_FIELDS = ("id", "amount", "currency")


def round_money(value):
    """Round a monetary value to two decimal places."""
    return round(float(value), 2)


def validate_transaction(transaction):
    """Check a transaction record.

    Returns a list of human-readable problems. An empty list means the
    record is valid.
    """
    if not isinstance(transaction, dict):
        return ["transaction must be a dictionary"]

    problems = [f"missing field: {field}" for field in REQUIRED_FIELDS if field not in transaction]
    if problems:
        return problems

    transaction_id = transaction["id"]
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        problems.append("id must be a non-empty string")

    amount = transaction["amount"]
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        problems.append("amount must be a number")
    elif math.isnan(amount) or math.isinf(amount):
        problems.append("amount must be finite")
    elif amount == 0:
        problems.append("amount must not be zero")

    currency = transaction["currency"]
    if not isinstance(currency, str) or len(currency) != 3:
        problems.append("currency must be a three-letter code")

    return problems


def is_valid_transaction(transaction):
    """Return True when the record passes validation."""
    return not validate_transaction(transaction)


def apply_discount(amount, percent):
    """Return the amount after taking a percentage discount off it."""
    discounted = amount * (1 - percent / 100)
    return round_money(discounted)
