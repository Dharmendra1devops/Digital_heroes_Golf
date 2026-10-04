from django.urls import path

from apps.subscriptions.views import (
    AdminSubscriptionPlanDetailView,
    AdminSubscriptionPlanListCreateView,
    AdminSubscriptionActionView,
    CancelSubscriptionView,
    MemberPlanChangeView,
    MemberSubscriptionView,
    ResumeSubscriptionView,
    SubscriptionCheckoutView,
    SubscriptionPlanListView,
)

app_name = 'subscriptions'

urlpatterns = [
    path('plans/', SubscriptionPlanListView.as_view(), name='plans'),
    path('checkout/', SubscriptionCheckoutView.as_view(), name='checkout'),
    path('me/', MemberSubscriptionView.as_view(), name='me'),
    path('me/cancel/', CancelSubscriptionView.as_view(), name='cancel'),
    path('me/resume/', ResumeSubscriptionView.as_view(), name='resume'),
    path('me/change-plan/', MemberPlanChangeView.as_view(), name='change-plan'),
    path('admin/plans/', AdminSubscriptionPlanListCreateView.as_view(), name='admin-plans'),
    path('admin/plans/<uuid:pk>/', AdminSubscriptionPlanDetailView.as_view(), name='admin-plan-detail'),
    path('admin/subscriptions/<uuid:subscription_id>/action/', AdminSubscriptionActionView.as_view(), name='admin-subscription-action'),
]
