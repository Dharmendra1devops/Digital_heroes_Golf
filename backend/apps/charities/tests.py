from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase

from apps.charities.models import Charity, CharitySelection


class CharitySelectionConstraintTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='charity-member', password='test-password')
        self.charity = Charity.objects.create(slug='first-charity', name='First Charity')

    def test_contribution_cannot_be_below_ten_percent(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CharitySelection.objects.create(
                    user=self.user,
                    charity=self.charity,
                    contribution_bps=999,
                )

    def test_user_can_only_have_one_current_charity_selection(self):
        CharitySelection.objects.create(user=self.user, charity=self.charity)
        second_charity = Charity.objects.create(slug='second-charity', name='Second Charity')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CharitySelection.objects.create(user=self.user, charity=second_charity)


class CharityApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='charity-api-member')
        self.charity = Charity.objects.create(
            slug='community-golf-fund',
            name='Community Golf Fund',
            description='Golf access for young people.',
            is_featured=True,
        )
        self.client = Client()

    def test_public_directory_filters_inactive_charities_and_supports_search(self):
        Charity.objects.create(slug='closed-fund', name='Closed Fund', is_active=False)
        response = self.client.get('/api/charities/?q=community&featured=true')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['slug'] for item in response.json()], ['community-golf-fund'])

    def test_member_can_change_charity_and_selection_history_is_kept(self):
        self.client.force_login(self.user)
        first = self.client.put(
            '/api/charities/selection/',
            {'charity_id': str(self.charity.pk), 'contribution_bps': 1500},
            content_type='application/json',
        )
        self.assertEqual(first.status_code, 200)

        next_charity = Charity.objects.create(slug='local-youth-sports', name='Local Youth Sports')
        second = self.client.put(
            '/api/charities/selection/',
            {'charity_id': str(next_charity.pk), 'contribution_bps': 2500},
            content_type='application/json',
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(CharitySelection.objects.filter(user=self.user).count(), 2)
        self.assertEqual(CharitySelection.objects.filter(user=self.user, effective_to__isnull=True).count(), 1)
        self.assertIsNotNone(
            CharitySelection.objects.get(user=self.user, charity=self.charity).effective_to,
        )

    def test_member_cannot_select_an_inactive_charity(self):
        inactive = Charity.objects.create(slug='inactive-fund', name='Inactive Fund', is_active=False)
        self.client.force_login(self.user)
        response = self.client.put(
            '/api/charities/selection/',
            {'charity_id': str(inactive.pk), 'contribution_bps': 1000},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_charity_mutation_requires_admin_access(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/charities/admin/',
            {'slug': 'new-cause', 'name': 'New Cause'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_a_charity_with_operational_flags(self):
        admin = get_user_model().objects.create_user(username='charity-admin', is_staff=True)
        self.client.force_login(admin)
        response = self.client.post(
            '/api/charities/admin/',
            {
                'slug': 'new-cause',
                'name': 'New Cause',
                'is_active': True,
                'is_featured': True,
                'display_order': 2,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['is_featured'])
        self.assertEqual(response.json()['display_order'], 2)

    def test_admin_cannot_delete_a_charity_with_selection_history(self):
        CharitySelection.objects.create(user=self.user, charity=self.charity)
        admin = get_user_model().objects.create_user(username='charity-delete-admin', is_staff=True)
        self.client.force_login(admin)

        response = self.client.delete(f'/api/charities/admin/{self.charity.pk}/')

        self.assertEqual(response.status_code, 409)
        self.assertTrue(Charity.objects.filter(pk=self.charity.pk).exists())
