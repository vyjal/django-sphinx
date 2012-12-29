# coding: utf-8

import time

import warnings
import operator

from sphinxapi import sphinxapi
import logging
import re
try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal  # for Python 2.3

from django.db import models
from django.db.models.fields.related import RelatedField
from django.db.models.query import Q, QuerySet
from django.conf import settings
from django.core.cache import cache

from djangosphinx.utils.config import get_sphinx_attr_type_for_field

__all__ = ('SearchError', 'ConnectionError', 'SphinxSearch', 'SphinxRelation', 'SphinxQuerySet')

from django.contrib.contenttypes.models import ContentType
from datetime import datetime, date

# server settings
SPHINX_SERVER           = getattr(settings, 'SPHINX_SERVER', 'localhost')
SPHINX_PORT             = int(getattr(settings, 'SPHINX_PORT', 3312))

# These require search API 275 (Sphinx 0.9.8)
SPHINX_RETRIES          = int(getattr(settings, 'SPHINX_RETRIES', 0))
SPHINX_RETRIES_DELAY    = int(getattr(settings, 'SPHINX_RETRIES_DELAY', 5))

MAX_INT = int(2 ** 31 - 1)
MAX_FLOAT = 1.1e+38 # this is almost max, that fits in struct.pack 'f'

EMPTY_RESULT_SET = dict(
    matches=[],
    total=0,
    total_found=0,
    words=[],
    attrs=[],
)

UNDEFINED = object()


class SearchError(Exception):
    pass


class ConnectionError(Exception):
    pass


