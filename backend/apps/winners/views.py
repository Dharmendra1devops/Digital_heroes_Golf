from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.winners.models import DrawWinner, Payout, WinnerProof
from apps.winners.serializers import (
    AdminWinnerProofReviewSerializer,
    PayoutSerializer,
    WinnerProofSerializer,
    WinnerSerializer,
)
from apps.winners.services import StorageUnavailable, create_signed_proof_url, store_winner_proof


class MyWinnersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        winners = (
            DrawWinner.objects.filter(entry__user=request.user)
            .prefetch_related('proofs', 'payouts')
            .order_by('-created_at')
        )
        return Response(WinnerSerializer(winners, many=True).data)


class WinnerProofView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, winner_id):
        winner = get_object_or_404(DrawWinner, pk=winner_id, entry__user=request.user)
        return Response(WinnerProofSerializer(winner.proofs.all(), many=True).data)

    def post(self, request, winner_id):
        winner = get_object_or_404(DrawWinner, pk=winner_id, entry__user=request.user)
        if winner.verification_status == DrawWinner.VerificationStatus.APPROVED:
            return Response({'detail': 'This winner claim has already been approved.'}, status=status.HTTP_409_CONFLICT)
        proof = request.FILES.get('proof')
        if proof is None:
            return Response({'proof': 'A proof image is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            record = store_winner_proof(proof, winner.pk)
        except DjangoValidationError as error:
            return Response(error.message_dict, status=status.HTTP_400_BAD_REQUEST)
        except StorageUnavailable as error:
            return Response(
                {'code': 'storage_not_configured', 'detail': str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(WinnerProofSerializer(record).data, status=status.HTTP_201_CREATED)


class AdminWinnerListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        winners = DrawWinner.objects.select_related('entry', 'entry__draw').prefetch_related('proofs', 'payouts')
        verification_status = request.query_params.get('status')
        if verification_status in DrawWinner.VerificationStatus.values:
            winners = winners.filter(verification_status=verification_status)
        return Response(WinnerSerializer(winners.order_by('-created_at'), many=True).data)


class AdminWinnerProofReviewView(APIView):
    permission_classes = [permissions.IsAdminUser]

    @transaction.atomic
    def patch(self, request, proof_id):
        proof = get_object_or_404(WinnerProof.objects.select_for_update(), pk=proof_id)
        serializer = AdminWinnerProofReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review_status = serializer.validated_data['review_status']
        if proof.review_status != WinnerProof.ReviewStatus.PENDING:
            return Response({'detail': 'This proof has already been reviewed.'}, status=status.HTTP_409_CONFLICT)

        proof.review_status = review_status
        proof.reviewed_by = request.user
        proof.reviewed_at = timezone.now()
        proof.review_reason = serializer.validated_data.get('review_reason', '').strip()
        proof.save(update_fields=('review_status', 'reviewed_by', 'reviewed_at', 'review_reason', 'updated_at'))

        winner = DrawWinner.objects.select_for_update().get(pk=proof.winner_id)
        winner_status = (
            DrawWinner.VerificationStatus.APPROVED
            if review_status == WinnerProof.ReviewStatus.APPROVED
            else DrawWinner.VerificationStatus.REJECTED
        )
        winner.verification_status = winner_status
        winner.reviewed_by = request.user
        winner.reviewed_at = proof.reviewed_at
        winner.review_reason = proof.review_reason
        winner.save(update_fields=('verification_status', 'reviewed_by', 'reviewed_at', 'review_reason', 'updated_at'))
        return Response(WinnerProofSerializer(proof).data)


class AdminWinnerProofSignedUrlView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, proof_id):
        proof = get_object_or_404(WinnerProof, pk=proof_id)
        try:
            signed_url = create_signed_proof_url(proof)
        except StorageUnavailable as error:
            return Response(
                {'code': 'storage_not_configured', 'detail': str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({'signed_url': signed_url, 'expires_in': 900})


class AdminPayoutListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        payouts = Payout.objects.select_related('winner').order_by('-created_at')
        return Response(PayoutSerializer(payouts, many=True).data)

    @transaction.atomic
    def patch(self, request, payout_id):
        payout = get_object_or_404(Payout.objects.select_for_update().select_related('winner'), pk=payout_id)
        target_status = request.data.get('status')
        if target_status == Payout.Status.PAID:
            provider_id = request.data.get('provider_payout_id', '').strip()
            if payout.winner.verification_status != DrawWinner.VerificationStatus.APPROVED:
                return Response({'detail': 'Winner verification must be approved before payout.'}, status=status.HTTP_409_CONFLICT)
            if not provider_id:
                return Response({'provider_payout_id': 'A provider payout reference is required.'}, status=status.HTTP_400_BAD_REQUEST)
            payout.status = Payout.Status.PAID
            payout.provider_payout_id = provider_id
            payout.paid_at = timezone.now()
            payout.failure_reason = ''
        elif target_status == Payout.Status.FAILED:
            payout.status = Payout.Status.FAILED
            payout.failure_reason = str(request.data.get('failure_reason', '')).strip()
        else:
            return Response({'status': 'Choose paid or failed.'}, status=status.HTTP_400_BAD_REQUEST)
        payout.save(update_fields=('status', 'provider_payout_id', 'paid_at', 'failure_reason', 'updated_at'))
        return Response(PayoutSerializer(payout).data)
