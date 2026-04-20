import re

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Transaction


class RegistrationTests(APITestCase):
    URL = '/api/auth/register/'

    def test_register_success(self):
        response = self.client.post(self.URL, {
            'email': 'alice@example.com',
            'password': 'securepass123',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn('token', data)
        self.assertIn('account_number', data)
        self.assertIn('email', data)
        self.assertEqual(data['email'], 'alice@example.com')
        self.assertEqual(data['balance'], '10000.00')

    def test_register_duplicate_email(self):
        self.client.post(self.URL, {
            'email': 'alice@example.com',
            'password': 'securepass123',
        })
        response = self.client.post(self.URL, {
            'email': 'alice@example.com',
            'password': 'anotherpass456',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email_case_insensitive(self):
        self.client.post(self.URL, {
            'email': 'alice@example.com',
            'password': 'securepass123',
        })
        response = self.client.post(self.URL, {
            'email': 'Alice@Example.COM',
            'password': 'anotherpass456',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_email(self):
        response = self.client.post(self.URL, {
            'email': 'not-an-email',
            'password': 'securepass123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password(self):
        response = self.client.post(self.URL, {
            'email': 'bob@example.com',
            'password': 'short',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        response = self.client.post(self.URL, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_account_number_is_10_digits(self):
        response = self.client.post(self.URL, {
            'email': 'carol@example.com',
            'password': 'securepass123',
        })
        account_number = response.json()['account_number']
        self.assertTrue(re.match(r'^\d{10}$', account_number))
        self.assertNotEqual(account_number[0], '0')

    def test_register_creates_welcome_transaction(self):
        response = self.client.post(self.URL, {
            'email': 'dave@example.com',
            'password': 'securepass123',
        })
        account_number = response.json()['account_number']
        txns = Transaction.objects.filter(
            account__account_number=account_number
        )
        self.assertEqual(txns.count(), 1)
        txn = txns.first()
        self.assertEqual(txn.transaction_type, Transaction.TransactionType.CREDIT)
        self.assertEqual(txn.amount, 10000)
        self.assertEqual(txn.description, 'Welcome bonus')