class SphinxProxy(object):
    """
    Acts exactly like a normal instance of an object except that
    it will handle any special sphinx attributes in a `_sphinx` class.

    If there is no `sphinx` attribute on the instance, it will also
    add a proxy wrapper to `_sphinx` under that name as well.
    """
    __slots__ = ('__dict__', '__instance__', '_sphinx', 'sphinx')

    def __init__(self, instance, attributes):
        object.__setattr__(self, '__instance__', instance)
        object.__setattr__(self, '_sphinx', attributes)

    def _get_current_object(self):
        """
        Return the current object.  This is useful if you want the real object
        behind the proxy at a time for performance reasons or because you want
        to pass the object into a different context.
        """
        return self.__instance__
    _current_object = property(_get_current_object)

    def __dict__(self):
        try:
            return self._current_object.__dict__
        except RuntimeError:
            return AttributeError('__dict__')
    __dict__ = property(__dict__)

    def __repr__(self):
        try:
            obj = self._current_object
        except RuntimeError:
            return '<%s unbound>' % self.__class__.__name__
        return repr(obj)

    def __nonzero__(self):
        try:
            return bool(self._current_object)
        except RuntimeError:
            return False

    def __unicode__(self):
        try:
            return unicode(self._current_object)
        except RuntimeError:
            return repr(self)

    def __dir__(self):
        try:
            return dir(self._current_object)
        except RuntimeError:
            return []

    # def __getattribute__(self, name):
    #     if not hasattr(self._current_object, 'sphinx') and name == 'sphinx':
    #         name = '_sphinx'
    #     if name == '_sphinx':
    #         return object.__getattribute__(self, name)
    #     print object.__getattribute__(self, '_current_object')
    #     return getattr(object.__getattribute__(self, '_current_object'), name)

    def __getattr__(self, name, value=UNDEFINED):
        if not hasattr(self._current_object, 'sphinx') and name == 'sphinx':
            name = '_sphinx'
        if name == '_sphinx':
            return getattr(self, '_sphinx', value)
        if value == UNDEFINED:
            return getattr(self._current_object, name)
        return getattr(self._current_object, name, value)

    def __setattr__(self, name, value):
        if name == '_sphinx':
            return object.__setattr__(self, '_sphinx', value)
        elif name == 'sphinx':
            if not hasattr(self._current_object, 'sphinx'):
                return object.__setattr__(self, '_sphinx', value)
        return setattr(self._current_object, name, value)

    def __setitem__(self, key, value):
        self._current_object[key] = value

    def __delitem__(self, key):
        del self._current_object[key]

    def __setslice__(self, i, j, seq):
        self._current_object[i:j] = seq

    def __delslice__(self, i, j):
        del self._current_object[i:j]

    __delattr__ = lambda x, n: delattr(x._current_object, n)
    __str__ = lambda x: str(x._current_object)
    __unicode__ = lambda x: unicode(x._current_object)
    __lt__ = lambda x, o: x._current_object < o
    __le__ = lambda x, o: x._current_object <= o
    __eq__ = lambda x, o: x._current_object == o
    __ne__ = lambda x, o: x._current_object != o
    __gt__ = lambda x, o: x._current_object > o
    __ge__ = lambda x, o: x._current_object >= o
    __cmp__ = lambda x, o: cmp(x._current_object, o)
    __hash__ = lambda x: hash(x._current_object)
    # attributes are currently not callable
    # __call__ = lambda x, *a, **kw: x._current_object(*a, **kw)
    __len__ = lambda x: len(x._current_object)
    __getitem__ = lambda x, i: x._current_object[i]
    __iter__ = lambda x: iter(x._current_object)
    __contains__ = lambda x, i: i in x._current_object
    __getslice__ = lambda x, i, j: x._current_object[i:j]
    __add__ = lambda x, o: x._current_object + o
    __sub__ = lambda x, o: x._current_object - o
    __mul__ = lambda x, o: x._current_object * o
    __floordiv__ = lambda x, o: x._current_object // o
    __mod__ = lambda x, o: x._current_object % o
    __divmod__ = lambda x, o: x._current_object.__divmod__(o)
    __pow__ = lambda x, o: x._current_object ** o
    __lshift__ = lambda x, o: x._current_object << o
    __rshift__ = lambda x, o: x._current_object >> o
    __and__ = lambda x, o: x._current_object & o
    __xor__ = lambda x, o: x._current_object ^ o
    __or__ = lambda x, o: x._current_object | o
    __div__ = lambda x, o: x._current_object.__div__(o)
    __truediv__ = lambda x, o: x._current_object.__truediv__(o)
    __neg__ = lambda x: -(x._current_object)
    __pos__ = lambda x: +(x._current_object)
    __abs__ = lambda x: abs(x._current_object)
    __invert__ = lambda x: ~(x._current_object)
    __complex__ = lambda x: complex(x._current_object)
    __int__ = lambda x: int(x._current_object)
    __long__ = lambda x: long(x._current_object)
    __float__ = lambda x: float(x._current_object)
    __oct__ = lambda x: oct(x._current_object)
    __hex__ = lambda x: hex(x._current_object)
    __index__ = lambda x: x._current_object.__index__()
    __coerce__ = lambda x, o: x.__coerce__(x, o)
    __enter__ = lambda x: x.__enter__()
    __exit__ = lambda x, *a, **kw: x.__exit__(*a, **kw)


def to_sphinx(value):
    "Convert a value into a sphinx query value"
    if isinstance(value, date) or isinstance(value, datetime):
        return int(time.mktime(value.timetuple()))
    elif isinstance(value, decimal.Decimal) or isinstance(value, float):
        return float(value)
    return int(value)

FILTER_LIST_OPERATIONS = ['in', 'range']
FILTER_CMP_OPERATIONS = ['exact', 'iexact', 'gt', 'lt', 'gte', 'lte']


