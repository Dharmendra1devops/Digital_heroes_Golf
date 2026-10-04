import os

import stripe
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.models import StripeCustomer
from apps.payments.stripe_utils import get_stripe_test_secret_key
from apps.subscriptions.models import Subscription, SubscriptionPlan
from apps.subscriptions.serializers import (
    AdminSubscriptionPlanSerializer,
    AdminSubscriptionSerializer,
    MemberPlanChangeSerializer,
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

        secret_key = get_stripe_test_secret_key()
        if not secret_key or not subscription.stripe_subscription_id:
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


class ResumeSubscriptionView(APIView):
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
            return Response({'detail': 'No active subscription can be resumed.'}, status=status.HTTP_404_NOT_FOUND)
        if not subscription.cancel_at_period_end:
            return Response(
                {'detail': 'This subscription is not scheduled to cancel.'},
                status=status.HTTP_409_CONFLICT,
            )

        secret_key = get_stripe_test_secret_key()
        if not secret_key or not subscription.stripe_subscription_id:
            return Response(
                {'code': 'stripe_not_configured', 'detail': 'Subscription changes are not available right now.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            updated = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False,
                api_key=secret_key,
            )
        except stripe.StripeError:
            return Response(
                {'detail': 'Renewal could not be confirmed. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if bool(getattr(updated, 'cancel_at_period_end', True)):
            return Response(
                {'detail': 'Stripe did not confirm the renewal change. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None
        subscription.save(update_fields=('cancel_at_period_end', 'canceled_at', 'updated_at'))
        return Response({'subscription': MemberSubscriptionSerializer(subscription).data})


class MemberPlanChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan_serializer = MemberPlanChangeSerializer(data=request.data)
        plan_serializer.is_valid(raise_exception=True)
        plan = get_object_or_404(
            SubscriptionPlan,
            pk=plan_serializer.validated_data['plan_id'],
            is_active=True,
        )
        subscription = (
            Subscription.objects.select_related('plan')
            .filter(
                user=request.user,
                status__in=(Subscription.Status.ACTIVE, Subscription.Status.TRIALING),
                current_period_end__gt=timezone.now(),
            )
            .order_by('-current_period_end')
            .first()
        )
        if subscription is None:
            return Response({'detail': 'No in-period subscription can be changed.'}, status=status.HTTP_404_NOT_FOUND)
        if subscription.cancel_at_period_end:
            return Response(
                {'detail': 'Resume renewal before changing your plan.'},
                status=status.HTTP_409_CONFLICT,
            )
        if plan.pk == subscription.plan_id:
            return Response({'subscription': MemberSubscriptionSerializer(subscription).data})
        if plan.currency != subscription.plan.currency:
            return Response(
                {'detail': 'Plan changes must use the same billing currency.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        secret_key = get_stripe_test_secret_key()
        if not secret_key or not subscription.stripe_subscription_id or not plan.stripe_price_id:
            return Response(
                {'code': 'stripe_not_configured', 'detail': 'Plan changes are not available right now.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            current = stripe.Subscription.retrieve(
                subscription.stripe_subscription_id,
                api_key=secret_key,
            )
            items = getattr(getattr(current, 'items', None), 'data', [])
            if not items:
                return Response(
                    {'detail': 'The current Stripe subscription has no billing item to update.'},
                    status=status.HTTP_409_CONFLICT,
                )
            updated = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{'id': items[0].id, 'price': plan.stripe_price_id}],
                proration_behavior='create_prorations',
                payment_behavior='error_if_incomplete',
                api_key=secret_key,
            )
        except stripe.StripeError:
            return Response(
                {'detail': 'The plan change could not be confirmed. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        updated_items = getattr(getattr(updated, 'items', None), 'data', [])
        confirmed_price = None
        for item in updated_items:
            price = getattr(item, 'price', None)
            price_id = getattr(price, 'id', price)
            if price_id == plan.stripe_price_id:
                confirmed_price = price_id
                break
        if (
            getattr(updated, 'status', subscription.status)
            not in (Subscription.Status.ACTIVE, Subscription.Status.TRIALING)
            or confirmed_price != plan.stripe_price_id
        ):
            return Response(
                {'detail': 'Stripe did not confirm the plan change. Please contact support.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        subscription.plan = plan
        subscription.save(update_fields=('plan', 'updated_at'))
        return Response({'subscription': MemberSubscriptionSerializer(subscription).data})


class AdminSubscriptionActionView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, subscription_id):
        action = request.data.get('action')
        if action not in {'cancel', 'resume'}:
            return Response(
                {'detail': 'Choose cancel or resume.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = get_object_or_404(
            Subscription.objects.select_related('plan', 'user'),
            pk=subscription_id,
            user__is_staff=False,
            user__is_superuser=False,
        )
        if (
            subscription.status not in (Subscription.Status.ACTIVE, Subscription.Status.TRIALING)
            or subscription.current_period_end is None
            or subscription.current_period_end <= timezone.now()
        ):
            return Response(
                {'detail': 'Only an in-period subscription can be changed.'},
                status=status.HTTP_409_CONFLICT,
            )
        if action == 'cancel' and subscription.cancel_at_period_end:
            return Response({'subscription': AdminSubscriptionSerializer(subscription).data})
        if action == 'resume' and not subscription.cancel_at_period_end:
            return Response(
                {'detail': 'This subscription is not scheduled to cancel.'},
                status=status.HTTP_409_CONFLICT,
            )

        secret_key = get_stripe_test_secret_key()
        if not secret_key or not subscription.stripe_subscription_id:
            return Response(
                {'code': 'stripe_not_configured', 'detail': 'Subscription changes are not available right now.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        cancel_at_period_end = action == 'cancel'
        try:
            updated = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=cancel_at_period_end,
                api_key=secret_key,
            )
        except stripe.StripeError:
            return Response(
                {'detail': 'The subscription change could not be confirmed. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        confirmed_cancel = bool(getattr(updated, 'cancel_at_period_end', cancel_at_period_end))
        subscription.cancel_at_period_end = confirmed_cancel
        subscription.canceled_at = timezone.now() if confirmed_cancel else None
        subscription.save(update_fields=('cancel_at_period_end', 'canceled_at', 'updated_at'))
        return Response({'subscription': AdminSubscriptionSerializer(subscription).data})


class SubscriptionCheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        interval = request.data.get('interval')
        if interval not in SubscriptionPlan.Interval.values:
            return Response({'detail': 'Choose a monthly or yearly plan.'}, status=status.HTTP_400_BAD_REQUEST)

        plan = SubscriptionPlan.objects.filter(interval=interval, is_active=True).first()
        if plan is None:
            return Response({'detail': 'This subscription plan is not available.'}, status=status.HTTP_404_NOT_FOUND)

        secret_key = get_stripe_test_secret_key()
        if not secret_key:
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

            frontend_url = os.getenv('FRONTEND_BASE_URL', 'http://localhost:3000').rstrip('/')
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
