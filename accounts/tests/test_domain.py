from decimal import Decimal

from django.test import TestCase

from accounts.domain.exceptions import InsufficientFundsError
from accounts.domain.models import BankAccount


class BankAccountDebitTests(TestCase):
    def test_debit_reduces_balance(self):
        account = BankAccount(balance=Decimal('1000.00'))
        account.debit(Decimal('200.00'))
        self.assertEqual(account.balance, Decimal('800.00'))

    def test_debit_exact_balance(self):
        account = BankAccount(balance=Decimal('500.00'))
        account.debit(Decimal('500.00'))
        self.assertEqual(account.balance, Decimal('0.00'))

    def test_debit_insufficient_funds_raises(self):
        account = BankAccount(balance=Decimal('100.00'))
        with self.assertRaises(InsufficientFundsError):
            account.debit(Decimal('200.00'))

    def test_debit_insufficient_preserves_balance(self):
        account = BankAccount(balance=Decimal('100.00'))
        try:
            account.debit(Decimal('200.00'))
        except InsufficientFundsError:
            pass
        self.assertEqual(account.balance, Decimal('100.00'))


class BankAccountCreditTests(TestCase):
    def test_credit_increases_balance(self):
        account = BankAccount(balance=Decimal('1000.00'))
        account.credit(Decimal('500.00'))
        self.assertEqual(account.balance, Decimal('1500.00'))

    def test_credit_from_zero(self):
        account = BankAccount(balance=Decimal('0.00'))
        account.credit(Decimal('250.00'))
        self.assertEqual(account.balance, Decimal('250.00'))


class TransferFeeTests(TestCase):
    def test_fee_percentage_above_minimum(self):
        fee = BankAccount.calculate_transfer_fee(Decimal('1000.00'))
        self.assertEqual(fee, Decimal('25.00'))

    def test_fee_minimum_applied(self):
        fee = BankAccount.calculate_transfer_fee(Decimal('100.00'))
        self.assertEqual(fee, Decimal('5.00'))

    def test_fee_at_boundary(self):
        fee = BankAccount.calculate_transfer_fee(Decimal('200.00'))
        self.assertEqual(fee, Decimal('5.00'))

    def test_fee_small_amount(self):
        fee = BankAccount.calculate_transfer_fee(Decimal('0.01'))
        self.assertEqual(fee, Decimal('5.00'))

    def test_fee_large_amount(self):
        fee = BankAccount.calculate_transfer_fee(Decimal('10000.00'))
        self.assertEqual(fee, Decimal('250.00'))
