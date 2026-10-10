from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.scores.models import GolfScore
from apps.scores.serializers import GolfScoreSerializer
from apps.scores.services import delete_golf_score, save_golf_score
from apps.subscriptions.models import Subscription


def has_active_subscription(user):
    return Subscription.objects.filter(
        user=user,
        status=Subscription.Status.ACTIVE,
        current_period_end__gt=timezone.now(),
    ).exists()


def validation_error_payload(error):
    if hasattr(error, 'message_dict'):
        return error.message_dict
    return {'detail': error.messages}


class ScoreAccessView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def require_subscription(self, request):
        if has_active_subscription(request.user):
            return None
        return Response(
            {
                'code': 'subscription_required',
                'detail': 'To enter a golf score, please purchase a subscription plan.',
            },
            status=status.HTTP_403_FORBIDDEN,
        )


class ScoreListCreateView(ScoreAccessView):
    def get(self, request):
        denied = self.require_subscription(request)
        if denied is not None:
            return denied
        scores = GolfScore.objects.filter(user=request.user).order_by('-score_date')
        return Response(GolfScoreSerializer(scores, many=True).data)

    def post(self, request):
        denied = self.require_subscription(request)
        if denied is not None:
            return denied
        serializer = GolfScoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            score = save_golf_score(
                request.user,
                serializer.validated_data['score_date'],
                serializer.validated_data['score'],
                allow_update=False,
            )
        except DjangoValidationError as error:
            return Response(validation_error_payload(error), status=status.HTTP_400_BAD_REQUEST)
        return Response(GolfScoreSerializer(score).data, status=status.HTTP_201_CREATED)


class ScoreDetailView(ScoreAccessView):
    def get_object(self, request, pk):
        return get_object_or_404(GolfScore, pk=pk, user=request.user)

    def patch(self, request, pk):
        denied = self.require_subscription(request)
        if denied is not None:
            return denied
        instance = self.get_object(request, pk)
        serializer = GolfScoreSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            score = save_golf_score(
                request.user,
                instance.score_date,
                serializer.validated_data.get('score', instance.score),
            )
        except DjangoValidationError as error:
            return Response(validation_error_payload(error), status=status.HTTP_400_BAD_REQUEST)
        return Response(GolfScoreSerializer(score).data)

    def delete(self, request, pk):
        denied = self.require_subscription(request)
        if denied is not None:
            return denied
        score = self.get_object(request, pk)
        delete_golf_score(request.user, score.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
