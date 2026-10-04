from rest_framework import serializers

from apps.payments.stripe_utils import get_stripe_test_secret_key
from apps.subscriptions.models import Subscription, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    checkout_available = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = ('id', 'interval', 'amount_minor', 'currency', 'checkout_available')

    def get_checkout_available(self, plan):
        return bool(
            plan.stripe_price_id
            and get_stripe_test_secret_key()
        )


class AdminSubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ('id', 'interval', 'amount_minor', 'currency', 'stripe_price_id', 'is_active')
        read_only_fields = ('id',)

    def validate_amount_minor(self, value):
        if value <= 0:
            raise serializers.ValidationError('Plan amount must be greater than zero.')
        return value

    def validate_currency(self, value):
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isascii() or not normalized.isalpha():
            raise serializers.ValidationError('Enter a three-letter ISO currency code.')
        return normalized

    def validate_stripe_price_id(self, value):
        normalized = value.strip()
        if not normalized.startswith('price_'):
            raise serializers.ValidationError('Enter a Stripe Price ID beginning with price_.')
        return normalized


class MemberSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            'id', 'plan', 'status', 'current_period_start', 'current_period_end',
            'cancel_at_period_end', 'canceled_at', 'ended_at',
        )


class MemberPlanChangeSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()


class AdminSubscriptionSerializer(serializers.ModelSerializer):
    plan_interval = serializers.CharField(source='plan.interval', read_only=True)

    class Meta:
        model = Subscription
        fields = (
            'id', 'plan_interval', 'status', 'current_period_start',
            'current_period_end', 'cancel_at_period_end',
        )
