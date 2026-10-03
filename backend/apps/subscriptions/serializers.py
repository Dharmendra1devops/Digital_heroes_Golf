import os

from rest_framework import serializers

from apps.subscriptions.models import Subscription, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    checkout_available = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = ('id', 'interval', 'amount_minor', 'currency', 'checkout_available')

    def get_checkout_available(self, plan):
        secret_key = os.getenv('STRIPE_SECRET_KEY', '').strip()
        return bool(
            plan.stripe_price_id
            and secret_key
            and not secret_key.startswith('sk_test_your_key')
        )


class AdminSubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ('id', 'interval', 'amount_minor', 'currency', 'stripe_price_id', 'is_active')
        read_only_fields = ('id',)


class MemberSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            'id', 'plan', 'status', 'current_period_start', 'current_period_end',
            'cancel_at_period_end', 'canceled_at', 'ended_at',
        )
