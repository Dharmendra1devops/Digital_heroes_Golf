from rest_framework import serializers

from apps.scores.models import GolfScore


class GolfScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfScore
        fields = ('id', 'score_date', 'score', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_score(self, value):
        if not 1 <= value <= 45:
            raise serializers.ValidationError('Stableford scores must be between 1 and 45.')
        return value
