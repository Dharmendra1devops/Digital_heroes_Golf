from rest_framework import serializers

from apps.draws.models import Draw, DrawConfiguration, DrawPrizeTierConfiguration, DrawRun


class DrawPrizeTierConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrawPrizeTierConfiguration
        fields = ('match_count', 'share_bps', 'rollover_unclaimed')


class DrawConfigurationSerializer(serializers.ModelSerializer):
    prize_tiers = DrawPrizeTierConfigurationSerializer(many=True, read_only=True)

    class Meta:
        model = DrawConfiguration
        fields = (
            'id', 'version', 'mode', 'candidate_min', 'candidate_max', 'number_count',
            'prize_pool_contribution_bps', 'parameters', 'prize_tiers',
        )
        read_only_fields = ('id', 'prize_tiers')

    def validate(self, attrs):
        minimum = attrs.get('candidate_min', getattr(self.instance, 'candidate_min', 1))
        maximum = attrs.get('candidate_max', getattr(self.instance, 'candidate_max', 45))
        count = attrs.get('number_count', getattr(self.instance, 'number_count', 5))
        if count > maximum - minimum + 1:
            raise serializers.ValidationError({'number_count': 'The candidate range cannot supply that many unique numbers.'})
        return attrs

    def create(self, validated_data):
        configuration = super().create(validated_data)
        DrawPrizeTierConfiguration.objects.bulk_create([
            DrawPrizeTierConfiguration(
                configuration=configuration,
                match_count=5,
                share_bps=4000,
                rollover_unclaimed=True,
            ),
            DrawPrizeTierConfiguration(
                configuration=configuration,
                match_count=4,
                share_bps=3500,
                rollover_unclaimed=False,
            ),
            DrawPrizeTierConfiguration(
                configuration=configuration,
                match_count=3,
                share_bps=2500,
                rollover_unclaimed=False,
            ),
        ])
        return configuration


class DrawSerializer(serializers.ModelSerializer):
    class Meta:
        model = Draw
        fields = (
            'id', 'configuration', 'scheduled_at', 'eligibility_cutoff',
            'status', 'configuration_snapshot', 'published_at', 'created_at',
        )
        read_only_fields = ('id', 'status', 'configuration_snapshot', 'published_at', 'created_at')


class DrawRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrawRun
        fields = (
            'id', 'draw', 'run_number', 'run_type', 'algorithm_version', 'input_hash',
            'result_snapshot', 'audit_metadata', 'is_published', 'created_at',
        )
