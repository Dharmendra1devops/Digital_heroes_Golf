import os

import stripe
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.models import StripeCustomer
from apps.subscriptions.models import Subscription, SubscriptionPlan
from apps.subscriptions.serializers import (
    AdminSubscriptionPlanSerializer,
    MemberSubscriptionSerializer,
    SubscriptionPlanSerializer,
)


class SubscriptionPlanListView(generics.ListAPIView):
    queryset = SubscriptionPlan.objects.filter(is_active=True).order_by('amount_minor')
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]


class AdminSubscriptionPlanListCreateView(generics.ListCreateAPIView):
    queryset = SubscriptionPlan.objects.all().order_by('amount_minor')
    serializer_class = AdminSubscriptionPlanSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminSubscriptionPlanDetailView(generics.RetrieveUpdateAPIView):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = AdminSubscriptionPlanSerializer
    permission_classes = [permissions.IsAdminUser]


class MemberSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        subscription = (
            Subscription.objects.select_related('plan')
            .filter(user=request.user)
            .order_by('-current_period_end', '-created_at')
            .first()
        )
        if subscription is None:
            return Response({'subscription': None})
        return Response({'subscription': MemberSubscriptionSerializer(subscription).data})


class CancelSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        subscription = (
            Subscription.objects.filter(
                user=request.user,
                status__in=(Subscription.Status.ACTIVE, Subscription.Status.TRIALING),
                current_period_end__gt=timezone.now(),
            )
            .order_by('-current_period_end')
            .first()
        )
        if subscription is None:
            return Response({'detail': 'No active subscription can be cancelled.'}, status=status.HTTP_404_NOT_FOUND)
        if subscription.cancel_at_period_end:
            return Response({'subscription': MemberSubscriptionSerializer(subscription).data})

        secret_key = os.getenv('STRIPE_SECRET_KEY', '').strip()
        if not secret_key or secret_key.startswith('sk_test_your_key') or not subscription.stripe_subscription_id:
            return Response(
                {'code': 'stripe_not_configured', 'detail': 'Subscription changes are not available right now.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            updated = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True,
                api_key=secret_key,
            )
        except stripe.StripeError:
            return Response(
                {'detail': 'Cancellation could not be confirmed. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        subscription.cancel_at_period_end = bool(getattr(updated, 'cancel_at_period_end', True))
        subscription.canceled_at = timezone.now()
        subscription.save(update_fields=('cancel_at_period_end', 'canceled_at', 'updated_at'))
        return Response({'subscription': MemberSubscriptionSerializer(subscription).data})


class SubscriptionCheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        interval = request.data.get('interval')
        if interval not in SubscriptionPlan.Interval.values:
            return Response({'detail': 'Choose a monthly or yearly plan.'}, status=status.HTTP_400_BAD_REQUEST)

        plan = SubscriptionPlan.objects.filter(interval=interval, is_active=True).first()
        if plan is None:
            return Response({'detail': 'This subscription plan is not available.'}, status=status.HTTP_404_NOT_FOUND)

        secret_key = os.getenv('STRIPE_SECRET_KEY', '').strip()
        if not secret_key or secret_key.startswith('sk_test_your_key'):
            return Response(
                {'code': 'stripe_not_configured', 'detail': 'Payments are not configured yet.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not plan.stripe_price_id:
            return Response(
                {'code': 'stripe_price_not_configured', 'detail': 'This plan is not ready for checkout yet.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        customer_link = StripeCustomer.objects.filter(user=request.user).first()
        try:
            if customer_link is None:
                profile = getattr(request.user, 'profile', None)
                email = profile.email if profile else request.user.email
                customer = stripe.Customer.create(
                    email=email,
                    metadata={'user_id': str(request.user.pk)},
                    api_key=secret_key,
                    idempotency_key=f'digital-heroes-customer-{request.user.pk}',
                )
                customer_link = StripeCustomer.objects.create(
                    user=request.user,
                    stripe_customer_id=customer.id,
                )

            frontend_url = os.getenv('FRONTEND_BASE_URL', 'http://127.0.0.1:3000').rstrip('/')
            session = stripe.checkout.Session.create(
                mode='subscription',
                customer=customer_link.stripe_customer_id,
                line_items=[{'price': plan.stripe_price_id, 'quantity': 1}],
                client_reference_id=str(request.user.pk),
                subscription_data={
                    'metadata': {
                        'user_id': str(request.user.pk),
                        'plan_id': str(plan.pk),
                    },
                },
                success_url=f'{frontend_url}/dashboard?checkout=success',
                cancel_url=f'{frontend_url}/subscribe?checkout=cancelled',
                api_key=secret_key,
            )
        except stripe.StripeError:
            return Response(
                {'detail': 'Checkout is temporarily unavailable. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({'checkout_url': session.url}, status=status.HTTP_201_CREATED)
