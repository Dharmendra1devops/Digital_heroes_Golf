from django.urls import path

from apps.draws.views import (
    AdminDrawConfigurationListCreateView,
    AdminDrawListCreateView,
    AdminDrawPublishView,
    AdminDrawSimulationView,
    MemberDrawSummaryView,
    PublicDrawListView,
)

app_name = 'draws'

urlpatterns = [
    path('', PublicDrawListView.as_view(), name='published-list'),
    path('me/summary/', MemberDrawSummaryView.as_view(), name='member-summary'),
    path('admin/configurations/', AdminDrawConfigurationListCreateView.as_view(), name='admin-configurations'),
    path('admin/', AdminDrawListCreateView.as_view(), name='admin-list-create'),
    path('admin/<uuid:draw_id>/publish/', AdminDrawPublishView.as_view(), name='admin-publish'),
    path('admin/<uuid:draw_id>/simulate/', AdminDrawSimulationView.as_view(), name='admin-simulate'),
]
