from sphinxapi import sphinxapi

__all__ = ('SPHINX_API_VERSION',)

SPHINX_API_VERSION = getattr(sphinxapi, 'VER_COMMAND_SEARCH', None)