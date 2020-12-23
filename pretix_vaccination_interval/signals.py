from collections import Counter

from django.dispatch import receiver
from django.urls import resolve, reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _  # NoQA

from pretix.base.services.cart import CartError
from pretix.base.settings import settings_hierarkey
from pretix.base.signals import validate_cart
from pretix.control.signals import nav_event_settings


@receiver(nav_event_settings, dispatch_uid='pretix_vaccination_interval_nav_event_settings')
def nav_event_settings(sender, request, **kwargs):
    url = resolve(request.path_info)
    if not request.user.has_event_permission(request.organizer, request.event, 'can_change_event_settings',
                                             request=request):
        return []
    return [{
        'label': _('Vaccination interval'),
        'url': reverse('plugins:pretix_vaccination_interval:settings', kwargs={
            'event': request.event.slug,
            'organizer': request.organizer.slug,
        }),
        'active': url.namespace == 'plugins:pretix_vaccination_interval',
    }]


@receiver(validate_cart, dispatch_uid='pretix_vaccination_validate_cart')
def val_cart(sender, positions, **kwargs):
    subevent_counter = Counter([p.subevent for p in positions if p.addon_to_id is None])
    if len(subevent_counter) < 2:
        raise CartError(
            _('To proceed, please make sure your cart contains exactly two different dates. Currently, you only selected one date.')
        )
    if len(subevent_counter) > 2:
        raise CartError(
            _('To proceed, please make sure your cart contains no more than two different dates.')
        )
    if max(subevent_counter.values()) != min(subevent_counter.values()):
        raise CartError(
            _('You submitted a different number of registration for the two dates you selected, please make sure that the number of registrations matches exactly.')
        )

    first_date = min(subevent_counter.keys(), key=lambda s: s.date_from).date_from.astimezone(sender.timezone).date()
    last_date = max(subevent_counter.keys(), key=lambda s: s.date_from).date_from.astimezone(sender.timezone).date()
    this_date = now().astimezone(sender.timezone).date()

    if (first_date - this_date).days > sender.settings.vaccination_future_max:
        raise CartError(
            _('The first date you select must not be more than {max} days in the future, but you selected a date that is {current} days in the future.').format(
                max=sender.settings.vaccination_future_max,
                current=(first_date - this_date).days
            )
        )

    if (last_date - first_date).days > sender.settings.vaccination_interval_max:
        raise CartError(
            _('The dates you select must not be more than {max} days apart, but you selected two dates that are {current} days apart.').format(
                max=sender.settings.vaccination_interval_max,
                current=(last_date - first_date).days
            )
        )

    if (last_date - first_date).days < sender.settings.vaccination_interval_min:
        raise CartError(
            _('The dates you select must not be at least {min} days apart, but you selected two dates that are only {current} days apart.').format(
                min=sender.settings.vaccination_interval_min,
                current=(last_date - first_date).days
            )
        )


settings_hierarkey.add_default('vaccination_interval_min', 0, int)
settings_hierarkey.add_default('vaccination_interval_max', 0, int)
settings_hierarkey.add_default('vaccination_future_max', 0, int)
