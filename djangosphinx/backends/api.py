#coding: utf-8

__author__ = 'ego'

from collections import OrderedDict

from django.conf import settings

from sphinxapi import sphinxapi

from djangosphinx.conf import *
from djangosphinx.backends.base import BaseSphinxQuerySet, SearchError
from djangosphinx.constants import EMPTY_RESULT_SET, MAX_FLOAT, MAX_INT, FILTER_CMP_OPERATIONS, QUERY_RANKERS

__all__ = ['SphinxQuerySet']

_mode = getattr(settings, 'SPHINX_MATCH_MODE', 'SPH_MATCH_ANY')
SPHINX_MATCH_MODE = getattr(sphinxapi, _mode)

_ranker = getattr(settings, 'SPHINX_RANKER', 'matchany')
SPHINX_RANKER = getattr(sphinxapi, QUERY_RANKERS[_ranker])

class SphinxQuerySet(BaseSphinxQuerySet):
    available_kwargs = ('ranker', 'mode', 'weights', 'maxmatches')

    def __init__(self, model=None, using=None, **kwargs):
        super(SphinxQuerySet, self).__init__(model, using, **kwargs)

        self._filters = []

        self._groupby = None
        self._sort = None
        self._weights = [1, 100]

        self._mode = SPHINX_MATCH_MODE
        self._ranker = SPHINX_RANK_MODE

        self._anchor = {}


        options = self._format_options(**kwargs)
        if options is not None:
            for key, value in options.iteritems():
                setattr(self, key, value)

    def _format_options(self, **kwargs):
        opts = {}
        for k, v in kwargs.iteritems():
            if k not in self.available_kwargs:
                continue

            if k == 'ranker':
                if v in QUERY_RANKERS:
                    v = getattr(sphinxapi, QUERY_RANKERS[v])

            opts['_%s' % k] = v
        # перезаписываем rankmode и mode только если не установлены или заданы явно
        #if 'rankmode' in kwargs:
        #    kwargs['rankmode'] = getattr(sphinxapi, kwargs.get('rankmode'))
        #
        #if 'mode' in kwargs:
        #    kwargs['mode'] = getattr(sphinxapi, kwargs.get('mode'))

        #kwargs = dict([('_%s' % (key,), value) for key, value in kwargs.iteritems() if key in self.available_kwargs])
        return opts if opts else None

    def group_by(self, attribute, func, groupsort='@group desc'):
        return self._clone(_groupby=attribute, _groupfunc=func, _groupsort=groupsort)

    # only works on attributes
    def filter(self, **kwargs):
        filters = self._filters[:]
        return self._clone(_filters=self._process_filter(filters, False, **kwargs))

    # only works on attributes
    def exclude(self, **kwargs):
        filters = self._filters[:]
        return self._clone(_filters=self._process_filter(filters, True, **kwargs))

    def geoanchor(self, lat_attr, lng_attr, lat, lng):
        assert sphinxapi.VER_COMMAND_SEARCH >= 0x113, "You must upgrade sphinxapi to version 0.98 to use Geo Anchoring."
        return self._clone(_anchor=(lat_attr, lng_attr, float(lat), float(lng)))

    # you cannot order by @weight (it always orders in descending)
    # keywords are @id, @weight, @rank, and @relevance
    def order_by(self, *args, **kwargs):
        mode = kwargs.pop('mode', sphinxapi.SPH_SORT_EXTENDED)
        if mode == sphinxapi.SPH_SORT_EXTENDED:
            sort_by = []
            for arg in args:
                sort = 'ASC'
                if arg[0] == '-':
                    arg = arg[1:]
                    sort = 'DESC'
                if arg == 'id':
                    arg = '@id'
                sort_by.append('%s %s' % (arg, sort))
        else:
            sort_by = args
        if sort_by:
            return self._clone(_sort=(mode, ', '.join(sort_by)))
        return self

    # Internal methods
    def _get_sphinx_client(self):
        client = sphinxapi.SphinxClient()
        client.SetServer(SEARCHD_SETTINGS['sphinx_host'], SEARCHD_SETTINGS['sphinx_api_port'])
        return client

    def _clone(self, **kwargs):
        # Clones the queryset passing any changed args
        c = self.__class__()
        c.__dict__.update(self.__dict__.copy())
        for k, v in kwargs.iteritems():
            setattr(c, k, v)
            # почистим кеш в новом объекте, раз уж параметры запроса изменились
        c._result_cache = None
        return c


    def _get_data(self, need_cache=True):
        assert(self._indexes)

        self._iter = iter(self._get_sphinx_results())
        self._result_cache = []
        self._metadata = []
        self._fill_cache()

    def _fill_cache(self, num=None):
        ct = None
        results = {}

        docs = OrderedDict()

        if self._iter:
            try:
                while True:
                    #self._result_cache.append(self._iter.next())

                    doc = self._iter.next()
                    doc_id = doc['id']

                    obj_id, ct = self._decode_document_id(int(doc_id))

                    results.setdefault(ct, {})[obj_id] = {}

                    docs.setdefault(doc_id, {})['results'] = results[ct][obj_id]
                    docs[doc_id]['data'] = {
                        'fields': doc['attrs'],
                    }
                    docs[doc_id]['data']['fields']['weight'] = doc['weight']

            except StopIteration:
                self._iter = None

                self._format_cache(docs, results, ct)

    def _get_sphinx_results(self):
        """\
        Всегда возвращает RESULT_SET\
        """
        assert(self._offset + self._limit <= self._maxmatches)

        if not self._limit > 0:
            # Fix for Sphinx throwing an assertion error when you pass it an empty limiter
            self._metadata = EMPTY_RESULT_SET
            return iter([])

        client = self._get_sphinx_client()

        if self._sort:
            client.SetSortMode(*self._sort)

        if isinstance(self._weights, dict):
            client.SetFieldWeights(self._weights)
        else:
            # assume its a list
            client.SetWeights(map(int, self._weights))

        client.SetMatchMode(self._mode)

        def _handle_filters(filter_list):
            for args in filter_list:
                filter_type = args.pop(0)

                if filter_type == 'filter':
                    client.SetFilter(*args)
                elif filter_type == 'range':
                    client.SetFilterRange(*args)
                elif filter_type == 'float_range':
                    client.SetFilterFloatRange(*args)
                elif filter_type == 'id_range':
                    client.SetIDRange(*args)
                else:
                    raise ValueError('Unknown filter_type `%s`' % filter_type)

        # Include filters
        if self._filters:
            _handle_filters(self._filters)

        if self._groupby:
            client.SetGroupBy(self._groupby, self._groupfunc, self._groupsort)

        if self._anchor:
            client.SetGeoAnchor(*self._anchor)

        if self._ranker:
            client.SetRankingMode(self._ranker)

        if sphinxapi.VER_COMMAND_SEARCH >= 0x113:
            client.SetRetries(SPHINX_RETRIES, SPHINX_RETRIES_DELAY)

        client.SetLimits(int(self._offset), int(self._limit), int(self._maxmatches))

        # To avoid modifying the Sphinx API, we solve unicode indexes here
        index = self.index
        if isinstance(index, unicode):
            index = index.encode('utf-8')

        results = client.Query(self._query, index)

        # The Sphinx API doesn't raise exceptions

        if not results:
            if client.GetLastError():
                raise SearchError(client.GetLastError())
            elif client.GetLastWarning():
                raise SearchError(client.GetLastWarning())
            else:
                self._metadata = EMPTY_RESULT_SET
                return iter([])
        elif not results['matches']:
            self._metadata = EMPTY_RESULT_SET
            return iter([])


        return results['matches']

    def _process_filter(self, filters, exclude, **kwargs):
        """\
        Filter types        :   Sphinx Client functions

            filter          :   SetFilter
            range           :   SetFilterRange
            id_range        :   SetIDRange
            float_range     :   SetFilterFloatRange

        """
        for k, v in kwargs.iteritems():
            parts = k.split('__')
            parts_len = len(parts)
            field = parts[0]
            lookup = parts[-1]

            if parts_len == 1:  # один
                v = self._process_single_obj_operation(v)
            elif parts_len == 2: # один exact или список, или сравнение
                if lookup in FILTER_CMP_OPERATIONS:
                    v = self._process_single_obj_operation(v)
                elif lookup in ['in', 'range']:
                    v = self._process_obj_list_operation(v)
                else:
                    raise NotImplementedError('Related object and/or field lookup "%s" not supported' % lookup)
            else: # related
                raise NotImplementedError('Related model fields lookup not supported')

            # parse args
            if isinstance(v, list):
                if lookup == 'range':
                    if len(v) != 2:
                        raise ValueError('Range may consist of two values')
                    if isinstance(v[0], float):
                        args = ('float_range', field, v[0], v[1], exclude)
                    else:
                        args = ('range', field, v[0], v[1], exclude)

                elif lookup in ['in']:
                    if not len(v):
                        raise ValueError('Empty list for `%s` lookup' % lookup)
                    args = ('filter', field, v, exclude)
                else:
                    raise NotImplementedError('Lookup "%s" is not supported' % lookup)


            else:
                args = []
                is_float = isinstance(v, float)
                _max = MAX_FLOAT if is_float else MAX_INT
                if lookup in ('gt', 'gte'):
                    if lookup == 'gt':
                        v += (1.0 / MAX_FLOAT) if is_float else 1
                    args = [field, v, _max, exclude]
                elif lookup in ('lt', 'lte'):
                    if lookup == 'lt':
                        v -= (1.0 / MAX_FLOAT) if is_float else 1
                    args = [field, 0, v, exclude]
                elif (field == lookup) and isinstance(v, (int, float)):
                    args = ('filter', field, [v], exclude)
                else:
                    e = NotImplementedError
                    if field == lookup:
                        lookup = '='
                    if isinstance(v, float):
                        e = TypeError
                    raise e('Lookup "%s" is not supported for type `%s`' % (lookup, type(v)))

                if args[0] != 'filter':
                    if is_float:
                        args.insert(0, 'float_range')
                    else:
                        args.insert(0, 'range')
                        #elif self.model and (field == 'pk' or field == self.model._meta.pk.column):
                        #    raise NotImplementedError('Document id filtering is not supported yet')
                        #args = args[1:3]
                        #args.insert(0, 'id_range')

            filters.append(args)
        return filters

    def _get_passages(self, instance):
        client = self._get_sphinx_client()

        fields = self._get_doc_fields(instance)

        docs = [getattr(instance, f) for f in fields]

        if isinstance(self._passages_opts, dict):
            opts = self._passages_opts
        else:
            opts = {}

        passages_list = client.BuildExcerpts(docs, instance.__sphinx_indexes__[0], self._query, opts)

        # если список пуст или есть None, заполняем его значениями из полей модели
        if not passages_list:
            passages_list = docs

        return dict(zip(fields, passages_list))
