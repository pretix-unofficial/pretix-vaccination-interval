from django.conf.urls import url
from pretix_vaccination_interval.views import VaccSettings

urlpatterns = [
    url(r'^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/vaccinationinterval/$',
        VaccSettings.as_view(), name='settings'),
]
