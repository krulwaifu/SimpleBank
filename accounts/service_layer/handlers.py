import uuid

from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

from accounts.domain.constants import WELCOME_BONUS
from accounts.domain.exceptions import InsufficientFundsError, SelfTransferError
from accounts.domain.models import BankAccount, Transaction
from accounts.service_layer.commands import (
    GetBalance,
    ListTransactions,
    Login,
    RegisterUser,
    Transfer,
)
from accounts.service_layer.unit_of_work import AbstractUnitOfWork, DjangoUnitOfWork


def register_user(cmd: RegisterUser, uow: AbstractUnitOfWork | None = None) -> dict:
    if uow is None:
        uow = DjangoUnitOfWork()

    with uow:
        user = uow.users.create_user(email=cmd.email, password=cmd.password)

        account_number = BankAccount.generate_account_number()
        account = uow.accounts.create(
            user=user,
            account_number=account_number,
            balance=WELCOME_BONUS,
        )

        uow.transactions.create(
            account=account,
            amount=WELCOME_BONUS,
            transaction_type=Transaction.TransactionType.CREDIT,
            description='Welcome bonus',
            balance_after=WELCOME_BONUS,
        )

        token = Token.objects.create(user=user)

    return {
        'token': token.key,
        'email': user.email,
        'account_number': account.account_number,
        'balance': str(account.balance),
    }


def login(cmd: Login, request=None) -> dict | None:
    user = authenticate(request, username=cmd.email, password=cmd.password)
    if user is None:
        return None
    token, _ = Token.objects.get_or_create(user=user)
    return {'token': token.key, 'email': user.email}


def get_balance(cmd: GetBalance, uow: AbstractUnitOfWork | None = None) -> dict:
    if uow is None:
        uow = DjangoUnitOfWork()

    account = uow.accounts.get_by_user_id(cmd.user_id)
    return {
        'account_number': account.account_number,
        'balance': account.balance,
    }


def list_transactions(cmd: ListTransactions, uow: AbstractUnitOfWork | None = None):
    if uow is None:
        uow = DjangoUnitOfWork()

    account = uow.accounts.get_by_user_id(cmd.user_id)
    return uow.transactions.list_for_account(
        account=account,
        from_date=cmd.from_date,
        to_date=cmd.to_date,
    )


def execute_transfer(cmd: Transfer, uow: AbstractUnitOfWork | None = None) -> dict:
    if uow is None:
        uow = DjangoUnitOfWork()

    with uow:
        sender_account = uow.accounts.get_by_user_id(cmd.from_user_id)

        if sender_account.account_number == cmd.to_account_number:
            raise SelfTransferError("Cannot transfer to your own account.")

        fee = BankAccount.calculate_transfer_fee(cmd.amount)
        total_debit = cmd.amount + fee
        reference = uuid.uuid4()

        receiver_account = uow.accounts.get_by_account_number(
            cmd.to_account_number
        )
        locked = uow.accounts.get_for_update(
            [sender_account.pk, receiver_account.pk]
        )
        sender = locked[sender_account.pk]
        receiver = locked[receiver_account.pk]

        if sender.balance < total_debit:
            raise InsufficientFundsError(
                f"Insufficient funds. Required: {total_debit} "
                f"(amount: {cmd.amount} + fee: {fee}), "
                f"available: {sender.balance}."
            )

        sender.debit(total_debit)
        receiver.credit(cmd.amount)

        uow.accounts.save(sender)
        uow.accounts.save(receiver)

        uow.transactions.create(
            account=sender,
            amount=total_debit,
            transaction_type=Transaction.TransactionType.DEBIT,
            description=(
                f"Transfer to {cmd.to_account_number} "
                f"(amount: {cmd.amount}, fee: {fee})"
            ),
            reference=reference,
            balance_after=sender.balance,
        )

        uow.transactions.create(
            account=receiver,
            amount=cmd.amount,
            transaction_type=Transaction.TransactionType.CREDIT,
            description=f"Transfer from {sender.account_number}",
            reference=reference,
            balance_after=receiver.balance,
        )

    return {
        'transfer_amount': cmd.amount,
        'fee': fee,
        'total_debited': total_debit,
        'new_balance': sender.balance,
        'reference': reference,
    }
