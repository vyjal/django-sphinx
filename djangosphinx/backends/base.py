#coding: utf-8

__author__ = 'ego'

# coding: utf-8

import re
import time

from datetime import datetime, date

try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal  # for Python 2.3

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.query import QuerySet

from django.utils.encoding import force_unicode

from djangosphinx.conf import *
from djangosphinx.constants import PASSAGES_OPTIONS, UNDEFINED, EMPTY_RESULT_SET
from djangosphinx.utils.config import get_sphinx_attr_type_for_field


__all__ = ['SearchError', 'ConnectionError', 'BaseSphinxQuerySet', 'SphinxProxy',
           'to_sphinx']

def to_sphinx(value):
   "Convert a value into a sphinx query value"
   if isinstance(value, date) or isinstance(value, datetime):
       return int(time.mktime(value.timetuple()))
   elif isinstance(value, decimal.Decimal) or isinstance(value, float):
       return float(value)
   return int(value)


class SearchError(Exception):
    pass


class ConnectionError(Exception):
    pass


class BaseSphinxQuerySet(object):

    __index_match = re.compile(r'[^a-z0-9_-]*', re.I)

    def __init__(self, model=None, using=None, **kwargs):
        self.model = model
        self.using = using

        self._iter = None

        self._query = None
        self._query_args = None

        self._field_names = {}
        self._fields = '*'
        self._aliases = {}
        self._group_by = ''
        self._order_by = ''
        self._group_order_by = ''

        self._filters = {}
        self._excludes = {}

        self._query_opts = None

        self._limit = 20
        self._offset = 0

        self._query_string = ''
        self._result_cache = None
        self._fields_cache = {}
        self._metadata = None

        self._maxmatches = SPHINX_MAX_MATCHES

        self._passages = SPHINX_PASSAGES
        self._passages_opts = {}
        self._passages_string = {}

        if model:
            self._indexes = self._parse_indexes(kwargs.pop('index', model._meta.db_table))
        else:
            self._indexes = self._parse_indexes(kwargs.pop('index', None))

        self._index = self.index

    def __len__(self):
        return self.count()

    def __iter__(self):
        if self._iter is None:
            self._get_data()

        return iter(self._result_cache)

    def __repr__(self):
        return repr(self.__iter__())

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice, int, long)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))),\
        "Negative indexing is not supported."

        # no cache now
        if self._result_cache is not None:
            if self._iter is not None:
                # The result cache has only been partially populated, so we may
                # need to fill it out a bit more.
                if isinstance(k, slice):
                    if k.stop is not None:
                        # Some people insist on passing in strings here.
                        bound = int(k.stop)
                    else:
                        bound = None
                else:
                    bound = k + 1
                if len(self._result_cache) < bound:
                    self._fill_cache(bound - len(self._result_cache))
            return self._result_cache[k]

        if isinstance(k, slice):
            qs = self._clone()
            if k.start is not None:
                start = int(k.start)
            else:
                start = None
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None
            qs.set_limits(start, stop)
            qs._fill_cache()
            return k.step and list(qs)[::k.step] or qs

        try:
            qs = self._clone()
            qs.set_limits(k, k + 1)
            qs._fill_cache()
            return list(qs)[0]
        except Exception, e:
            raise IndexError(e.args)

    def next(self):
        raise NotImplementedError

    # indexes

    def add_index(self, index):
        _indexes = self._indexes[:]

        for x in self._parse_indexes(index):
            if x not in _indexes:
                _indexes.append(x)

        return self._clone(_indexes=_indexes)

    def remove_index(self, index):
        _indexes = self._indexes[:]

        for x in self._parse_indexes(index):
            if x in _indexes:
                _indexes.pop(_indexes.index(x))

        return self._clone(_indexes=_indexes)

    def _get_index(self):
        return ' '.join(self._indexes)

    index = property(_get_index)

    # querying

    def query(self, query):
        return self._clone(_query=force_unicode(query))

    def filter(self, **kwargs):
        raise NotImplementedError

    def exclude(self, **kwargs):
        raise NotImplementedError

    def count(self):
        return min(self.meta.get('total_found', 0), self._maxmatches)

    def all(self):
       return self

    def none(self):
       qs = EmptySphinxQuerySet()
       qs.__dict__.update(self.__dict__.copy())
       return qs


    # other
    def reset(self):
           return self.__class__(self.model, self.using, index=' '.join(self._indexes))

    def _meta(self):
       if self._metadata is None:
           self._get_data()

       return self._metadata

    meta = property(_meta)

    def get_query_set(self, model):
        qs = model._default_manager
        if self.using is not None:
            qs = qs.db_manager(self.using)
        return qs.all()

    def escape(self, value):
        return re.sub(r"([=\(\)|\-!@~\"&/\\\^\$\=])", r"\\\1", value)



    def set_passages(self, enable=True, **kwargs):
        self._passages = enable

        for k, v in kwargs.iteritems():
            if k in PASSAGES_OPTIONS:
                assert(isinstance(v, PASSAGES_OPTIONS[k]))

                if isinstance(v, bool):
                    v = int(v)

                self._passages_opts[k] = v

        self._passages_string = None

    def _build_passages_string(self):
        opts_list = []
        for k, v in self._passages_opts.iteritems():
            opts_list.append("'%s' AS `%s`" % (self.escape(v), k))

        if opts_list:
            self._passages_string = ', %s' % ', '.join(opts_list)

    def _get_passages_string(self):
        if self._passages_string is None:
            self._build_passages_string()
        return self._passages_string

    passages = property(_get_passages_string)


    def set_options(self, **kwargs):
        kwargs = self._format_options(**kwargs)
        if kwargs is not None:
            return self._clone(**kwargs)
        return self


    def set_limits(self, start=None, stop=None):
        if start is not None:
            self._offset = int(start)
        if stop is not None:
            self._limit = stop - start

        self._query_string = None

    #internal
    def _format_options(self, **kwargs):
        raise NotImplementedError

    def _get_data(self):
        raise NotImplementedError

    def _clone(self, *args, **kwargs):
        raise NotImplementedError

    # internal
    def _fill_cache(self):
        raise NotImplementedError

    def _format_cache(self, docs, results, ct):
        if self.model is None and len(self._indexes) == 1 and ct is not None:
            self.model = ContentType.objects.get(pk=ct).model_class()

        if self.model:
            qs = self.get_query_set(self.model)

            qs = qs.filter(pk__in=results[ct].keys())

            for obj in qs:
                results[ct][obj.pk]['obj'] = obj

        else:
            for ct in results:
                model_class = ContentType.objects.get(pk=ct).model_class()
                qs = self.get_query_set(model_class).filter(pk__in=results[ct].keys())

                for obj in qs:
                    results[ct][obj.pk]['obj'] = obj

        if self._passages:
            for doc in docs.values():
                doc['data']['passages'] = self._get_passages(doc['results']['obj'])
                self._result_cache.append(SphinxProxy(doc['results']['obj'], doc['data']))
        else:
            for doc in docs.values():
                self._result_cache.append(SphinxProxy(doc['results']['obj'], doc['data']))

    def _get_passages(self, instance):
        raise NotImplementedError

    def _parse_indexes(self, index):

        if index is None:
            return list()

        return [x.lower() for x in re.split(self.__index_match, index) if x]

    def _decode_document_id(self, doc_id):
        assert isinstance(doc_id, int)

        ct = (doc_id & 0xFF000000) >> DOCUMENT_ID_SHIFT
        return doc_id & 0x00FFFFFF, ct

    def _process_single_obj_operation(self, obj):
        if isinstance(obj, models.Model):
            if self.model is None:
                raise ValueError('For non model or multiple model indexes comparsion with objects not supported')
            value = obj.pk
        elif not isinstance(obj, (list, tuple, QuerySet)):
            value = obj
        else:
            raise TypeError('Comparison operations require a single object, not a `%s`' % type(obj))

        return to_sphinx(value)

    def _process_obj_list_operation(self, obj_list):
        if isinstance(obj_list, (models.Model, QuerySet)):
            if self.model is None:
                raise ValueError('For non model or multiple model indexes comparsion with objects not supported')

            if isinstance(obj_list, models.Model):
                values = [obj_list.pk]
            else:
                values = [obj.pk for obj in obj_list]

        elif hasattr(obj_list, '__iter__') or isinstance(obj_list, (list, tuple)):
            values = list(obj_list)
        elif isinstance(obj_list, (int, float, date, datetime)):
            values = [obj_list]
        else:
            raise ValueError('`%s` is not a list of objects and not single object' % type(obj_list))

        return map(to_sphinx, values)

    def _get_doc_fields(self, instance):
        cache = self._fields_cache.get(type(instance), None)
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


class EmptySphinxQuerySet(BaseSphinxQuerySet):
    def _get_data(self):
        self._iter = iter([])
        self._result_cache = []
        self._metadata = EMPTY_RESULT_SET

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
