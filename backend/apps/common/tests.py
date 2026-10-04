from django.test import TestCase


class HealthCheckTests(TestCase):
    def test_health_check_reports_database_readiness(self):
        response = self.client.get('/api/health/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_health_check_only_accepts_get(self):
        response = self.client.post('/api/health/')

        self.assertEqual(response.status_code, 405)
