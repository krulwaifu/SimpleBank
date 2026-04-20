from django.contrib import admin

from accounts.models import BankAccount, Transaction


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'user', 'balance', 'created_at')
    search_fields = ('account_number', 'user__email')
    readonly_fields = ('account_number', 'created_at', 'updated_at')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'account', 'transaction_type', 'amount', 'balance_after', 'created_at'
    )
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('account__account_number', 'description')
    readonly_fields = ('created_at',)
