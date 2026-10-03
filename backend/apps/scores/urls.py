from django.urls import path

from apps.scores.views import ScoreDetailView, ScoreListCreateView

app_name = 'scores'

urlpatterns = [
    path('', ScoreListCreateView.as_view(), name='list-create'),
    path('<uuid:pk>/', ScoreDetailView.as_view(), name='detail'),
]
