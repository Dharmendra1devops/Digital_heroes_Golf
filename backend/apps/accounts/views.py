from django.contrib.auth import login, logout
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.http import JsonResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import LoginSerializer, RegisterSerializer
from apps.subscriptions.models import Subscription


def account_payload(user):
    profile = getattr(user, 'profile', None)
    active_subscription = Subscription.objects.filter(
        user=user,
        status=Subscription.Status.ACTIVE,
        current_period_end__gt=timezone.now(),
    ).order_by('-current_period_end').first()
    return {
        'id': str(user.pk),
        'email': profile.email if profile else user.email,
        'display_name': profile.display_name if profile else user.get_full_name(),
        'is_admin': user.is_staff,
        'is_subscriber': active_subscription is not None,
        'subscription_renews_at': (
            active_subscription.current_period_end.isoformat() if active_subscription else None
        ),
    }


@ensure_csrf_cookie
def csrf_cookie(request):
    return JsonResponse({'detail': 'CSRF cookie ready.'})


@method_decorator(csrf_protect, name='dispatch')
class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request._request, user, backend='django.contrib.auth.backends.ModelBackend')
        return Response({'user': account_payload(user)}, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request._request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request._request, user, backend='django.contrib.auth.backends.ModelBackend')
        return Response({'user': account_payload(user)})


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'user': account_payload(request.user)})
