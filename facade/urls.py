"""URL configuration for facade app."""

from django.urls import path
from . import views

app_name = 'facade'

urlpatterns = [
    path('hook-agent/events/', views.HookAgentEventView.as_view(), name='hook_agent_events'),
    path('hook-agent/heartbeat/', views.HookAgentHeartbeatView.as_view(), name='hook_agent_heartbeat'),
]