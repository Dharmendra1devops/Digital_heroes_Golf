from django.urls import path

from apps.draws.views import (
    AdminDrawConfigurationListCreateView,
    AdminDrawListCreateView,
    AdminDrawSimulationView,
    PublicDrawListView,
)

app_name = 'draws'

urlpatterns = [
    path('', PublicDrawListView.as_view(), name='published-list'),
    path('admin/configurations/', AdminDrawConfigurationListCreateView.as_view(), name='admin-configurations'),
    path('admin/', AdminDrawListCreateView.as_view(), name='admin-list-create'),
    path('admin/<uuid:draw_id>/simulate/', AdminDrawSimulationView.as_view(), name='admin-simulate'),
]
