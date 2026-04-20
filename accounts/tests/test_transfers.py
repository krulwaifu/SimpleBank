from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import BankAccount, Transaction


class TransferTests(APITestCase):
    REGISTER_URL = '/api/auth/register/'
    TRANSFER_URL = '/api/transfers/'
    BALANCE_URL = '/api/account/balance/'

    def setUp(self):
        resp_a = self.client.post(self.REGISTER_URL, {
            'email': 'alice@example.com',
            'password': 'securepass123',
        })
        data_a = resp_a.json()
        self.token_a = data_a['token']
        self.account_a = data_a['account_number']

        resp_b = self.client.post(self.REGISTER_URL, {
            'email': 'bob@example.com',
            'password': 'securepass456',
        })
        data_b = resp_b.json()
        self.token_b = data_b['token']
        self.account_b = data_b['account_number']

        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.token_a}'
        )

    def test_transfer_success(self):
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '1000.00',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['transfer_amount'], '1000.00')
        self.assertIn('fee', data)
        self.assertIn('total_debited', data)
        self.assertIn('new_balance', data)
        self.assertIn('reference', data)

    def test_transfer_fee_percentage(self):
        # 2.5% of 1000 = 25, which is > minimum 5
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '1000.00',
        })
        data = response.json()
        self.assertEqual(data['fee'], '25.00')
        self.assertEqual(data['total_debited'], '1025.00')

    def test_transfer_fee_minimum(self):
        # 2.5% of 100 = 2.50, which is < minimum 5
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '100.00',
        })
        data = response.json()
        self.assertEqual(data['fee'], '5.00')
        self.assertEqual(data['total_debited'], '105.00')

    def test_transfer_fee_boundary(self):
        # 2.5% of 200 = 5.00, exactly equal to minimum
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '200.00',
        })
        data = response.json()
        self.assertEqual(data['fee'], '5.00')

    def test_transfer_sender_balance_deducted(self):
        self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '1000.00',
        })
        response = self.client.get(self.BALANCE_URL)
        # 10000 - 1000 - 25 = 8975
        self.assertEqual(response.json()['balance'], '8975.00')

    def test_transfer_receiver_balance_increased(self):
        self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '1000.00',
        })
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.token_b}'
        )
        response = self.client.get(self.BALANCE_URL)
        # 10000 + 1000 = 11000
        self.assertEqual(response.json()['balance'], '11000.00')

    def test_transfer_creates_debit_transaction(self):
        self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '500.00',
        })
        txn = Transaction.objects.filter(
            account__account_number=self.account_a,
            transaction_type=Transaction.TransactionType.DEBIT,
        ).first()
        self.assertIsNotNone(txn)
        # Debit amount includes fee: 500 + max(12.50, 5) = 512.50
        self.assertEqual(txn.amount, Decimal('512.50'))

    def test_transfer_creates_credit_transaction(self):
        self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '500.00',
        })
        txn = Transaction.objects.filter(
            account__account_number=self.account_b,
            transaction_type=Transaction.TransactionType.CREDIT,
            description__startswith='Transfer from',
        ).first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.amount, Decimal('500.00'))

    def test_transfer_transactions_share_reference(self):
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '100.00',
        })
        reference = response.json()['reference']
        txns = Transaction.objects.filter(reference=reference)
        self.assertEqual(txns.count(), 2)
        types = set(txns.values_list('transaction_type', flat=True))
        self.assertEqual(types, {'CREDIT', 'DEBIT'})

    def test_transfer_insufficient_funds(self):
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '20000.00',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())

    def test_transfer_insufficient_funds_including_fee(self):
        # Balance is 10000. Transferring exactly 10000 should fail
        # because fee makes total > 10000
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '10000.00',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_self_transfer(self):
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_a,
            'amount': '100.00',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot transfer to your own account', response.json()['error'])

    def test_transfer_nonexistent_account(self):
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': '0000000000',
            'amount': '100.00',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_negative_amount(self):
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '-100.00',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_zero_amount(self):
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '0.00',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_very_small_amount(self):
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '0.01',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # 2.5% of 0.01 = 0.00025 rounds to 0.00, so minimum fee of 5.00 applies
        self.assertEqual(response.json()['fee'], '5.00')

    def test_transfer_large_amount(self):
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '9000.00',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        # fee = 9000 * 0.025 = 225
        self.assertEqual(data['fee'], '225.00')
        self.assertEqual(data['total_debited'], '9225.00')
        # 10000 - 9225 = 775
        self.assertEqual(data['new_balance'], '775.00')

    def test_transfer_decimal_precision(self):
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '123.45',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        # 123.45 * 0.025 = 3.08625 rounds to 3.09, which is < 5 minimum
        self.assertEqual(data['fee'], '5.00')

    def test_transfer_unauthenticated(self):
        self.client.credentials()
        response = self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '100.00',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_multiple_transfers_balance_consistency(self):
        # Transfer 100 three times from A to B
        for _ in range(3):
            self.client.post(self.TRANSFER_URL, {
                'to_account_number': self.account_b,
                'amount': '100.00',
            })

        # Each transfer: amount=100, fee=5 (2.5%=2.50 < min 5), total_debit=105
        # Sender: 10000 - (105 * 3) = 10000 - 315 = 9685
        response = self.client.get(self.BALANCE_URL)
        self.assertEqual(response.json()['balance'], '9685.00')

        # Receiver: 10000 + (100 * 3) = 10300
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.token_b}'
        )
        response = self.client.get(self.BALANCE_URL)
        self.assertEqual(response.json()['balance'], '10300.00')

        # Verify via DB directly
        sender = BankAccount.objects.get(account_number=self.account_a)
        receiver = BankAccount.objects.get(account_number=self.account_b)
        self.assertEqual(sender.balance, Decimal('9685.00'))
        self.assertEqual(receiver.balance, Decimal('10300.00'))
