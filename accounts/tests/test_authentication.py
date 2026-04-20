from rest_framework import status
from rest_framework.test import APITestCase


class AuthenticationTests(APITestCase):
    REGISTER_URL = '/api/auth/register/'
    LOGIN_URL = '/api/auth/login/'
    BALANCE_URL = '/api/account/balance/'

    def setUp(self):
        self.client.post(self.REGISTER_URL, {
            'email': 'user@example.com',
            'password': 'securepass123',
        })

    def test_login_success(self):
        response = self.client.post(self.LOGIN_URL, {
            'email': 'user@example.com',
            'password': 'securepass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.json())
        self.assertEqual(response.json()['email'], 'user@example.com')

    def test_login_wrong_password(self):
        response = self.client.post(self.LOGIN_URL, {
            'email': 'user@example.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        response = self.client.post(self.LOGIN_URL, {
            'email': 'noone@example.com',
            'password': 'securepass123',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields(self):
        response = self.client.post(self.LOGIN_URL, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_authenticated_endpoint_without_token(self):
        response = self.client.get(self.BALANCE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_endpoint_with_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token invalidtoken123')
        response = self.client.get(self.BALANCE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_endpoint_with_valid_token(self):
        login_resp = self.client.post(self.LOGIN_URL, {
            'email': 'user@example.com',
            'password': 'securepass123',
        })
        token = login_resp.json()['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        response = self.client.get(self.BALANCE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
