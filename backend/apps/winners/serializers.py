from rest_framework import serializers

from apps.winners.models import DrawWinner, Payout, WinnerProof


class WinnerProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = WinnerProof
        fields = (
            'id', 'bucket', 'object_path', 'review_status', 'submitted_at',
            'reviewed_by', 'reviewed_at', 'review_reason',
        )


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = (
            'id', 'winner', 'attempt_number', 'amount_minor', 'currency', 'status',
            'provider_payout_id', 'paid_at', 'failure_reason', 'created_at',
        )


class WinnerSerializer(serializers.ModelSerializer):
    draw_id = serializers.UUIDField(source='entry.draw_id', read_only=True)
    proofs = WinnerProofSerializer(many=True, read_only=True)
    payouts = PayoutSerializer(many=True, read_only=True)

    class Meta:
        model = DrawWinner
        fields = (
            'id', 'draw_id', 'match_count', 'prize_amount_minor', 'currency',
            'verification_status', 'reviewed_at', 'review_reason', 'proofs', 'payouts',
        )


class AdminWinnerProofReviewSerializer(serializers.Serializer):
    review_status = serializers.ChoiceField(choices=WinnerProof.ReviewStatus.choices)
    review_reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)
