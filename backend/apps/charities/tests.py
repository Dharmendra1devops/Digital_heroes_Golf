from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.utils import timezone
from datetime import timedelta
from io import StringIO

from apps.charities.models import Charity, CharityEvent, CharitySelection


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

    def test_public_charity_detail_includes_upcoming_events_and_hides_inactive_causes(self):
        event = CharityEvent.objects.create(
            charity=self.charity,
            title='Community golf day',
            starts_at=timezone.now() + timedelta(days=14),
            location='City course',
        )
        response = self.client.get(f'/api/charities/{self.charity.slug}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], self.charity.name)
        self.assertEqual(response.json()['upcoming_events'][0]['id'], str(event.pk))

        self.charity.is_active = False
        self.charity.save(update_fields=('is_active', 'updated_at'))
        hidden = self.client.get(f'/api/charities/{self.charity.slug}/')
        self.assertEqual(hidden.status_code, 404)

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

    def test_admin_can_edit_public_charity_content(self):
        admin = get_user_model().objects.create_user(username='charity-edit-admin', is_staff=True)
        self.client.force_login(admin)

        response = self.client.patch(
            f'/api/charities/admin/{self.charity.pk}/',
            {
                'name': 'Updated Community Cause',
                'description': 'An updated cause profile.',
                'image_path': 'https://images.example.test/community.webp',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.charity.refresh_from_db()
        self.assertEqual(self.charity.name, 'Updated Community Cause')
        self.assertEqual(self.charity.description, 'An updated cause profile.')
        self.assertEqual(self.charity.image_path, 'https://images.example.test/community.webp')

    def test_admin_cannot_delete_a_charity_with_selection_history(self):
        CharitySelection.objects.create(user=self.user, charity=self.charity)
        admin = get_user_model().objects.create_user(username='charity-delete-admin', is_staff=True)
        self.client.force_login(admin)

        response = self.client.delete(f'/api/charities/admin/{self.charity.pk}/')

        self.assertEqual(response.status_code, 409)
        self.assertTrue(Charity.objects.filter(pk=self.charity.pk).exists())


class DemoCauseCommandTests(TestCase):
    def test_command_seeds_cause_categories_idempotently_and_removes_old_sample_events(self):
        charity = Charity.objects.create(
            slug='demo-community-learning-fund',
            name='DEMO ONLY: Community Learning Fund',
            description='Legacy sample cause label.',
        )
        CharityEvent.objects.create(
            charity=charity,
            title='DEMO ONLY: Community learning day',
            description='Fictional demo event only.',
            starts_at=timezone.now() + timedelta(days=30),
        )

        call_command('seed_demo_causes', stdout=StringIO())
        call_command('seed_demo_causes', stdout=StringIO())

        causes = Charity.objects.filter(slug__startswith='demo-')
        self.assertEqual(causes.count(), 2)
        self.assertSetEqual(set(causes.values_list('name', flat=True)), {'Community Learning', 'Green Spaces'})
        self.assertTrue(all('demo' not in cause.description.lower() for cause in causes))
        self.assertTrue(all(cause.is_active for cause in causes))
        self.assertEqual(CharityEvent.objects.filter(charity__in=causes).count(), 0)

    def test_command_refuses_to_overwrite_an_unrelated_existing_cause(self):
        charity = Charity.objects.create(
            slug='demo-community-learning-fund',
            name='Existing community organization',
        )

        with self.assertRaises(CommandError):
            call_command('seed_demo_causes', stdout=StringIO())

        charity.refresh_from_db()
        self.assertEqual(charity.name, 'Existing community organization')
        self.assertEqual(Charity.objects.count(), 1)
        self.assertEqual(CharityEvent.objects.count(), 0)
