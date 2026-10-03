import os
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from apps.draws.models import Draw, DrawConfiguration, DrawEntry
from apps.subscriptions.models import Subscription, SubscriptionPlan
from apps.winners.models import DrawWinner, Payout, WinnerProof


class WinnerApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='winner-member')
        self.other_user = user_model.objects.create_user(username='other-member')
        self.admin = user_model.objects.create_user(username='winner-admin', is_staff=True)
        plan = SubscriptionPlan.objects.create(
            interval=SubscriptionPlan.Interval.MONTHLY,
            amount_minor=1200,
            currency='USD',
        )
        now = timezone.now()
        subscription = Subscription.objects.create(
            user=self.user,
            plan=plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=now - timedelta(days=1),
            current_period_end=now + timedelta(days=30),
        )
        configuration = DrawConfiguration.objects.create(version=1, mode=DrawConfiguration.Mode.RANDOM)
        draw = Draw.objects.create(
            configuration=configuration,
            scheduled_at=now + timedelta(days=1),
            eligibility_cutoff=now,
        )
        entry = DrawEntry.objects.create(
            draw=draw,
            user=self.user,
            subscription=subscription,
            eligible_at=now,
        )
        self.winner = DrawWinner.objects.create(
            entry=entry,
            match_count=3,
            prize_amount_minor=5000,
            currency='USD',
        )
        self.proof = WinnerProof.objects.create(
            winner=self.winner,
            object_path=f'{self.winner.pk}/proof.png',
        )
        self.payout = Payout.objects.create(
            winner=self.winner,
            attempt_number=1,
            amount_minor=5000,
            currency='USD',
        )
        self.client = Client()

    def test_member_can_only_access_their_own_wins_and_proofs(self):
        self.client.force_login(self.other_user)
        own_wins = self.client.get('/api/winners/me/')
        foreign_proof = self.client.get(f'/api/winners/{self.winner.pk}/proofs/')

        self.assertEqual(own_wins.status_code, 200)
        self.assertEqual(own_wins.json(), [])
        self.assertEqual(foreign_proof.status_code, 404)

    def test_proof_upload_fails_closed_until_storage_is_configured(self):
        self.client.force_login(self.user)
        image = SimpleUploadedFile(
            'proof.png',
            b'\x89PNG\r\n\x1a\n' + b'proof-content',
            content_type='image/png',
        )
        with patch.dict(os.environ, {'SUPABASE_URL': '', 'SUPABASE_SERVICE_ROLE_KEY': ''}):
            response = self.client.post(
                f'/api/winners/{self.winner.pk}/proofs/',
                {'proof': image},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'storage_not_configured')
        self.assertEqual(WinnerProof.objects.filter(winner=self.winner).count(), 1)

    def test_admin_proof_preview_fails_closed_until_storage_is_configured(self):
        self.client.force_login(self.admin)
        with patch.dict(os.environ, {'SUPABASE_URL': '', 'SUPABASE_SERVICE_ROLE_KEY': ''}):
            response = self.client.get(f'/api/winners/admin/proofs/{self.proof.pk}/signed-url/')

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'storage_not_configured')

    def test_member_cannot_request_admin_proof_preview(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/api/winners/admin/proofs/{self.proof.pk}/signed-url/')

        self.assertEqual(response.status_code, 403)

    def test_admin_approval_updates_winner_review_state(self):
        self.client.force_login(self.admin)
        response = self.client.patch(
            f'/api/winners/admin/proofs/{self.proof.pk}/review/',
            {'review_status': 'approved', 'review_reason': 'Score proof confirmed.'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.winner.refresh_from_db()
        self.assertEqual(self.winner.verification_status, DrawWinner.VerificationStatus.APPROVED)
        self.assertEqual(self.winner.review_reason, 'Score proof confirmed.')

    def test_payout_requires_approved_winner_and_provider_reference(self):
        self.client.force_login(self.admin)
        url = f'/api/winners/admin/payouts/{self.payout.pk}/'
        denied = self.client.patch(
            url,
            {'status': 'paid', 'provider_payout_id': 'po_test_123'},
            content_type='application/json',
        )
        self.assertEqual(denied.status_code, 409)

        self.winner.verification_status = DrawWinner.VerificationStatus.APPROVED
        self.winner.save(update_fields=('verification_status', 'updated_at'))
        missing_reference = self.client.patch(
            url,
            {'status': 'paid'},
            content_type='application/json',
        )
        self.assertEqual(missing_reference.status_code, 400)

        paid = self.client.patch(
            url,
            {'status': 'paid', 'provider_payout_id': 'po_test_123'},
            content_type='application/json',
        )
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(paid.json()['status'], Payout.Status.PAID)
