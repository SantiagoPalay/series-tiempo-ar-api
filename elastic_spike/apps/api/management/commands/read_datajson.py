#! coding: utf-8
import requests
from django.core.management import BaseCommand
from pydatajson import DataJson

from elastic_spike.apps.api.query.catalog_reader import ReaderPipeline


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('catalog')
        parser.add_argument('--index', action='store_true')

    def handle(self, *args, **options):
        catalog_url = options['catalog']
        index_only = options.get('index')

        catalog = DataJson(catalog_url)

        ReaderPipeline(catalog, index_only)
