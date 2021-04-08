from collections import OrderedDict, defaultdict
from decimal import Decimal

import dateutil
import pytz
from django import forms
from django.db.models import (
    Case, CharField, Count, DateTimeField, F, IntegerField, Max, Min, OuterRef,
    Subquery, Sum, When,
)
from django.db.models.functions import TruncDate
from django.utils.functional import cached_property
from django.utils.translation import gettext as _, gettext_lazy, pgettext
from pretix_shipping.models import ShippingAddress

from pretix.base.exporter import MultiSheetListExporter
from pretix.base.i18n import language
from pretix.base.models import (
    Invoice, InvoiceAddress, Order,
    OrderPosition, Question,
)
from pretix.base.models.orders import OrderFee, OrderPayment, OrderRefund
from pretix.base.settings import PERSON_NAME_SCHEMES
from pretix.helpers.iter import chunked_iterable


class OrderListExporter(MultiSheetListExporter):
    identifier = 'vacc_interval_list'
    verbose_name = gettext_lazy('Vaccination list')

    @property
    def sheets(self):
        return (
            ('positions', _('Order positions')),
        )

    @property
    def additional_form_fields(self):
        d = [
            ('date_from',
             forms.DateField(
                 label=_('Start date'),
                 widget=forms.DateInput(attrs={'class': 'datepickerfield'}),
                 required=False,
                 help_text=_('Only include orders created on or after this date.')
             )),
            ('date_to',
             forms.DateField(
                 label=_('End date'),
                 widget=forms.DateInput(attrs={'class': 'datepickerfield'}),
                 required=False,
                 help_text=_('Only include orders created on or before this date.')
             )),
            ('event_date_from',
             forms.DateField(
                 label=_('Start event date'),
                 widget=forms.DateInput(attrs={'class': 'datepickerfield'}),
                 required=False,
                 help_text=_('Only include orders including at least one ticket for a date on or after this date. '
                             'Will also include other dates in case of mixed orders!')
             )),
            ('event_date_to',
             forms.DateField(
                 label=_('End event date'),
                 widget=forms.DateInput(attrs={'class': 'datepickerfield'}),
                 required=False,
                 help_text=_('Only include orders including at least one ticket for a date on or after this date. '
                             'Will also include other dates in case of mixed orders!')
             )),
        ]
        d = OrderedDict(d)
        if not self.is_multievent and not self.event.has_subevents:
            del d['event_date_from']
            del d['event_date_to']
        return d

    def iterate_sheet(self, form_data, sheet):
        if sheet == 'positions':
            return self.iterate_positions(form_data)

    @cached_property
    def event_object_cache(self):
        return {e.pk: e for e in self.events}

    def _date_filter(self, qs, form_data):
        annotations = {}
        filters = {}

        if form_data.get('date_from'):
            date_value = form_data.get('date_from')
            if isinstance(date_value, str):
                date_value = dateutil.parser.parse(date_value).date()

            annotations['date'] = TruncDate(f'order__datetime')
            filters['date__gte'] = date_value

        if form_data.get('date_to'):
            date_value = form_data.get('date_to')
            if isinstance(date_value, str):
                date_value = dateutil.parser.parse(date_value).date()

            annotations['date'] = TruncDate(f'order__datetime')
            filters['date__lte'] = date_value

        if form_data.get('event_date_from'):
            date_value = form_data.get('event_date_from')
            if isinstance(date_value, str):
                date_value = dateutil.parser.parse(date_value).date()

            annotations['event_date_max'] = Case(
                When(**{f'subevent__isnull': False}, then=Max(f'subevent__date_from')),
                default=F(f'order__event__date_from'),
            )
            filters['event_date_max__gte'] = date_value

        if form_data.get('event_date_to'):
            date_value = form_data.get('event_date_to')
            if isinstance(date_value, str):
                date_value = dateutil.parser.parse(date_value).date()

            annotations['event_date_min'] = Case(
                When(**{f'subevent__isnull': False}, then=Min(f'subevent__date_from')),
                default=F(f'order__event__date_from'),
            )
            filters['event_date_min__lte'] = date_value

        if filters:
            return qs.annotate(**annotations).filter(**filters)
        return qs

    def iterate_positions(self, form_data: dict):
        base_qs = OrderPosition.objects.filter(
            order__event__in=self.events,
            order__status__in=(Order.STATUS_PENDING, Order.STATUS_PAID)
        )
        qs = base_qs.select_related(
            'order', 'order__invoice_address', 'item', 'variation', 'order__shipping_address'
        ).prefetch_related(
            'answers', 'answers__question', 'answers__options'
        )

        qs = self._date_filter(qs, form_data)

        headers = [
            _('Event slug'),
            _('Event'),
            pgettext('subevent', 'Date'),
            pgettext('subevent', 'Date'),
            _('Order code'),
            _('Position ID'),
            _('Email'),
            _('Phone number'),
            _('Order date'),
            _('Product'),
            _('Variation'),
            _('Count'),
        ]

        questions = list(Question.objects.filter(event__in=self.events))
        question_names = []
        qnamecache = {}
        for q in questions:
            if str(q.question) not in question_names:
                question_names.append(str(q.question))
            qnamecache[q.pk] = str(q.question)
        headers += question_names

        headers += [
            _('Shipping Company'), _('Shipping Name'), _('Shipping Address'), _('Shipping ZIP code'),
            _('Shipping City'),
            _('Shipping Country'),
            _('Shipping State'),
            _('Order comment'),
        ]
        yield headers

        all_ids = list(base_qs.order_by('subevent__date_from', 'order__datetime', 'order__code' 'positionid').values_list('pk', flat=True))
        yield self.ProgressSetTotal(total=len(all_ids))

        pending_row = None

        for ids in chunked_iterable(all_ids, 1000):
            ops = sorted(qs.filter(id__in=ids), key=lambda k: ids.index(k.pk))

            for op in ops:
                order = op.order
                tz = pytz.timezone(self.event_object_cache[order.event_id].settings.timezone)
                row = [
                    self.event_object_cache[order.event_id].slug,
                    str(self.event_object_cache[order.event_id].name),
                    (op.subevent or self.event_object_cache[order.event_id]).date_from.strftime('%Y-%m-%d'),
                    (op.subevent or self.event_object_cache[order.event_id]).date_from.strftime('%H:%M:%S'),
                    order.code,
                    op.positionid,
                    order.email,
                    str(order.phone) if order.phone else '',
                    order.datetime.astimezone(tz).strftime('%Y-%m-%d'),
                    str(op.item),
                    str(op.variation) if op.variation else '',
                    1,
                ]

                answers = [''] * len(question_names)
                for a in op.answers.all():
                    # We do not want to localize Date, Time and Datetime question answers, as those can lead
                    # to difficulties parsing the data (for example 2019-02-01 may become Février, 2019 01 in French).
                    if a.question.type == Question.TYPE_CHOICE_MULTIPLE:
                        answers[question_names.index(qnamecache[a.question_id])] = a.answer
                    elif a.question.type in Question.UNLOCALIZED_TYPES:
                        answers[question_names.index(qnamecache[a.question_id])] = a.answer
                    else:
                        answers[question_names.index(qnamecache[a.question_id])] = str(a)
                row += answers

                try:
                    row += [
                        order.shipping_address.company,
                        order.shipping_address.name,
                        order.shipping_address.street,
                        order.shipping_address.zipcode,
                        order.shipping_address.city,
                        order.shipping_address.country.name,
                        order.shipping_address.state
                    ]
                except ShippingAddress.DoesNotExist:
                    row += [''] * 7

                row.append(op.order.comment)

                ignore_idx = [5]
                counter_idx = 11
                if pending_row:
                    if all(pending_row[i] == row[i] for i in range(len(row)) if i not in ignore_idx and i != counter_idx):
                        for idx in ignore_idx:
                            pending_row[idx] = ''
                        pending_row[counter_idx] += 1
                    else:
                        yield pending_row
                        pending_row = row
                else:
                    pending_row = row

        if pending_row:
            yield pending_row

    def get_filename(self):
        if self.is_multievent:
            return '{}_orders'.format(self.events.first().organizer.slug)
        else:
            return '{}_orders'.format(self.event.slug)

