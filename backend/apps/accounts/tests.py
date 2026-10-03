from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.accounts.models import UserProfile


class AccountApiTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def csrf_headers(self):
        self.client.get('/api/auth/csrf/')
        return {'HTTP_X_CSRFTOKEN': self.client.cookies['csrftoken'].value}

    def test_registration_requires_csrf_and_starts_a_session(self):
        payload = {
            'email': 'member@example.com',
            'display_name': 'Avery Member',
            'password': 'TallPine!River58',
        }
        denied = self.client.post('/api/auth/register/', payload, content_type='application/json')
        self.assertEqual(denied.status_code, 403)

        response = self.client.post(
            '/api/auth/register/',
            payload,
            content_type='application/json',
            **self.csrf_headers(),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(UserProfile.objects.get().email, 'member@example.com')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)

    def test_login_uses_email_and_rejects_invalid_credentials(self):
        user = get_user_model().objects.create_user(
            username='account-login-test',
            email='login@example.com',
            password='TallPine!River58',
        )
        UserProfile.objects.create(user=user, email='login@example.com')
        headers = self.csrf_headers()

        invalid = self.client.post(
            '/api/auth/login/',
            {'email': 'login@example.com', 'password': 'wrong-password'},
            content_type='application/json',
            **headers,
        )
        self.assertEqual(invalid.status_code, 400)

        valid = self.client.post(
            '/api/auth/login/',
            {'email': 'LOGIN@example.com', 'password': 'TallPine!River58'},
            content_type='application/json',
            **headers,
        )
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()['user']['email'], 'login@example.com')

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        user = get_user_model().objects.create_user(username='existing-account')
        UserProfile.objects.create(user=user, email='duplicate@example.com')
        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'DUPLICATE@example.com',
                'password': 'TallPine!River58',
            },
            content_type='application/json',
            **self.csrf_headers(),
        )
        self.assertEqual(response.status_code, 400)
