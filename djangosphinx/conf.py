#coding: utf-8

__author__ = 'ego'

from django.conf import settings
from djangosphinx.constants import SNIPPETS_OPTIONS

__all__ = [
    'DOCUMENT_ID_SHIFT',
    'SEARCHD_SETTINGS',
    'SPHINX_RETRIES', 'SPHINX_RETRIES_DELAY',
    'SPHINX_MAX_MATCHES',
    'SPHINX_SNIPPETS', 'SPHINX_SNIPPETS_OPTS'
]

DOCUMENT_ID_SHIFT = 24

SPHINX_MAX_MATCHES = int(getattr(settings, 'SPHINX_MAX_MATCHES', 1000))

SEARCHD_SETTINGS = {
    'log_path': getattr(settings, 'SPHINX_LOG_PATH', '/var/log/sphinx/').rstrip('/'),
    'data_path': getattr(settings, 'SPHINX_DATA_PATH', '/var/data/').rstrip('/'),
    'pid_file': getattr(settings, 'SPHINX_PID_FILE', '/var/run/searchd.pid'),
    'sphinx_host': getattr(settings, 'SPHINX_HOST', '127.0.0.1'),
    'sphinx_port': getattr(settings, 'SPHINX_PORT', 9306),
    'max_matches': SPHINX_MAX_MATCHES,
}

# These require search API 275 (Sphinx 0.9.8)
SPHINX_RETRIES = int(getattr(settings, 'SPHINX_RETRIES', 0))
SPHINX_RETRIES_DELAY = int(getattr(settings, 'SPHINX_RETRIES_DELAY', 5))

SPHINX_SNIPPETS = bool(getattr(settings, 'SPHINX_SNIPPETS', False))

_snip_opts = getattr(settings, 'SPHINX_SNIPPETS_OPTIONS', {})

SPHINX_SNIPPETS_OPTS = {}
for k, v in _snip_opts.iteritems():
    assert(isinstance(v, SNIPPETS_OPTIONS[k]))

    if isinstance(v, bool):
        v = int(v)

    SPHINX_SNIPPETS_OPTS[k] = v
