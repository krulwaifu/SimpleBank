from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Transaction


class TransactionTests(APITestCase):
    REGISTER_URL = '/api/auth/register/'
    TRANSACTIONS_URL = '/api/account/transactions/'
    TRANSFER_URL = '/api/transfers/'

    def setUp(self):
        # Register user A
        resp_a = self.client.post(self.REGISTER_URL, {
            'email': 'alice@example.com',
            'password': 'securepass123',
        })
        data_a = resp_a.json()
        self.token_a = data_a['token']
        self.account_a = data_a['account_number']

        # Register user B
        resp_b = self.client.post(self.REGISTER_URL, {
            'email': 'bob@example.com',
            'password': 'securepass456',
        })
        data_b = resp_b.json()
        self.token_b = data_b['token']
        self.account_b = data_b['account_number']

    def _auth_as(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    def test_list_transactions_after_registration(self):
        self._auth_as(self.token_a)
        response = self.client.get(self.TRANSACTIONS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['transaction_type'], 'CREDIT')
        self.assertEqual(results[0]['amount'], '10000.00')
        self.assertEqual(results[0]['description'], 'Welcome bonus')

    def test_transactions_after_transfer(self):
        self._auth_as(self.token_a)
        self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '100.00',
        })
        response = self.client.get(self.TRANSACTIONS_URL)
        results = response.json()['results']
        self.assertEqual(len(results), 2)

    def test_transactions_ordered_by_newest_first(self):
        self._auth_as(self.token_a)
        self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '100.00',
        })
        response = self.client.get(self.TRANSACTIONS_URL)
        results = response.json()['results']
        self.assertEqual(results[0]['transaction_type'], 'DEBIT')
        self.assertEqual(results[1]['transaction_type'], 'CREDIT')

    def test_transactions_date_filter_from(self):
        self._auth_as(self.token_a)
        today = timezone.now().date().isoformat()
        response = self.client.get(
            self.TRANSACTIONS_URL, {'from': today}
        )
        results = response.json()['results']
        self.assertEqual(len(results), 1)

    def test_transactions_date_filter_to(self):
        self._auth_as(self.token_a)
        today = timezone.now().date().isoformat()
        response = self.client.get(
            self.TRANSACTIONS_URL, {'to': today}
        )
        results = response.json()['results']
        self.assertEqual(len(results), 1)

    def test_transactions_date_filter_range(self):
        self._auth_as(self.token_a)
        today = timezone.now().date()
        yesterday = (today - timedelta(days=1)).isoformat()
        tomorrow = (today + timedelta(days=1)).isoformat()
        response = self.client.get(
            self.TRANSACTIONS_URL,
            {'from': yesterday, 'to': tomorrow},
        )
        results = response.json()['results']
        self.assertEqual(len(results), 1)

    def test_transactions_date_filter_excludes_out_of_range(self):
        self._auth_as(self.token_a)
        yesterday = (timezone.now().date() - timedelta(days=1)).isoformat()
        response = self.client.get(
            self.TRANSACTIONS_URL, {'to': yesterday}
        )
        results = response.json()['results']
        self.assertEqual(len(results), 0)

    def test_transactions_pagination(self):
        self._auth_as(self.token_a)
        # Create 21 transfers (welcome bonus + 21 debit = 22 total)
        for i in range(21):
            self.client.post(self.TRANSFER_URL, {
                'to_account_number': self.account_b,
                'amount': '1.00',
            })
        response = self.client.get(self.TRANSACTIONS_URL)
        data = response.json()
        self.assertEqual(len(data['results']), 20)
        self.assertIsNotNone(data['next'])

    def test_transactions_unauthenticated(self):
        response = self.client.get(self.TRANSACTIONS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_transactions_isolation(self):
        # Alice's transactions should not include Bob's
        self._auth_as(self.token_a)
        self.client.post(self.TRANSFER_URL, {
            'to_account_number': self.account_b,
            'amount': '100.00',
        })

        # Bob should see only his own transactions (welcome + credit)
        self._auth_as(self.token_b)
        response = self.client.get(self.TRANSACTIONS_URL)
        results = response.json()['results']
        self.assertEqual(len(results), 2)
        for txn in results:
            self.assertEqual(txn['transaction_type'], 'CREDIT')
