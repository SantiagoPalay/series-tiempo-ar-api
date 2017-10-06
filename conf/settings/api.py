#! coding: utf-8

ES_URL = "http://localhost:9200/"

# JSON del mapping de series de tiempo
MAPPING = {
  "properties": {
    "timestamp":                    {"type": "date"},
    "value":                        {"type": "scaled_float", "scaling_factor": 10000000},
    "change":                       {"type": "scaled_float", "scaling_factor": 10000000},
    "percent_change":               {"type": "scaled_float", "scaling_factor": 10000000},
    "change_a_year_ago":            {"type": "scaled_float", "scaling_factor": 10000000},
    "percent_change_a_year_ago":    {"type": "scaled_float", "scaling_factor": 10000000},
    "series_id":                    {"type": "keyword"}
  },
  "_all": {"enabled": False},
  "dynamic": "strict"
}

# Único índice asignado a las series de tiempo
TS_INDEX = 'indicators'

# Único tipo asignado a las series de tiempo
TS_DOC_TYPE = "doc"

INDEX_CREATION_BODY = {
    'mappings': {
        TS_DOC_TYPE: MAPPING
    }
}

# Actualización de datos en segundos
TS_REFRESH_INTERVAL = "30s"


# Nombre de la columna de índice de tiempo en las distribuciones
INDEX_COLUMN = 'indice_tiempo'

# Modos de representación de las series, calculados y guardados
# en el proceso de indexación
REP_MODES = [
    'value',
    'change',
    'change_a_year_ago',
    'percent_change',
    'percent_change_a_year_ago'
]

API_DEFAULT_VALUES = {
    'rep_mode': 'value',
    'collapse_aggregation': 'avg',
    'collapse': 'year',
    'start': 0,
    'limit': 100
}
