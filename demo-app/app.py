"""Command-line entry point for the transaction manager.

Examples:
    python app.py summary
    python app.py duplicates
    python app.py show 2
    python app.py discount 200 15
    python app.py validate
    python app.py --empty summary
"""

import argparse
import sys

from transaction_service import TransactionService
from utils import apply_discount, validate_transaction

SAMPLE_TRANSACTIONS = [
    {"id": "TXN-1001", "amount": 120.00, "currency": "USD", "description": "Office chairs"},
    {"id": "TXN-1002", "amount": 45.50, "currency": "USD", "description": "Printer paper"},
    {"id": "TXN-1003", "amount": -20.00, "currency": "USD", "description": "Refund: damaged paper"},
    {"id": "TXN-1002", "amount": 45.50, "currency": "USD", "description": "Printer paper"},
    {"id": "TXN-1004", "amount": 310.25, "currency": "USD", "description": "Conference ticket"},
    {"id": "", "amount": 15.00, "currency": "USD", "description": "Unlabelled receipt"},
]


def build_service(empty=False):
    service = TransactionService()
    if not empty:
        service.load(SAMPLE_TRANSACTIONS)
    return service


def format_transaction(transaction):
    return "{id:<10} {amount:>10.2f} {currency}  {description}".format(
        id=transaction.get("id", "?"),
        amount=transaction.get("amount", 0.0),
        currency=transaction.get("currency", "???"),
        description=transaction.get("description", ""),
    )


def cmd_summary(service, _args):
    print(f"Records stored:      {service.count()}")
    print(f"Valid transactions:  {len(service.valid_transactions())}")
    print(f"Net total:           {service.total_valid_transactions():.2f}")
    print(f"Average value:       {service.average_transaction_value():.2f}")
    print(f"Duplicate records:   {len(service.find_duplicates())}")


def cmd_duplicates(service, _args):
    duplicates = service.find_duplicates()
    if not duplicates:
        print("No duplicate transactions.")
        return
    for transaction in duplicates:
        print(format_transaction(transaction))


def cmd_show(service, args):
    transaction = service.get_transaction(args.index)
    if transaction is None:
        print(f"No transaction at position {args.index}.")
        return
    print(format_transaction(transaction))


def cmd_discount(_service, args):
    print(f"{apply_discount(args.amount, args.percent):.2f}")


def cmd_validate(service, _args):
    for position, transaction in enumerate(service.all_transactions()):
        problems = validate_transaction(transaction)
        status = "ok" if not problems else "INVALID: " + "; ".join(problems)
        print(f"[{position}] {status}")


def build_parser():
    parser = argparse.ArgumentParser(description="Transaction manager")
    parser.add_argument("--empty", action="store_true", help="start with no transactions loaded")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("summary", help="totals for the stored transactions").set_defaults(func=cmd_summary)
    commands.add_parser("duplicates", help="list duplicate transactions").set_defaults(func=cmd_duplicates)
    commands.add_parser("validate", help="validate every stored record").set_defaults(func=cmd_validate)

    show = commands.add_parser("show", help="show the record at a position")
    show.add_argument("index", type=int)
    show.set_defaults(func=cmd_show)

    discount = commands.add_parser("discount", help="apply a percentage discount to an amount")
    discount.add_argument("amount", type=float)
    discount.add_argument("percent", type=float)
    discount.set_defaults(func=cmd_discount)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    service = build_service(empty=args.empty)
    args.func(service, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
