from django.urls import path

from apps.charities.views import (
    CharityAdminDetailView,
    CharityAdminListCreateView,
    CharityDetailView,
    CharityListView,
    CharitySelectionView,
)

app_name = 'charities'

urlpatterns = [
    path('', CharityListView.as_view(), name='list'),
    path('selection/', CharitySelectionView.as_view(), name='selection'),
    path('admin/', CharityAdminListCreateView.as_view(), name='admin-list-create'),
    path('admin/<uuid:pk>/', CharityAdminDetailView.as_view(), name='admin-detail'),
    path('<slug:slug>/', CharityDetailView.as_view(), name='detail'),
]
