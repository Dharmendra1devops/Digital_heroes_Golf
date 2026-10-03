from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.draws.models import Draw, DrawConfiguration
from apps.draws.serializers import DrawConfigurationSerializer, DrawRunSerializer, DrawSerializer
from apps.draws.services import simulate_draw


class PublicDrawListView(generics.ListAPIView):
    serializer_class = DrawSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Draw.objects.filter(status=Draw.Status.PUBLISHED).order_by('-scheduled_at')


class AdminDrawConfigurationListCreateView(generics.ListCreateAPIView):
    queryset = DrawConfiguration.objects.prefetch_related('prize_tiers').all().order_by('-version')
    serializer_class = DrawConfigurationSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminDrawListCreateView(generics.ListCreateAPIView):
    queryset = Draw.objects.select_related('configuration').all().order_by('-scheduled_at')
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
