from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.charities.models import Charity, CharitySelection
from apps.charities.serializers import CharityAdminSerializer, CharitySelectionSerializer, CharitySerializer
from apps.charities.services import select_charity


class CharityListView(generics.ListAPIView):
    serializer_class = CharitySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Charity.objects.filter(is_active=True).prefetch_related('events')
        query = self.request.query_params.get('q', '').strip()
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(description__icontains=query))
        featured = self.request.query_params.get('featured')
        if featured in {'true', 'false'}:
            queryset = queryset.filter(is_featured=(featured == 'true'))
        return queryset


class CharityDetailView(generics.RetrieveAPIView):
    serializer_class = CharitySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        return Charity.objects.filter(is_active=True).prefetch_related('events')


class CharityAdminListCreateView(generics.ListCreateAPIView):
    queryset = Charity.objects.all()
    serializer_class = CharityAdminSerializer
    permission_classes = [permissions.IsAdminUser]


class CharityAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Charity.objects.all()
    serializer_class = CharityAdminSerializer
    permission_classes = [permissions.IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'This charity has financial or selection history. Deactivate it instead.'},
                status=status.HTTP_409_CONFLICT,
            )


class CharitySelectionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        selection = (
            CharitySelection.objects.select_related('charity')
            .filter(user=request.user, effective_to__isnull=True)
            .first()
        )
        if selection is None:
            return Response({'selection': None})
        return Response({'selection': CharitySelectionSerializer(selection).data})

    def put(self, request):
        serializer = CharitySelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            selection = select_charity(
                request.user,
                serializer.validated_data['charity_id'],
                serializer.validated_data['contribution_bps'],
            )
        except (DjangoValidationError, Charity.DoesNotExist) as error:
            detail = error.message_dict if hasattr(error, 'message_dict') else str(error)
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'selection': CharitySelectionSerializer(selection).data})

    def delete(self, request):
        current = CharitySelection.objects.filter(user=request.user, effective_to__isnull=True).first()
        if current is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        current.effective_to = timezone.now()
        current.save(update_fields=('effective_to', 'updated_at'))
        return Response(status=status.HTTP_204_NO_CONTENT)
