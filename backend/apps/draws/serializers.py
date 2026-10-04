from rest_framework import serializers

from apps.draws.models import Draw, DrawConfiguration, DrawPrizeTierConfiguration, DrawRun, DrawTierPool


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
        contribution_bps = attrs.get(
            'prize_pool_contribution_bps',
            getattr(self.instance, 'prize_pool_contribution_bps', None),
        )
        if contribution_bps is not None and not 1 <= contribution_bps <= 10000:
            raise serializers.ValidationError({
                'prize_pool_contribution_bps': 'Choose a contribution greater than 0% and at most 100%.',
            })
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


class DrawTierPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrawTierPool
        fields = (
            'match_count', 'share_bps', 'available_minor', 'rollover_in_minor',
            'rollover_out_minor', 'currency',
        )


class DrawSerializer(serializers.ModelSerializer):
    winning_numbers = serializers.SerializerMethodField()
    prize_pools = serializers.SerializerMethodField()

    def get_winning_numbers(self, draw):
        published_run = next((run for run in draw.runs.all() if run.is_published), None)
        if published_run is None:
            return []
        return [number.number for number in published_run.winning_numbers.all()]

    def get_prize_pools(self, draw):
        return DrawTierPoolSerializer(draw.tier_pools.all(), many=True).data

    class Meta:
        model = Draw
        fields = (
            'id', 'configuration', 'scheduled_at', 'eligibility_cutoff',
            'status', 'configuration_snapshot', 'published_at', 'created_at',
            'winning_numbers', 'prize_pools',
        )
        read_only_fields = ('id', 'status', 'configuration_snapshot', 'published_at', 'created_at')


class DrawRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrawRun
        fields = (
            'id', 'draw', 'run_number', 'run_type', 'algorithm_version', 'input_hash',
            'result_snapshot', 'audit_metadata', 'is_published', 'created_at',
        )
