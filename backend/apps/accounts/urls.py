from django.urls import path

from apps.accounts.views import (
    AdminOverviewView,
    AdminUserDetailView,
    AdminUserListView,
    AdminUserScoreDetailView,
    CurrentAccountView,
    LoginView,
    LogoutView,
    MemberPasswordChangeView,
    RegisterView,
    csrf_cookie,
)

app_name = 'accounts'

urlpatterns = [
    path('csrf/', csrf_cookie, name='csrf'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', CurrentAccountView.as_view(), name='me'),
    path('me/password/', MemberPasswordChangeView.as_view(), name='me-password'),
    path('admin/overview/', AdminOverviewView.as_view(), name='admin-overview'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:user_id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path(
        'admin/users/<int:user_id>/scores/<uuid:score_id>/',
        AdminUserScoreDetailView.as_view(),
        name='admin-user-score-detail',
    ),
]
