import random
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models

from accounts.domain.constants import TRANSFER_FEE_PERCENTAGE, MINIMUM_FEE
from accounts.domain.exceptions import InsufficientFundsError


class BankAccount(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bank_account',
    )
    account_number = models.CharField(
        max_length=10,
        unique=True,
        editable=False,
        db_index=True,
    )
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'accounts'
        ordering = ['-created_at']

    def __str__(self):
        return f"Account {self.account_number} ({self.user.email})"

    @classmethod
    def generate_account_number(cls):
        while True:
            number = str(random.randint(1, 9)) + ''.join(
                str(random.randint(0, 9)) for _ in range(9)
            )
            if not cls.objects.filter(account_number=number).exists():
                return number

    @staticmethod
    def calculate_transfer_fee(amount: Decimal) -> Decimal:
        percentage_fee = (amount * TRANSFER_FEE_PERCENTAGE).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return max(percentage_fee, MINIMUM_FEE)

    def debit(self, amount: Decimal) -> None:
        if self.balance < amount:
            raise InsufficientFundsError(
                f"Insufficient funds. Required: {amount}, available: {self.balance}."
            )
        self.balance -= amount

    def credit(self, amount: Decimal) -> None:
        self.balance += amount


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        CREDIT = 'CREDIT', 'Credit'
        DEBIT = 'DEBIT', 'Debit'

    account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_type = models.CharField(
        max_length=6,
        choices=TransactionType.choices,
    )
    description = models.CharField(max_length=255)
    reference = models.UUIDField(
        default=None,
        null=True,
        blank=True,
        db_index=True,
    )
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = 'accounts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} {self.amount} on {self.account.account_number}"
