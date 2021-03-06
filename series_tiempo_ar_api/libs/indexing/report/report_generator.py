#!coding=utf8
from __future__ import unicode_literals
import datetime

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.mail.message import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from django_datajsonar.models import Catalog, Node
from series_tiempo_ar_api.apps.analytics.models import Query
from series_tiempo_ar_api.apps.management.models import Indicator
from series_tiempo_ar_api.libs.indexing.report import attachments
from series_tiempo_ar_api.libs.indexing.report.indicators_generator import IndicatorsGenerator


class ReportGenerator(object):
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    def __init__(self, task):
        self.task = task

    def generate(self):
        self.task.finished = timezone.now()
        self.task.status = self.task.FINISHED
        self.task.save()

        for node in Node.objects.filter(indexable=True):
            IndicatorsGenerator(node, self.task).generate()

        self.generate_email()

        ids = Catalog.objects.all().values_list('identifier')
        # Reportes de catálogo individual
        for node in Node.objects.filter(indexable=True, catalog_id__in=ids):
            self.generate_email(node=node)

    def generate_email(self, node=None):
        """Genera y manda el mail con el reporte de indexación. Si node es especificado, genera el reporte
        con valores de entidades pertenecientes únicamente a ese nodo (reporte individual). Caso contrario
        (default), genera el reporte de indexación global
        """

        context = {
            'finish_time': self._format_date(self.task.finished),
            'is_partial_report': bool(node),
            'queries': self.get_queries()
        }
        context.update({
            indicator: self._get_indicator_value(indicator, node=node)
            for indicator, _ in Indicator.TYPE_CHOICES
        })
        self.send_email(context, node)

    def send_email(self, context, node=None):
        if not node:
            recipients = Group.objects.get(name=settings.READ_DATAJSON_RECIPIENT_GROUP).user_set.all()
        else:
            recipients = node.admins.all()

        emails = [user.email for user in recipients]
        if not emails:  # Nothing to do here
            return
        start_time = self._format_date(self.task.created)
        subject = u'[{}] API Series de Tiempo: {}'.format(settings.ENV_TYPE, start_time)

        msg = render_to_string('indexing/report.txt', context=context)
        mail = EmailMultiAlternatives(subject, msg, settings.EMAIL_HOST_USER, emails)
        html_msg = render_to_string('indexing/report.html', context=context)
        mail.attach_alternative(html_msg, 'text/html')

        mail.attach('errors.log', self.task.logs, 'text/plain')
        mail.attach('catalogs.csv', attachments.generate_catalog_attachment(node=node), 'text/csv')
        mail.attach('datasets.csv', attachments.generate_dataset_attachment(node=node), 'text/csv')
        mail.attach('distributions.csv', attachments.generate_distribution_attachment(node=node), 'text/csv')
        mail.attach('series.csv', attachments.generate_field_attachment(node=node), 'text/csv')

        sent = mail.send()
        if emails and not sent:
            raise ValueError

    def _format_date(self, date):
        return timezone.localtime(date).strftime(self.DATE_FORMAT)

    def _get_indicator_value(self, indicator_type, node=None):
        """Devuelve el valor del indicador_type para el nodo node, o si no es especificado,
        la suma del valor de ese indicador en todos los nodos indexados
        """
        if not indicator_type:
            return 0

        if node:
            indicator_queryset = self.task.indicator_set.filter(type=indicator_type, node=node)
        else:
            indicator_queryset = self.task.indicator_set.filter(type=indicator_type)
        if not indicator_queryset:
            return 0

        return int(sum([indic.value for indic in indicator_queryset]))

    @staticmethod
    def get_queries():
        yesterday = datetime.date.today() - relativedelta(days=1)

        count = Query.objects.filter(timestamp__day=yesterday.day,
                                     timestamp__month=yesterday.month,
                                     timestamp__year=yesterday.year).count()

        return count
