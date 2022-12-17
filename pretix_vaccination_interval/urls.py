from django.urls import path
from pretix_vaccination_interval.views import VaccSettings

urlpatterns = [
    path('control/event/<str:organizer>/<str:event>/vaccinationinterval/',
        VaccSettings.as_view(), name='settings'),
]
