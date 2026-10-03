from django.utils import timezone
from rest_framework import serializers

from apps.charities.models import Charity, CharityEvent, CharitySelection


class CharityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharityEvent
        fields = ('id', 'title', 'description', 'starts_at', 'ends_at', 'location', 'image_path')


class CharitySerializer(serializers.ModelSerializer):
    upcoming_events = serializers.SerializerMethodField()

    class Meta:
        model = Charity
        fields = (
            'id', 'slug', 'name', 'description', 'image_path', 'website',
            'is_featured', 'upcoming_events',
        )
        read_only_fields = ('id',)

    def get_upcoming_events(self, charity):
        events = charity.events.filter(starts_at__gte=timezone.now()).order_by('starts_at')[:5]
        return CharityEventSerializer(events, many=True).data


class CharityAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charity
        fields = (
            'id', 'slug', 'name', 'description', 'image_path', 'website',
            'is_active', 'is_featured', 'display_order', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class CharitySelectionSerializer(serializers.ModelSerializer):
    charity = CharitySerializer(read_only=True)
    charity_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = CharitySelection
        fields = ('id', 'charity', 'charity_id', 'contribution_bps', 'effective_from', 'effective_to')
        read_only_fields = ('id', 'effective_from', 'effective_to')

    def validate_charity_id(self, value):
        if not Charity.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError('Choose an active charity.')
        return value

    def validate_contribution_bps(self, value):
        if not 1000 <= value <= 10000:
            raise serializers.ValidationError('Contribution must be between 10% and 100%.')
        return value