class SphinxQuerySet(object):
    available_kwargs = ('rankmode', 'mode', 'weights', 'maxmatches', 'passages', 'passages_opts')

    def __init__(self, model=None, using=None, **kwargs):
        self._select_related        = False
        self._select_related_args   = {}
        self._select_related_fields = []
        self._filters               = {}
        self._extra                 = {}
        self._query                 = ''
        self.__metadata             = None
        self._offset                = 0
        self._limit                 = 20

        self._groupby               = None
        self._sort                  = None
        self._weights               = [1, 100]

        self._passages              = False
        self._passages_opts         = {}
        self._maxmatches            = 1000
        self._result_cache          = None
        self._fields_cache          = {}
        self._mode                  = sphinxapi.SPH_MATCH_ANY
        self._rankmode              = getattr(sphinxapi, 'SPH_RANK_PROXIMITY_BM25', None)
        self.model                  = model
        self._anchor                = {}
        self.__metadata             = {}
        self.results_cts            = []

        self.using                  = using

        options = self._format_options(**kwargs)
        for key, value in options.iteritems():
            setattr(self, key, value)

        if model:
            self._index             = kwargs.get('index', model._meta.db_table)
        else:
            self._index             = kwargs.get('index')

    def __repr__(self):
        if self._result_cache is not None:
            return repr(self._get_data())
        else:
            return '<%s instance>' % (self.__class__.__name__,)

    def __len__(self):
        return self.count()

    def __iter__(self):
        return iter(self._get_data())

    def __getitem__(self, k):
        if not isinstance(k, (slice, int, long)):
            raise TypeError
        assert (not isinstance(k, slice) and (k >= 0)) \
            or (isinstance(k, slice) and (k.start is None or k.start >= 0) and (k.stop is None or k.stop >= 0)), \
            "Negative indexing is not supported."

        if self._result_cache is not None:
            # Check to see if this is a portion of an already existing result cache
            if type(k) == slice:
                start = k.start
                if start < self._offset or k.stop > self._limit:
                    self._result_cache = None
                else:
                    return self._get_data()[k.start: k.stop]
            else:
                if k not in range(self._offset, self._limit + self._offset):
                    self._result_cache = None
                else:
                    return self._get_data()[k - self._offset]

        if type(k) == slice:
            self._offset = k.start if k.start is not None else 0
            try:
                self._limit = k.stop - k.start
            except TypeError:
                self._limit = k.stop if k.stop else self._maxmatches - self._offset

            if not self._offset and self._limit == self._maxmatches:
                return self._get_data()

            return self._get_data(False)
        else:
            return self._get_data(False)[k]

    def _format_options(self, **kwargs):
        # перезаписываем rankmode и mode только если не установлены или заданы явно
        if self._rankmode is None or 'rankmode' in kwargs:
            kwargs['rankmode'] = getattr(sphinxapi,
                                        kwargs.get('rankmode', getattr(settings,  'SPH_RANK_NONE', None)),
                                        sphinxapi.SPH_RANK_NONE)

        if self._mode is None or 'mode' in kwargs:
            kwargs['mode'] = getattr(sphinxapi,
                                    kwargs.get('mode', getattr(settings, 'SPHINX_MATCH_MODE', None)),
                                    sphinxapi.SPH_MATCH_ANY)

        kwargs = dict([('_%s' % (key,), value) for key, value in kwargs.iteritems() if key in self.available_kwargs])
        return kwargs

    def get_query_set(self, model):
        qs = model._default_manager
        if self.using:
            qs = qs.db_manager(self.using)
        return qs.all()

    def set_options(self, **kwargs):
        kwargs = self._format_options(**kwargs)
        return self._clone(**kwargs)

    def query(self, string):
        return self._clone(_query=unicode(string).encode('utf-8'))

    def group_by(self, attribute, func, groupsort='@group desc'):
        return self._clone(_groupby=attribute, _groupfunc=func, _groupsort=groupsort)

    def rank_none(self):
        warnings.warn('`rank_none()` is deprecated. Use `set_options(rankmode=None)` instead.', DeprecationWarning)
        return self._clone(_rankmode=sphinxapi.SPH_RANK_NONE)

    def mode(self, mode):
        warnings.warn('`mode()` is deprecated. Use `set_options(mode='')` instead.', DeprecationWarning)
        return self._clone(_mode=mode)

    def weights(self, weights):
        warnings.warn('`mode()` is deprecated. Use `set_options(weights=[])` instead.', DeprecationWarning)
        return self._clone(_weights=weights)

    def on_index(self, index):
        warnings.warn('`mode()` is deprecated. Use `set_options(on_index=foo)` instead.', DeprecationWarning)
        return self._clone(_index=index)

    # only works on attributes
    def filter(self, **kwargs):
        filters = self._filters.copy()
        return self._clone(_filters=self._process_filter(filters, False, **kwargs))

    # only works on attributes
    def exclude(self, **kwargs):
        filters = self._filters.copy()
        return self._clone(_filters=self._process_filter(filters, True, **kwargs))


    def geoanchor(self, lat_attr, lng_attr, lat, lng):
        assert sphinxapi.VER_COMMAND_SEARCH >= 0x113, "You must upgrade sphinxapi to version 0.98 to use Geo Anchoring."
        return self._clone(_anchor=(lat_attr, lng_attr, float(lat), float(lng)))

    # this actually does nothing, its just a passthru to
    # keep things looking/working generally the same
    def all(self):
        return self

    def none(self):
        c = EmptySphinxQuerySet()
        c.__dict__.update(self.__dict__.copy())
        return c



    def escape(self, value):
        return re.sub(r"([=\(\)|\-!@~\"&/\\\^\$\=])", r"\\\1", value)

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

    # pass these thru on the queryset and let django handle it
    def select_related(self, *args, **kwargs):
        _args = self._select_related_fields[:]
        _args.extend(args)
        _kwargs = self._select_related_args.copy()
        _kwargs.update(kwargs)

        return self._clone(
            _select_related=True,
            _select_related_fields=_args,
            _select_related_args=_kwargs,
        )

    def extra(self, **kwargs):
        extra = self._extra.copy()
        extra.update(kwargs)
        return self._clone(_extra=extra)

    def count(self):
        return min(self._sphinx.get('total_found', 0), self._maxmatches)

    def reset(self):
        return self.__class__(self.model, self._index)

    # Internal methods
    def _get_sphinx_client(self):
        client = sphinxapi.SphinxClient()
        client.SetServer(SPHINX_SERVER, SPHINX_PORT)
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

    def _sphinx(self):
        if not self.__metadata:
            # We have to force execution if this is accessed beforehand
            self._get_data()
        return self.__metadata
    _sphinx = property(_sphinx)

    def _get_data(self, need_cache=True):
        assert(self._index)
        # need to find a way to make this work yet
        if need_cache:
            if self._result_cache is None:
                self._result_cache = self._get_results()
        else:
            return self._get_results()

        return self._result_cache

    def _get_sphinx_results(self):
        """\
        Всегда возвращает RESULT_SET\
        """
        assert(self._offset + self._limit <= self._maxmatches)

        if not self._limit > 0:
            # Fix for Sphinx throwing an assertion error when you pass it an empty limiter
            return EMPTY_RESULT_SET

        client = self._get_sphinx_client()

        params = []

        if self._sort:
            params.append('sort=%s' % (self._sort,))
            client.SetSortMode(*self._sort)

        if isinstance(self._weights, dict):
            client.SetFieldWeights(self._weights)
        else:
            # assume its a list
            client.SetWeights(map(int, self._weights))
        params.append('weights=%s' % (self._weights,))

        params.append('matchmode=%s' % (self._mode,))
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
            params.append('filters=%s' % (self._filters,))
            _handle_filters(self._filters)

        if self._groupby:
            params.append('groupby=%s' % (self._groupby,))
            client.SetGroupBy(self._groupby, self._groupfunc, self._groupsort)

        if self._anchor:
            params.append('geoanchor=%s' % (self._anchor,))
            client.SetGeoAnchor(*self._anchor)

        if self._rankmode:
            params.append('rankmode=%s' % (self._rankmode,))
            client.SetRankingMode(self._rankmode)

        if sphinxapi.VER_COMMAND_SEARCH >= 0x113:
            client.SetRetries(SPHINX_RETRIES, SPHINX_RETRIES_DELAY)

        client.SetLimits(int(self._offset), int(self._limit), int(self._maxmatches))

        # To avoid modifying the Sphinx API, we solve unicode indexes here
        if isinstance(self._index, unicode):
            self._index = self._index.encode('utf-8')

        results = client.Query(self._query, self._index)

        # The Sphinx API doesn't raise exceptions

        if not results:
            if client.GetLastError():
                raise SearchError(client.GetLastError())
            elif client.GetLastWarning():
                raise SearchError(client.GetLastWarning())
            else:
                results = EMPTY_RESULT_SET
        elif not results['matches']:
            results = EMPTY_RESULT_SET

        # Decode the encoded document ids, and if a content type is found set the string
        # on the results list attributes (that likely got clobbered due to heterogenous index schema :\)
        for result in results['matches']:
            result = self._decode_document_id(result)

        #results['attrs'].append({'content_type': True})

        logging.debug('Found %s results for search query %s on %s with params: %s', results['total'], self._query, self._index, ', '.join(params))

        return results

    def _check_related_field(self, field_name, obj):
        field = self.model._meta.get_field(field_name)

        if not isinstance(field, RelatedField):
            raise AttributeError('An object can only be compared with Related field, not with `%s`' % type(field))

        related_model = field.rel.to

        if not isinstance(obj, related_model):
            raise TypeError('Field `%s` is not associated with the model `%s`' % (field.name, type(obj)))

        return field

    def _check_field(self, field_name):
        field = self.model._meta.get_field(field_name)

        if get_sphinx_attr_type_for_field(field) == 'string':
            raise TypeError('Can`t filter by string attribute `%s`' % type(field))

        return field

    def _process_single_obj_operation(self, field, obj):
        if isinstance(obj, models.Model):
            self._check_related_field(field, obj)
            value = obj.pk

        elif not isinstance(obj, (list, tuple, QuerySet)):
            self._check_field(field)
            value = obj
        else:
            raise TypeError('Comparison operations require a single object, not a list')

        return to_sphinx(value)

    def _process_obj_list_operation(self, field, obj_list):
        if isinstance(obj_list, QuerySet):
            self._check_related_field(field, obj_list[0])
            values = list(obj_list)
        elif hasattr(obj_list, '__iter__') or isinstance(obj_list, (list, tuple)):
            values = list(obj_list)
        else:
            raise TypeError('`%s` is not a list of objects' % type(obj_list))

        return map(to_sphinx, values)

    def _process_filter(self, filters, exclude, **kwargs):
        """
        Filter types:
            filter: SetFilter
            range: SetFilterRange
            id_range: SetIDRange
            float_range: SetFilterFloatRange

        """
        for k, v in kwargs.iteritems():
            parts = k.split('__')
            parts_len = len(parts)
            field = parts[0]
            lookup = parts[-1]



            if parts_len == 1:  # один
                v = self._process_single_obj_operation(parts[0], v)
            elif parts_len == 2: # один exact или список, или сравнение
                if lookup in FILTER_CMP_OPERATIONS:
                    v = self._process_single_obj_operation(field, v)
                elif lookup in FILTER_LIST_OPERATIONS:
                    v = self._process_obj_list_operation(field, v)
                else:
                    raise NotImplementedError('Related object and/or field lookup "%s" not supported' % lookup)
            else: # related
                raise NotImplementedError('Related model fields lookup not supported')

            # parse args
            if isinstance(v, list):
                if lookup == 'range':
                    if len(v) > 2:
                        raise ValueError('Range may consist of two values')
                    args = ('range', field, v[0], v[1], exclude)
                elif lookup in ['in', 'exact', 'iexact']:
                    args = ('filter', field, v, exclude)
                else:
                    raise NotImplementedError('Lookup "%s" is not supported' % lookup)
            else:
                args = []
                is_float = isinstance(v, float)
                _max = MAX_FLOAT if is_float else MAX_INT
                if lookup in ('gt', 'gte'):
                    if lookup == 'gt':
                        v += (1.0/MAX_INT) if is_float else 1
                    args = [field, v, _max, exclude]
                elif lookup in ('lt', 'lte'):
                    if lookup == 'lt':
                        v -= (1.0/MAX_INT) if is_float else 1
                    args = [field, _max, v, exclude]
                elif field == lookup:
                    args = ('filter', field, [v], exclude)
                else:
                    raise NotImplementedError('Lookup "%s" is not supported' % lookup)

                if is_float:
                    args.insert(0, 'float_range')
                elif not exclude and self.model and field == self.model._meta.pk.name:
                    raise NotImplementedError('Document id filtering is not supported yet')
                    #args = args[1:3]
                    #args.insert(0, 'id_range')

            filters.setdefault(k, []).extend(args)
        return filters

    def get(self, **kwargs):
        """Hack to support ModelAdmin"""
        queryset = self.model._default_manager
        if self._select_related:
            queryset = queryset.select_related(*self._select_related_fields, **self._select_related_args)
        if self._extra:
            queryset = queryset.extra(**self._extra)
        return queryset.get(**kwargs)

    def _decode_document_id(self, result):
        doc_id = int(result['id'])
        result_ct = (doc_id & 0xFF000000) >> 24
        result['attrs']['content_type'] = result_ct
        result['id'] = doc_id & 0x00FFFFFF

        return result

    def _get_results(self):
        results = self._get_sphinx_results()

        self.__metadata = {
            'total': results['total'],
            'total_found': results['total_found'],
            'words': results['words'],
        }

        if results == EMPTY_RESULT_SET:
            return []

        if results['matches'] and self._passages:
            # We need to do some initial work for passages
            # XXX: The passages implementation has a potential gotcha if your id
            # column is not actually your primary key
            words = ' '.join([w['word'] for w in results['words']])

        if self.model:
            if results['matches']:
                queryset = self.get_query_set(self.model)
                if self._select_related:
                    queryset = queryset.select_related(*self._select_related_fields, **self._select_related_args)
                if self._extra:
                    queryset = queryset.extra(**self._extra)

                # django-sphinx supports the compositepks branch
                # as well as custom id columns in your sphinx configuration
                # but all primary key columns still need to be present in the field list
                pks = getattr(self.model._meta, 'pks', [self.model._meta.pk])
                if pks[0].column in results['matches'][0]['attrs']:
                    # имеем составной индекс и часть ключей в списке атрибутов

                    # XXX: Sometimes attrs is empty and we cannot have custom primary key attributes
                    for r in results['matches']:
                        r['id'] = ', '.join([unicode(r['attrs'][p.column]) for p in pks])

                    # Join our Q objects to get a where clause which
                    # matches all primary keys, even across multiple columns
                    q = reduce(operator.or_, [reduce(operator.and_, [Q(**{p.name: r['attrs'][p.column]}) for p in pks]) for r in results['matches']])
                    queryset = queryset.filter(q)
                else:
                    for r in results['matches']:
                        # Decode the bitshifted document id into object id
                        r = self._decode_document_id(r)
                        r['id'] = unicode(r['id'])
                    queryset = queryset.filter(pk__in=[r['id'] for r in results['matches']])
                queryset = dict([(', '.join([unicode(getattr(o, p.attname)) for p in pks]), o) for o in queryset])

                if self._passages:
                    # TODO: clean this up
                    for r in results['matches']:
                        if r['id'] in queryset:
                            r['passages'] = self._get_passages(queryset[r['id']], words, results['fields'])

                results = [SphinxProxy(queryset[r['id']], r) for r in results['matches'] if r['id'] in queryset]
            else:
                results = []
        else:

            objects = {}
            for r in results['matches']:
                ct = r['attrs']['content_type']
                r['id'] = unicode(r['id'])
                objects.setdefault(ct, {})[r['id']] = None

            for ct in objects:
                model_class = ContentType.objects.get(pk=ct).model_class()

                pks = getattr(model_class._meta, 'pks', [model_class._meta.pk])
                if results['matches'][0]['attrs'].get(pks[0].column):
                    for r in results['matches']:
                        if r['attrs']['content_type'] == ct:
                            val = ', '.join([unicode(r['attrs'][p.column]) for p in pks])
                            objects[ct][r['id']] = r['id'] = val

                    q = reduce(operator.or_, [reduce(operator.and_, [Q(**{p.name: r['attrs'][p.column]}) for p in pks]) for r in results['matches'] if r['attrs']['content_type'] == ct])
                    queryset = self.get_query_set(model_class).filter(q)
                else:
                    queryset = self.get_query_set(model_class).filter(pk__in=[key for key in objects[ct]])

                for obj in queryset:
                    objects[ct][unicode(obj.pk)] = obj

            if self._passages:
                for r in results['matches']:
                    ct = r['attrs']['content_type']
                    if r['id'] in objects[ct]:
                        r['passages'] = self._get_passages(objects[ct][r['id']], words)

            results = [SphinxProxy(objects[r['attrs']['content_type']][r['id']], r) for r in results['matches'] if r['id'] in objects[r['attrs']['content_type']]]

        return results

    def _get_doc_fields(self, instance):
        cache =  self._fields_cache.get(type(instance), None)
        if cache is None:

            def _get_field(name):
                return instance._meta.get_field(name)

            opts = instance.__sphinx_options__
            included = opts.get('included_fields', [])
            excluded = opts.get('excluded_fields', [])
            stored_attrs = opts.get('stored_attributes', [])
            stored_fields = opts.get('stored_fields', [])
            if included:
                included = [f for f in included if
                                                    f not in excluded
                                                    and
                                                    get_sphinx_attr_type_for_field(_get_field(f)) == 'string']
                for f in stored_fields:
                    if get_sphinx_attr_type_for_field(_get_field(f)) == 'string':
                        included.append(f)
            else:
                included = [f.name for f in instance._meta.fields
                                    if
                                        f.name not in excluded
                                        and
                                        (f.name not in stored_attrs
                                             or
                                             f.name in stored_fields)
                                        and
                                        get_sphinx_attr_type_for_field(f) == 'string']

            cache = self._fields_cache[type(instance)] = included

        return cache

    def _get_passages(self, instance, words, fields=None):
        client = self._get_sphinx_client()

        if not fields:
            fields = self._get_doc_fields(instance)

        docs = [getattr(instance, f) for f in fields]

        if isinstance(self._passages_opts, dict):
            opts = self._passages_opts
        else:
            opts = {}
        if isinstance(self._index, unicode):
            self._index = self._index.encode('utf-8')
        passages_list = client.BuildExcerpts(docs, instance.__sphinx_indexes__[0], words, opts)

        # если список пуст или есть None, заполняем его значениями из полей модели
        if not passages_list:
            passages_list = docs

        return dict(zip(fields, passages_list))


