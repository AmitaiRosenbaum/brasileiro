from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient


class SessionAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            username='testuser',
            password='super-secret-password',
            email='test@example.com',
        )

    def test_csrf_endpoint_sets_token(self):
        response = self.client.get('/auth/csrf/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('csrfToken', response.data)
        self.assertIn('csrftoken', response.cookies)

    def test_login_sets_session_and_me_returns_current_user(self):
        csrf_response = self.client.get('/auth/csrf/')
        csrf_token = csrf_response.data['csrfToken']

        login_response = self.client.post(
            '/auth/login/',
            {'username': 'testuser', 'password': 'super-secret-password'},
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.data['user']['username'], 'testuser')
        self.assertIn('sessionid', login_response.cookies)

        me_response = self.client.get('/auth/me/')

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data['user']['email'], 'test@example.com')

    def test_logout_clears_authenticated_session(self):
        csrf_response = self.client.get('/auth/csrf/')
        csrf_token = csrf_response.data['csrfToken']

        login_response = self.client.post(
            '/auth/login/',
            {'username': 'testuser', 'password': 'super-secret-password'},
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        rotated_csrf_token = login_response.data['csrfToken']

        logout_response = self.client.post(
            '/auth/logout/',
            {},
            format='json',
            HTTP_X_CSRFTOKEN=rotated_csrf_token,
        )

        self.assertEqual(logout_response.status_code, 204)

        me_response = self.client.get('/auth/me/')

        self.assertEqual(me_response.status_code, 403)
