#! coding: utf-8
from datetime import datetime

from django.conf import settings
from elasticsearch_dsl import Search, Q, A

from series_tiempo_ar_api.apps.api.helpers import extra_offset
from series_tiempo_ar_api.apps.api.query import constants
from series_tiempo_ar_api.apps.api.query.es_query.periods_between import periods_between


class Series(object):
    def __init__(self, index, series_id, rep_mode, periodicity, collapse_agg=None):
        self.index = index
        self.series_id = series_id
        self.rep_mode = rep_mode
        self.original_periodicity = periodicity
        self.periodicity = periodicity
        self.collapse_agg = collapse_agg or constants.API_DEFAULT_VALUES[constants.PARAM_COLLAPSE_AGG]
        self.search = self.init_search()

    def init_search(self):
        search = Search(index=self.index)

        search = search.sort(settings.TS_TIME_INDEX_FIELD)  # Default: ascending sort
        # Filtra los resultados por la serie pedida. Si se hace en memoria filtramos
        # por la agg default, y calculamos la agg pedida en runtime
        agg = self.collapse_agg if self.collapse_agg not in constants.IN_MEMORY_AGGS else constants.AGG_DEFAULT
        search = search.filter('bool',
                               must=[Q('match', series_id=self.series_id),
                                     Q('match', aggregation=agg)])

        return search

    def add_range_filter(self, start, end):
        _filter = {
            'lte': end,
            'gte': start
        }
        self.search = self.search.filter('range', timestamp=_filter)

    def add_collapse(self, periodicity):
        if self.collapse_agg not in constants.IN_MEMORY_AGGS:
            self.search = self.search.filter('bool', must=[Q('match', interval=periodicity)])

        elif periodicity != self.original_periodicity:
            # Agregamos la aggregation (?) para que se ejecute en ES en runtime
            self.search.aggs.bucket('test',
                                    A('date_histogram',
                                      field='timestamp',
                                      interval=periodicity,
                                      format='yyyy-MM-dd').
                                    metric('test', self.collapse_agg, field=self.rep_mode))
        else:  # Ignoramos la in memory ag
            self.collapse_agg = constants.AGG_DEFAULT
            self.search = self.search.filter('bool', must=[Q('match', interval=periodicity)])

        self.periodicity = periodicity

    def add_pagination(self, start, limit, request_start_dates=None):
        # ☢️☢️☢️
        es_start = self.get_es_start(request_start_dates, start)

        es_offset = start + limit
        if self.rep_mode != constants.API_DEFAULT_VALUES[constants.PARAM_REP_MODE]:
            es_offset += extra_offset(self.periodicity)

        self.search = self.search[es_start:es_offset]

    def get_es_start(self, request_start_dates, start):
        """Calcula el comienzo de la query para esta serie particular. El parámetro
        'start' pasado es el primer valor a devolver del resultado global, conformado por
        todas las series pedidas. Si una serie individual comienza en una fecha posterior al
        resultado global, el slicing de la búsqueda de ES con el parámetro start directo quitaría
        valores adicionales a los esperados. Debemos ajustar ese valor por la cantidad de períodos
        de diferencia entre el primer valor de la serie, y el comienzo del resultado (la menor
        fecha de todas las series pedidas)
        """
        min_date = min(request_start_dates.values()) if request_start_dates else None
        start_date = request_start_dates.get(self.series_id) if request_start_dates else None
        es_start = start - self.serie_first_date_offset(start_date,
                                                        min_date)
        es_start = max(es_start, 0)
        return es_start

    def serie_first_date_offset(self, series_start_date: datetime, min_start_date: datetime):
        if series_start_date is None or min_start_date is None:
            return 0

        return periods_between(series_start_date, min_start_date, self.periodicity)
