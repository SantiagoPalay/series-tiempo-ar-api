#! coding: utf-8
from django.conf import settings
from elasticsearch_dsl import MultiSearch, Q

from series_tiempo_ar_api.apps.api.exceptions import QueryError
from series_tiempo_ar_api.apps.api.query import constants
from series_tiempo_ar_api.apps.api.query import strings
from series_tiempo_ar_api.apps.api.query.es_query.response_formatter import ResponseFormatter
from series_tiempo_ar_api.apps.api.query.es_query.series import Series
from series_tiempo_ar_api.libs.indexing.elastic import ElasticInstance


class ESQuery(object):
    """Representa una query de la API de series de tiempo, que termina
    devolviendo resultados de datos leídos de ElasticSearch"""

    def __init__(self, index):
        """
        args:
            index (str): Índice de Elasticsearch a ejecutar las queries.
        """
        self.index = index
        self.series = []
        self.elastic = ElasticInstance()
        self.data = []

        self.periodicity = None
        # Parámetros que deben ser guardados y accedidos varias veces
        self.args = {
            constants.PARAM_START: constants.API_DEFAULT_VALUES[constants.PARAM_START],
            constants.PARAM_LIMIT: constants.API_DEFAULT_VALUES[constants.PARAM_LIMIT],
            constants.PARAM_SORT: constants.API_DEFAULT_VALUES[constants.PARAM_SORT]
        }

    def add_series(self, series_id, rep_mode, periodicity,
                   collapse_agg=constants.API_DEFAULT_VALUES[constants.PARAM_COLLAPSE_AGG]):
        # Fix a casos en donde collapse agg no es avg pero los valores serían iguales a avg
        # Estos valores no son indexados! Entonces seteamos la aggregation a avg manualmente
        if periodicity == constants.COLLAPSE_INTERVALS[-1]:
            collapse_agg = constants.AGG_DEFAULT

        self._init_series(series_id, rep_mode, collapse_agg)
        self.periodicity = periodicity

    def get_series_ids(self):
        """Devuelve una lista de series cargadas"""
        return [serie.series_id for serie in self.series]

    def sort(self, how):
        """Ordena los resultados por ascendiente o descendiente"""
        if how == constants.SORT_ASCENDING:
            order = settings.TS_TIME_INDEX_FIELD

        elif how == constants.SORT_DESCENDING:
            order = '-' + settings.TS_TIME_INDEX_FIELD
        else:
            msg = strings.INVALID_SORT_PARAMETER.format(how)
            raise ValueError(msg)

        for serie in self.series:
            serie.search = serie.search.sort(order)

        # Guardo el parámetro, necesario en el evento de hacer un collapse
        self.args[constants.PARAM_SORT] = how

    def add_collapse(self, interval):
        self.periodicity = interval

    def _init_series(self, series_id, rep_mode, collapse_agg):
        self.series.append(Series(series_id=series_id,
                                  index=self.index,
                                  rep_mode=rep_mode,
                                  args=self.args,
                                  collapse_agg=collapse_agg))

    def add_pagination(self, start, limit):
        if not len(self.series):
            raise QueryError(strings.EMPTY_QUERY_ERROR)

        for serie in self.series:
            serie.search = serie.search[start:limit]

        # Guardo estos parámetros, necesarios en el evento de hacer un collapse
        self.args[constants.PARAM_START] = start
        self.args[constants.PARAM_LIMIT] = limit

    def add_filter(self, start=None, end=None):
        if not len(self.series):
            raise QueryError(strings.EMPTY_QUERY_ERROR)

        _filter = {
            'lte': end,
            'gte': start
        }
        for serie in self.series:
            # Agrega un filtro de rango temporal a la query de ES
            serie.search = serie.search.filter('range',
                                               timestamp=_filter)

    def get_data_start_end_dates(self):
        if not self.data:
            return {}

        return {
            constants.PARAM_START_DATE: self.data[0][0],
            constants.PARAM_END_DATE: self.data[-1][0]
        }

    def run(self):
        """Ejecuta la query de todas las series agregadas. Devuelve una
        'tabla' (lista de listas) con los resultados, siendo cada columna
        una serie.
        """
        if not self.series:
            raise QueryError(strings.EMPTY_QUERY_ERROR)

        multi_search = MultiSearch(index=self.index,
                                   doc_type=settings.TS_DOC_TYPE,
                                   using=self.elastic)

        for serie in self.series:
            search = serie.search
            search = search.filter('bool',
                                   must=[Q('match', interval=self.periodicity)])
            multi_search = multi_search.add(search)

        responses = multi_search.execute()
        formatter = ResponseFormatter(self.series, responses, self.args, self.periodicity)
        self.data = formatter.format_response()
        # Devuelvo hasta LIMIT values
        return self.data[:self.args[constants.PARAM_LIMIT]]
