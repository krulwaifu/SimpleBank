from rest_framework import status
from rest_framework.test import APITestCase


class BalanceTests(APITestCase):
    REGISTER_URL = '/api/auth/register/'
    BALANCE_URL = '/api/account/balance/'

    def setUp(self):
        response = self.client.post(self.REGISTER_URL, {
            'email': 'user@example.com',
            'password': 'securepass123',
        })
        token = response.json()['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    def test_get_balance_after_registration(self):
        response = self.client.get(self.BALANCE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['balance'], '10000.00')

    def test_balance_returns_account_number(self):
        response = self.client.get(self.BALANCE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('account_number', response.json())
        self.assertEqual(len(response.json()['account_number']), 10)

    def test_balance_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(self.BALANCE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