class EmptySphinxQuerySet(SphinxQuerySet):
    def _get_sphinx_results(self):
        return EMPTY_RESULT_SET


class SphinxModelManager(object):
    def __init__(self, model, **kwargs):
        self.model = model
        self._index = kwargs.pop('index', model._meta.db_table)
        self._kwargs = kwargs

    def _get_query_set(self):
        return SphinxQuerySet(self.model, index=self._index, **self._kwargs)

    def get_index(self):
        return self._index

    def all(self):
        return self._get_query_set()

    def none(self):
        return self._get_query_set().none()

    def filter(self, **kwargs):
        return self._get_query_set().filter(**kwargs)

    def query(self, *args, **kwargs):
        return self._get_query_set().query(*args, **kwargs)

    def on_index(self, *args, **kwargs):
        return self._get_query_set().on_index(*args, **kwargs)

    def geoanchor(self, *args, **kwargs):
        return self._get_query_set().geoanchor(*args, **kwargs)


class SphinxInstanceManager(object):
    """Collection of tools useful for objects which are in a Sphinx index."""
    # TODO: deletion support
    def __init__(self, instance, index):
        self._instance = instance
        self._index = index

    def update(self, **kwargs):
        assert sphinxapi.VER_COMMAND_SEARCH >= 0x113, "You must upgrade sphinxapi to version 0.98 to use UpdateAttributes."
        sphinxapi.UpdateAttributes(self._index, kwargs.keys(), dict(self.instance.pk, map(to_sphinx, kwargs.values())))


