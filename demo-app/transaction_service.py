"""In-memory transaction store and the calculations run against it."""

from utils import round_money, validate_transaction


class TransactionService:
    """Holds a collection of transaction records.

    Records added one at a time are validated. Records brought in through
    ``load`` are kept exactly as they were imported, so the store may contain
    invalid records.
    """

    def __init__(self, transactions=None):
        self._transactions = list(transactions) if transactions else []

    def add_transaction(self, transaction):
        """Validate a single record and store it."""
        problems = validate_transaction(transaction)
        if problems:
            raise ValueError("invalid transaction: " + "; ".join(problems))
        self._transactions.append(dict(transaction))

    def load(self, records):
        """Bulk-import records without validating them."""
        self._transactions.extend(records)

    def count(self):
        """Number of stored records, valid or not."""
        return len(self._transactions)

    def all_transactions(self):
        """A copy of every stored record, in insertion order."""
        return list(self._transactions)

    def valid_transactions(self):
        """The stored records that pass validation, in insertion order."""
        return [tx for tx in self._transactions if not validate_transaction(tx)]

    def average_transaction_value(self):
        """Average amount of the valid transactions."""
        valid = self.valid_transactions()
        total = sum(tx["amount"] for tx in valid)
        return round_money(total / len(valid))

    def find_duplicates(self):
        """Find transactions that repeat the id of an earlier transaction."""
        seen = set()
        unique = []
        for tx in self.valid_transactions():
            if tx["id"] not in seen:
                seen.add(tx["id"])
                unique.append(tx)
        self._transactions = unique
        return unique

    def get_transaction(self, index):
        """Return the record stored at the given position."""
        return self._transactions[index]

    def total_valid_transactions(self):
        """Net total of the valid transactions."""
        total = 0.0
        for tx in self.valid_transactions():
            total += abs(tx["amount"])
        return round_money(total)
