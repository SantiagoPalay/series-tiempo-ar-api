#! coding: utf-8
from django.core.management import BaseCommand

from series_tiempo_ar_api.libs.indexing.tasks import scrape


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('catalog')
        parser.add_argument('--async', action='store_true')

    def handle(self, *args, **options):
        catalog_url = options['catalog']
        run_async = options.get('async')

        if run_async:
            scrape.delay(catalog_url)
        else:
            scrape(catalog_url)