class SphinxSearch(object):
    def __init__(self, index=None, using=None, **kwargs):
        # Metadata for things like excluded_fields, included_fields, etc
        try:
            self._options = kwargs.pop('options')
        except:
            self._options = None

        self._kwargs = kwargs
        self._sphinx = None
        self._index = index

        self.model = None
        self.using = using

    def __call__(self, index, **kwargs):
        warnings.warn('For non-model searches use a SphinxQuerySet instance.', DeprecationWarning)
        return SphinxQuerySet(index=index, using=self.using, **kwargs)

    def __get__(self, instance, model, **kwargs):
        if instance:
            return SphinxInstanceManager(instance, self._index)
        return self._sphinx

    def get_query_set(self):
        """Override this method to change the QuerySet used for config generation."""
        return self.model._default_manager.all()

    def contribute_to_class(self, model, name, **kwargs):
        if self._index is None:
            self._index = model._meta.db_table
        self._sphinx = SphinxModelManager(model, index=self._index, **self._kwargs)
        self.model = model

        if hasattr(model, '__sphinx_indexes__') or hasattr(model, '__sphinx_options__'):
            raise AttributeError('Only one instance of SphinxSearch can be present in the model: `%s.%s`' % (self.model._meta.app_label, self.model._meta.object_name))

        setattr(model, '__sphinx_indexes__', [self._index])
        setattr(model, '__sphinx_options__', self._options)

        setattr(model, name, self._sphinx)


