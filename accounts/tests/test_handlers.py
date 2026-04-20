from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from accounts.domain.exceptions import InsufficientFundsError, SelfTransferError
from accounts.domain.models import BankAccount, Transaction
from accounts.adapters.repository import (
    AbstractBankAccountRepository,
    AbstractTransactionRepository,
    AbstractUserRepository,
)
from accounts.service_layer.commands import Transfer
from accounts.service_layer.handlers import execute_transfer
from accounts.service_layer.unit_of_work import AbstractUnitOfWork


class FakeUser:
    def __init__(self, pk, email):
        self.pk = pk
        self.email = email


class FakeBankAccountRepository(AbstractBankAccountRepository):
    def __init__(self):
        self._accounts = {}
        self._by_account_number = {}
        self._by_user_id = {}

    def add(self, account):
        self._accounts[account.pk] = account
        self._by_account_number[account.account_number] = account
        self._by_user_id[account.user_id] = account

    def get_by_account_number(self, account_number):
        return self._by_account_number[account_number]

    def get_by_user_id(self, user_id):
        return self._by_user_id[user_id]

    def get_for_update(self, pks):
        sorted_pks = sorted(pks)
        return {pk: self._accounts[pk] for pk in sorted_pks}

    def save(self, account):
        self._accounts[account.pk] = account

    def create(self, user, account_number, balance):
        account = BankAccount(
            pk=len(self._accounts) + 1,
            user=user,
            account_number=account_number,
            balance=balance,
        )
        self.add(account)
        return account

    def account_number_exists(self, account_number):
        return account_number in self._by_account_number


class FakeTransactionRepository(AbstractTransactionRepository):
    def __init__(self):
        self._transactions = []

    def create(self, **kwargs):
        self._transactions.append(kwargs)
        return Transaction(**kwargs)

    def list_for_account(self, account, from_date=None, to_date=None):
        return [t for t in self._transactions if t.get('account') == account]


class FakeUserRepository(AbstractUserRepository):
    def __init__(self):
        self._users = []

    def create_user(self, email, password):
        user = FakeUser(pk=len(self._users) + 1, email=email)
        self._users.append(user)
        return user

    def email_exists(self, email):
        return any(u.email == email for u in self._users)


class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.accounts = FakeBankAccountRepository()
        self.transactions = FakeTransactionRepository()
        self.users = FakeUserRepository()
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class ExecuteTransferHandlerTests(TestCase):
    def _make_uow_with_accounts(self, sender_balance='10000.00', receiver_balance='10000.00'):
        uow = FakeUnitOfWork()

        sender = BankAccount(pk=1, user_id=1, account_number='1111111111', balance=Decimal(sender_balance))
        receiver = BankAccount(pk=2, user_id=2, account_number='2222222222', balance=Decimal(receiver_balance))

        uow.accounts.add(sender)
        uow.accounts.add(receiver)

        return uow, sender, receiver

    def test_transfer_debits_sender_with_fee(self):
        uow, sender, receiver = self._make_uow_with_accounts()

        cmd = Transfer(from_user_id=1, to_account_number='2222222222', amount=Decimal('1000.00'))
        result = execute_transfer(cmd, uow=uow)

        self.assertEqual(result['fee'], Decimal('25.00'))
        self.assertEqual(result['total_debited'], Decimal('1025.00'))
        self.assertEqual(sender.balance, Decimal('8975.00'))

    def test_transfer_credits_receiver(self):
        uow, sender, receiver = self._make_uow_with_accounts()

        cmd = Transfer(from_user_id=1, to_account_number='2222222222', amount=Decimal('1000.00'))
        execute_transfer(cmd, uow=uow)

        self.assertEqual(receiver.balance, Decimal('11000.00'))

    def test_transfer_creates_two_transactions(self):
        uow, sender, receiver = self._make_uow_with_accounts()

        cmd = Transfer(from_user_id=1, to_account_number='2222222222', amount=Decimal('1000.00'))
        execute_transfer(cmd, uow=uow)

        self.assertEqual(len(uow.transactions._transactions), 2)
        debit_txn = uow.transactions._transactions[0]
        credit_txn = uow.transactions._transactions[1]
        self.assertEqual(debit_txn['transaction_type'], Transaction.TransactionType.DEBIT)
        self.assertEqual(credit_txn['transaction_type'], Transaction.TransactionType.CREDIT)
        self.assertEqual(debit_txn['reference'], credit_txn['reference'])

    def test_self_transfer_raises(self):
        uow, sender, receiver = self._make_uow_with_accounts()

        cmd = Transfer(from_user_id=1, to_account_number='1111111111', amount=Decimal('100.00'))
        with self.assertRaises(SelfTransferError):
            execute_transfer(cmd, uow=uow)

    def test_insufficient_funds_raises(self):
        uow, sender, receiver = self._make_uow_with_accounts(sender_balance='10.00')

        cmd = Transfer(from_user_id=1, to_account_number='2222222222', amount=Decimal('1000.00'))
        with self.assertRaises(InsufficientFundsError):
            execute_transfer(cmd, uow=uow)

    def test_minimum_fee_applied(self):
        uow, sender, receiver = self._make_uow_with_accounts()

        cmd = Transfer(from_user_id=1, to_account_number='2222222222', amount=Decimal('100.00'))
        result = execute_transfer(cmd, uow=uow)

        self.assertEqual(result['fee'], Decimal('5.00'))

    def test_transfer_returns_reference(self):
        uow, sender, receiver = self._make_uow_with_accounts()

        cmd = Transfer(from_user_id=1, to_account_number='2222222222', amount=Decimal('1000.00'))
        result = execute_transfer(cmd, uow=uow)

        self.assertIsNotNone(result['reference'])
