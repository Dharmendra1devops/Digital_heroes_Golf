from django.urls import path

from apps.winners.views import (
    AdminPayoutListView,
    AdminWinnerListView,
    AdminWinnerProofReviewView,
    AdminWinnerProofSignedUrlView,
    MyWinnersView,
    WinnerProofView,
)

app_name = 'winners'

urlpatterns = [
    path('me/', MyWinnersView.as_view(), name='my-winners'),
    path('<uuid:winner_id>/proofs/', WinnerProofView.as_view(), name='proofs'),
    path('admin/', AdminWinnerListView.as_view(), name='admin-list'),
    path('admin/proofs/<uuid:proof_id>/signed-url/', AdminWinnerProofSignedUrlView.as_view(), name='admin-proof-url'),
    path('admin/proofs/<uuid:proof_id>/review/', AdminWinnerProofReviewView.as_view(), name='admin-proof-review'),
    path('admin/payouts/', AdminPayoutListView.as_view(), name='admin-payouts'),
    path('admin/payouts/<uuid:payout_id>/', AdminPayoutListView.as_view(), name='admin-payout-update'),
]
