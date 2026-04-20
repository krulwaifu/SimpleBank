import abc
from decimal import Decimal

from django.contrib.auth import get_user_model

from accounts.domain.models import BankAccount, Transaction

User = get_user_model()


class AbstractBankAccountRepository(abc.ABC):
    @abc.abstractmethod
    def get_by_account_number(self, account_number: str) -> BankAccount:
        ...

    @abc.abstractmethod
    def get_by_user_id(self, user_id: int) -> BankAccount:
        ...

    @abc.abstractmethod
    def get_for_update(self, pks: list[int]) -> dict[int, BankAccount]:
        ...

    @abc.abstractmethod
    def save(self, account: BankAccount) -> None:
        ...

    @abc.abstractmethod
    def create(self, user, account_number: str, balance: Decimal) -> BankAccount:
        ...

    @abc.abstractmethod
    def account_number_exists(self, account_number: str) -> bool:
        ...


class AbstractTransactionRepository(abc.ABC):
    @abc.abstractmethod
    def create(self, **kwargs) -> Transaction:
        ...

    @abc.abstractmethod
    def list_for_account(self, account: BankAccount, from_date=None, to_date=None):
        ...


class AbstractUserRepository(abc.ABC):
    @abc.abstractmethod
    def create_user(self, email: str, password: str):
        ...

    @abc.abstractmethod
    def email_exists(self, email: str) -> bool:
        ...


class DjangoBankAccountRepository(AbstractBankAccountRepository):
    def get_by_account_number(self, account_number: str) -> BankAccount:
        return BankAccount.objects.get(account_number=account_number)

    def get_by_user_id(self, user_id: int) -> BankAccount:
        return BankAccount.objects.get(user_id=user_id)

    def get_for_update(self, pks: list[int]) -> dict[int, BankAccount]:
        sorted_pks = sorted(pks)
        return {
            acct.pk: acct
            for acct in BankAccount.objects.select_for_update().filter(
                pk__in=sorted_pks
            )
        }

    def save(self, account: BankAccount) -> None:
        account.save(update_fields=['balance', 'updated_at'])

    def create(self, user, account_number: str, balance: Decimal) -> BankAccount:
        return BankAccount.objects.create(
            user=user,
            account_number=account_number,
            balance=balance,
        )

    def account_number_exists(self, account_number: str) -> bool:
        return BankAccount.objects.filter(account_number=account_number).exists()


class DjangoTransactionRepository(AbstractTransactionRepository):
    def create(self, **kwargs) -> Transaction:
        return Transaction.objects.create(**kwargs)

    def list_for_account(self, account: BankAccount, from_date=None, to_date=None):
        qs = Transaction.objects.filter(account=account)
        if from_date:
            qs = qs.filter(created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__date__lte=to_date)
        return qs


class DjangoUserRepository(AbstractUserRepository):
    def create_user(self, email: str, password: str):
        return User.objects.create_user(
            username=email,
            email=email,
            password=password,
        )

    def email_exists(self, email: str) -> bool:
        return User.objects.filter(email=email).exists()
