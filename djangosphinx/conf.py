#coding: utf-8

__author__ = 'ego'

from django.conf import settings
from djangosphinx.constants import SNIPPETS_OPTIONS, QUERY_OPTIONS

__all__ = [
    'DOCUMENT_ID_SHIFT', 'CONTENT_TYPE_MASK', 'OBJECT_ID_MASK',
    'SEARCHD_SETTINGS',
    'SPHINX_MAX_MATCHES',
    'SPHINX_QUERY_OPTS', 'SPHINX_QUERY_LIMIT',
    'SPHINX_SNIPPETS', 'SPHINX_SNIPPETS_OPTS',
    'SPHINX_CELERY_PING', 'SPHINX_CELERY_PING_TIMEOUT',
]

DOCUMENT_ID_SHIFT = getattr(settings, 'SPHINX_DOCUMENT_ID_SHIFT', 52)
CONTENT_TYPE_MASK = (2 ** (64 - DOCUMENT_ID_SHIFT) - 1) << DOCUMENT_ID_SHIFT  # 4095 content types
OBJECT_ID_MASK = 2 ** DOCUMENT_ID_SHIFT - 1  # 4503599627370495 objects for content type

SPHINX_MAX_MATCHES = int(getattr(settings, 'SPHINX_MAX_MATCHES', 1000))

SEARCHD_SETTINGS = {
    'log_path': getattr(settings, 'SPHINX_LOG_PATH', '/var/log/sphinx/').rstrip('/'),
    'data_path': getattr(settings, 'SPHINX_DATA_PATH', '/var/data/sphinx/').rstrip('/'),
    'pid_file': getattr(settings, 'SPHINX_PID_FILE', '/var/run/searchd.pid'),
    'sphinx_host': getattr(settings, 'SPHINX_HOST', '127.0.0.1'),
    'sphinx_port': getattr(settings, 'SPHINX_PORT', 9306),
    'max_matches': SPHINX_MAX_MATCHES,
}

SPHINX_SNIPPETS = bool(getattr(settings, 'SPHINX_SNIPPETS', False))

_snip_opts = getattr(settings, 'SPHINX_SNIPPETS_OPTIONS', {})

SPHINX_SNIPPETS_OPTS = {}
for k, v in _snip_opts.iteritems():
    assert(isinstance(v, SNIPPETS_OPTIONS[k]))

    if isinstance(v, bool):
        v = int(v)

    SPHINX_SNIPPETS_OPTS[k] = v

#if 'html_strip_mode' not in SPHINX_SNIPPETS_OPTS:
#    SPHINX_SNIPPETS_OPTS['html_strip_mode'] = 'strip'

_query_opts = getattr(settings, 'SPHINX_QUERY_OPTIONS', {})
SPHINX_QUERY_OPTS = {}
for k, v in _query_opts.iteritems():
    assert(isinstance(v, QUERY_OPTIONS[k]))

    if isinstance(v, bool):
        v = int(v)

    SPHINX_QUERY_OPTS[k] = v

SPHINX_QUERY_LIMIT = getattr(settings, 'SPHINX_QUERY_LIMIT', 20)

assert(SPHINX_QUERY_LIMIT < SPHINX_MAX_MATCHES)

# использовать Celery для пинга SphinxQL-сервера, если Celery доступен
SPHINX_CELERY_PING=getattr(settings, 'SPHINX_CELERY_PING', True)

# таймаут пинга в минутах
_timeout = int(getattr(settings, 'SPHINX_CELERY_PING_TIMEOUT', 2))
SPHINX_CELERY_PING_TIMEOUT='*/%i' % _timeout