class SphinxRelationProxy(SphinxProxy):
    def count(self):
        return min(self._sphinx['attrs']['@count'], self._maxmatches)


class SphinxRelation(SphinxSearch):
    """
    Adds "related model" support to django-sphinx --
    http://code.google.com/p/django-sphinx/
    http://www.sphinxsearch.com/

    Example --

    class MySearch(SphinxSearch):
        myrelatedobject = SphinxRelation(RelatedModel)
        anotherone = SphinxRelation(AnotherModel)
        ...

    class MyModel(models.Model):
        search = MySearch('index')

    """
    def __init__(self, model=None, attr=None, sort='@count desc', **kwargs):
        if model:
            self._related_model = model
            self._related_attr = attr or model.__name__.lower()
            self._related_sort = sort
        super(SphinxRelation, self).__init__(**kwargs)

    def __get__(self, instance, instance_model, **kwargs):
        self._mode = instance._mode
        self._rankmode = instance._rankmode
        self._index = instance._index
        self._query = instance._query
        self._filters = instance._filters
        self._excludes = instance._excludes
        self.model = self._related_model
        self._groupby = self._related_attr
        self._groupsort = self._related_sort
        self._groupfunc = sphinxapi.SPH_GROUPBY_ATTR
        return self

    def _get_results(self):
        results = self._get_sphinx_results()
        if not results or not results['matches']:
            # No matches so lets create a dummy result set
            results = EMPTY_RESULT_SET
        elif self.model:
            ids = []
            for r in results['matches']:
                value = r['attrs']['@groupby']
                if isinstance(value, (int, long)):
                    ids.append(value)
                else:
                    ids.extend()
            qs = self.get_query_set(self.model).filter(pk__in=set(ids))
            if self._select_related:
                qs = qs.select_related(*self._select_related_fields,
                                       **self._select_related_args)
            if self._extra:
                qs = qs.extra(**self._extra)
            queryset = dict([(o.id, o) for o in qs])
            results = [SphinxRelationProxy(queryset[k['attrs']['@groupby']], k) \
                        for k in results['matches'] \
                        if k['attrs']['@groupby'] in queryset]
        self.__metadata = {
            'total': results['total'],
            'total_found': results['total_found'],
            'words': results['words'],
        }
        self._result_cache = results
        return results

    def _sphinx(self):
        if not self.__metadata:
            # We have to force execution if this is accessed beforehand
            self._get_data()
        return self.__metadata
    _sphinx = property(_sphinx)
