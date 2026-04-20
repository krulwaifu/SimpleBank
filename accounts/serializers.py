from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.models import BankAccount, Transaction

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return email



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class BalanceSerializer(serializers.Serializer):
    account_number = serializers.CharField(read_only=True)
    balance = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id',
            'amount',
            'transaction_type',
            'description',
            'reference',
            'balance_after',
            'created_at',
        ]
        read_only_fields = fields


class TransferSerializer(serializers.Serializer):
    to_account_number = serializers.CharField(max_length=10)
    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal('0.01')
    )

    def validate_to_account_number(self, value):
        if not BankAccount.objects.filter(account_number=value).exists():
            raise serializers.ValidationError(
                "Destination account not found."
            )
        return value


class TransferResponseSerializer(serializers.Serializer):
    transfer_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    fee = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_debited = serializers.DecimalField(max_digits=15, decimal_places=2)
    new_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    reference = serializers.UUIDField()


class RegisterResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    email = serializers.EmailField()
    account_number = serializers.CharField()
    balance = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    email = serializers.EmailField()


class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField()
