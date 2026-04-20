import abc

from django.db import transaction as db_transaction

from accounts.adapters.repository import (
    AbstractBankAccountRepository,
    AbstractTransactionRepository,
    AbstractUserRepository,
    DjangoBankAccountRepository,
    DjangoTransactionRepository,
    DjangoUserRepository,
)


class AbstractUnitOfWork(abc.ABC):
    accounts: AbstractBankAccountRepository
    transactions: AbstractTransactionRepository
    users: AbstractUserRepository

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    @abc.abstractmethod
    def commit(self):
        ...

    @abc.abstractmethod
    def rollback(self):
        ...


class DjangoUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.accounts = DjangoBankAccountRepository()
        self.transactions = DjangoTransactionRepository()
        self.users = DjangoUserRepository()

    def __enter__(self):
        self._atomic = db_transaction.atomic()
        self._atomic.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._atomic.__exit__(exc_type, exc_val, exc_tb)

    def commit(self):
        pass

    def rollback(self):
        db_transaction.set_rollback(True)
