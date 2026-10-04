from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Prefetch, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.draws.models import Draw, DrawConfiguration, DrawEntry, DrawRun
from apps.draws.serializers import DrawConfigurationSerializer, DrawRunSerializer, DrawSerializer
from apps.draws.services import publish_draw, simulate_draw
from apps.winners.models import DrawWinner, Payout


class PublicDrawListView(generics.ListAPIView):
    serializer_class = DrawSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        published_runs = DrawRun.objects.filter(is_published=True).prefetch_related('winning_numbers')
        return (
            Draw.objects.filter(status=Draw.Status.PUBLISHED)
            .prefetch_related(
                Prefetch('runs', queryset=published_runs),
                'tier_pools',
            )
            .order_by('-scheduled_at')
        )


class MemberDrawSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        entries = DrawEntry.objects.filter(user=request.user)
        entry_draw_ids = entries.values_list('draw_id', flat=True)
        upcoming = (
            Draw.objects.filter(
                status__in=(Draw.Status.DRAFT, Draw.Status.SIMULATED),
                scheduled_at__gt=now,
            )
            .order_by('scheduled_at')[:5]
        )
        winnings = (
            DrawWinner.objects.filter(entry__user=request.user)
            .values('currency')
            .annotate(amount_minor=Sum('prize_amount_minor'))
            .order_by('currency')
        )
        payout_status = (
            Payout.objects.filter(winner__entry__user=request.user)
            .values('status', 'currency')
            .annotate(amount_minor=Sum('amount_minor'), count=Count('id'))
            .order_by('currency', 'status')
        )
        entered_draw_ids = set(entry_draw_ids)
        upcoming_draws = []
        for draw in upcoming:
            scheduled_at = draw.scheduled_at
            if scheduled_at is None:
                raise RuntimeError(f'Upcoming draw {draw.pk} has no scheduled time.')
            upcoming_draws.append({
                'id': str(draw.pk),
                'scheduled_at': scheduled_at.isoformat(),
                'entered': draw.pk in entered_draw_ids,
            })
        return Response({
            'draws_entered': entries.count(),
            'upcoming_draws': upcoming_draws,
            'winnings_by_currency': list(winnings),
            'payouts_by_status': list(payout_status),
        })


class AdminDrawConfigurationListCreateView(generics.ListCreateAPIView):
    queryset = DrawConfiguration.objects.prefetch_related('prize_tiers').all().order_by('-version')
    serializer_class = DrawConfigurationSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminDrawListCreateView(generics.ListCreateAPIView):
    published_runs = DrawRun.objects.filter(is_published=True).prefetch_related('winning_numbers')
    queryset = (
        Draw.objects.select_related('configuration')
        .prefetch_related(Prefetch('runs', queryset=published_runs), 'tier_pools')
        .all()
        .order_by('-scheduled_at')
    )
    serializer_class = DrawSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminDrawSimulationView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, draw_id):
        draw = get_object_or_404(Draw, pk=draw_id)
        try:
            run = simulate_draw(draw.pk)
        except DjangoValidationError as error:
            detail = error.message_dict if hasattr(error, 'message_dict') else error.messages
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'run': DrawRunSerializer(run).data}, status=status.HTTP_201_CREATED)


class AdminDrawPublishView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, draw_id):
        draw = get_object_or_404(Draw, pk=draw_id)
        try:
            run = publish_draw(draw.pk, request.user)
        except DjangoValidationError as error:
            detail = error.message_dict if hasattr(error, 'message_dict') else error.messages
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'run': DrawRunSerializer(run).data}, status=status.HTTP_201_CREATED)
