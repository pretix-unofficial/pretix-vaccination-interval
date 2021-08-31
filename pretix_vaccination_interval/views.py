from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _, gettext_noop  # NoQA
from pretix.base.forms import SettingsForm
from pretix.base.models import Event
from pretix.control.views.event import (
    EventSettingsFormView, EventSettingsViewMixin,
)


class VaccSettingsForm(SettingsForm):
    vaccination_interval_check = forms.BooleanField(
        label=_('Enable validation'),
        required=False,
    )
    vaccination_future_max = forms.IntegerField(
        label=_('Maximum time frame for first shot'),
        required=True,
        min_value=1,
        widget=forms.NumberInput(
            attrs={'addon_after': _('days')}
        ),
    )
    vaccination_interval_min = forms.IntegerField(
        label=_('Minimum interval between first and second shot'),
        required=True,
        min_value=1,
        widget=forms.NumberInput(
            attrs={'addon_after': _('days')}
        ),
    )
    vaccination_interval_max = forms.IntegerField(
        label=_('Maximum interval between first and second shot'),
        required=True,
        min_value=1,
        widget=forms.NumberInput(
            attrs={'addon_after': _('days')}
        ),
    )


class VaccSettings(EventSettingsViewMixin, EventSettingsFormView):
    model = Event
    form_class = VaccSettingsForm
    template_name = 'pretix_vaccination_interval/settings.html'
    permission = 'can_change_event_settings'

    def get_success_url(self) -> str:
        return reverse('plugins:pretix_vaccination_interval:settings', kwargs={
            'organizer': self.request.event.organizer.slug,
            'event': self.request.event.slug
        })
