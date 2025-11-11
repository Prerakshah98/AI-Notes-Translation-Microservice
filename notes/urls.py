from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnalyticsStatsView, NoteViewSet

router = DefaultRouter()
router.register(r'notes', NoteViewSet, basename='note')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', AnalyticsStatsView.as_view(), name='analytics-stats'),
]