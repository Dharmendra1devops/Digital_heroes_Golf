from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.http import JsonResponse
from rest_framework import generics, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import (
    AdminUserScoreSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    LoginSerializer,
    MemberPasswordChangeSerializer,
    MemberProfileUpdateSerializer,
    RegisterSerializer,
)
from apps.charities.models import Charity
from apps.draws.models import Draw, DrawTierPool
from apps.payments.models import Donation, FundingAllocation
from apps.scores.models import GolfScore
from apps.scores.services import delete_golf_score, save_golf_score
from apps.subscriptions.models import Subscription
from apps.winners.models import DrawWinner


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

    def patch(self, request):
        serializer = MemberProfileUpdateSerializer(
            request.user,
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'user': account_payload(request.user)})


class MemberPasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MemberPasswordChangeSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=('password',))
        update_session_auth_hash(request, request.user)
        return Response({'detail': 'Your password has been updated.'})


class AdminUserListView(generics.ListAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAdminUser]

    class Pagination(PageNumberPagination):
        page_size = 25
        max_page_size = 100

    pagination_class = Pagination

    def get_queryset(self):
        queryset = get_user_model().objects.filter(is_staff=False, is_superuser=False)
        search = self.request.query_params.get('q', '').strip()
        if search:
            queryset = queryset.filter(
                Q(profile__email__icontains=search)
                | Q(email__icontains=search)
                | Q(profile__display_name__icontains=search)
            )
        active = self.request.query_params.get('active')
        if active in {'true', 'false'}:
            queryset = queryset.filter(is_active=(active == 'true'))
        return queryset.select_related('profile').prefetch_related(
            Prefetch(
                'subscriptions',
                queryset=Subscription.objects.select_related('plan').order_by('-created_at'),
            ),
            Prefetch('golf_scores', queryset=GolfScore.objects.order_by('-score_date')),
        ).order_by('-date_joined')


class AdminUserDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, user_id):
        user = get_object_or_404(
            get_user_model().objects.select_related('profile'),
            pk=user_id,
            is_staff=False,
            is_superuser=False,
        )
        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminUserSerializer(user).data)


class AdminUserScoreDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, user_id, score_id):
        score = get_object_or_404(GolfScore, pk=score_id, user_id=user_id)
        serializer = AdminUserScoreSerializer(score, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        if not isinstance(validated_data, dict):
            raise RuntimeError('A valid score update did not produce validated data.')
        try:
            updated = save_golf_score(
                score.user,
                score.score_date,
                validated_data.get('score', score.score),
            )
        except DjangoValidationError as error:
            detail = error.message_dict if hasattr(error, 'message_dict') else error.messages
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AdminUserScoreSerializer(updated).data)

    def delete(self, request, user_id, score_id):
        score = get_object_or_404(GolfScore, pk=score_id, user_id=user_id)
        delete_golf_score(score.user, score.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminOverviewView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        user_model = get_user_model()
        active_subscription_filter = Q(
            subscriptions__status=Subscription.Status.ACTIVE,
            subscriptions__current_period_end__gt=timezone.now(),
        )
        user_summary = user_model.objects.filter(is_staff=False, is_superuser=False).aggregate(
            total_users=Count('id'),
            active_subscribers=Count('id', filter=active_subscription_filter, distinct=True),
        )
        prize_funding = list(
            FundingAllocation.objects.filter(
                allocation_type=FundingAllocation.Type.PRIZE_POOL,
            )
            .values('currency')
            .annotate(amount_minor=Sum('amount_minor'))
            .order_by('currency')
        )
        charity_totals = {
            item['currency']: item['amount_minor']
            for item in FundingAllocation.objects.filter(
                allocation_type=FundingAllocation.Type.CHARITY,
            )
            .values('currency')
            .annotate(amount_minor=Sum('amount_minor'))
        }
        donations_by_currency = Donation.objects.filter(
            status=Donation.Status.SUCCEEDED,
        ).values('currency').annotate(amount_minor=Sum('amount_minor'))
        for item in donations_by_currency:
            charity_totals[item['currency']] = (
                charity_totals.get(item['currency'], 0) + item['amount_minor']
            )
        return Response({
            **user_summary,
            'prize_funding_by_currency': prize_funding,
            'charity_contributions_by_currency': [
                {'currency': currency, 'amount_minor': amount}
                for currency, amount in sorted(charity_totals.items())
            ],
            'draws_by_status': list(
                Draw.objects.values('status').annotate(count=Count('id')).order_by('status')
            ),
            'distributed_pools_by_currency': list(
                DrawTierPool.objects.values('currency')
                .annotate(distributed_minor=Sum('available_minor'))
                .order_by('currency')
            ),
            'top_charities': list(
                Charity.objects.filter(donations__status=Donation.Status.SUCCEEDED)
                .values('id', 'name', 'donations__currency')
                .annotate(
                    donation_total_minor=Sum('donations__amount_minor'),
                )
                .order_by('-donation_total_minor', 'name', 'donations__currency')[:10]
            ),
            'total_winners': DrawWinner.objects.count(),
        })
