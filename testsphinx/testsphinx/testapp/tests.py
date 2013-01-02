# coding: utf-8
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import datetime
import time

from django.conf import settings
from django.db.models.query import QuerySet
from django.db.models.fields import FieldDoesNotExist
from django.test import TestCase

from django_any import any_model

from sphinxapi import sphinxapi
from djangosphinx.models import MAX_INT, MAX_FLOAT
from djangosphinx import models as ds

from models import *

dt = datetime.datetime.now()
d = datetime.date.today()
sphinx_dt = time.mktime(dt.timetuple())
sphinx_d = time.mktime(d.timetuple())

class TestFunctions(TestCase):

    def test_to_sphinx(self):
        from djangosphinx.models import to_sphinx, decimal

        # int
        self.assertEqual(1, to_sphinx(1))

        dt = datetime.datetime.now()
        d = datetime.date.today()

        # date and time
        self.assertEqual(time.mktime(dt.timetuple()), to_sphinx(dt))
        self.assertEqual(time.mktime(d.timetuple()), to_sphinx(d))

        # float
        self.assertEqual(1.0, to_sphinx(1.0))
        # decimal
        self.assertEqual(3.14, to_sphinx(decimal.Decimal(3.14)))

        for obj in [str(), unicode(), list(), tuple(), dict(), set()]:
            self.assertRaises(StandardError, to_sphinx, obj)


class TestEmptyQueryset(TestCase):

    def test_sphinx_results(self):
        qs = ds.EmptySphinxQuerySet()
        self.assertEqual(ds.EMPTY_RESULT_SET, qs._get_sphinx_results())


class TestSphinxQuerySet(TestCase):

    def test__format_options(self):
        qs = ds.SphinxQuerySet()

        valid = ('rankmode', 'mode', 'weights', 'maxmatches', 'passages', 'passages_opts')

        opts, kwargs = self._get_test_opts()

        self.assertEqual(opts, qs._format_options(**kwargs))

        self.assertRaises(AttributeError, qs._format_options, rankmode='BLAH')
        self.assertRaises(AttributeError, qs._format_options, mode='BLAH')

    def test_get_queryset(self):
        qs = Search.search.query('test')

        self.assertIsInstance(qs.get_query_set(qs.model), QuerySet)

        qs.using = 'test_testdb'
        mqs = qs.get_query_set(qs.model)

        self.assertEqual(qs.using, mqs._db)

    def test_set_options(self):
        qs = ds.SphinxQuerySet()

        opts, kwargs = self._get_test_opts()

        new_qs = qs.set_options(**kwargs)

        for opt, value in opts.iteritems():
            self.assertEqual(value, getattr(new_qs, opt))

    def test_query(self):
        qs = ds.SphinxQuerySet()
        qs._query = None
        query = 'query'
        new_qs = qs.query(query)

        self.assertEqual(query, new_qs._query)

    def test_group_by(self):
        qs = ds.SphinxQuerySet()

        qs._groupby = None
        qs._groupfunc = None
        qs._groupsort = None

        attrs = dict(_groupby='by',
            _groupfunc='func',
            _groupsort='sort')

        new_qs = qs.group_by('by', 'func', 'sort')

        for attr, value in attrs.iteritems():
            self.assertEqual(value, getattr(new_qs, attr))

    def test_filter_exclude(self):
        qs = Search.search.query('test')
        qs._filters = []

        qs1 = qs.filter(uint=1)


        self.assertEqual(('filter', 'uint', [1], False),
                        tuple(qs1._filters[0]))

        qs2 = qs.exclude(uint=1)

        self.assertEqual(('filter', 'uint', [1], True),
                        tuple(qs2._filters[0]))

    def test_geoanchor(self):
        qs = ds.SphinxQuerySet()

        qs._anchor = None

        _anchor = ('lat', 'lng', 1.0, 1.0)

        qs1 = qs.geoanchor('lat', 'lng', 1, 1)

        self.assertEqual(_anchor, qs1._anchor)

    def test_all_and_none_querysets(self):
        qs = Search.search.none()

        self.assertEqual([], list(qs))

        qs2 = qs.all()

        self.assertEqual(qs2, qs)

    def test_escape(self):
        self.fail('Test not implemented')

    def test_order_by(self):
        self.fail('Test not implemented')

    def test_select_related(self):
        self.fail('Test not implemented')

    def test_extra(self):
        qs = ds.SphinxQuerySet()
        qs._extra = dict()

        attrs = dict(test=True)

        qs1 = qs.extra(**attrs)

        self.assertEqual(attrs, qs1._extra)

    def test_count(self):
        qs = ds.SphinxQuerySet(index='test')

        _max = qs._maxmatches

        def _get_sphinx_results(*args):
            res = ds.EMPTY_RESULT_SET.copy()
            res.update(dict(total_found=20))
            return res

        qs._get_sphinx_results = _get_sphinx_results


        self.assertEqual(20, qs.count())

        qs = ds.SphinxQuerySet(index='test')

        def _get_sphinx_results1(*args):
            res = ds.EMPTY_RESULT_SET.copy()
            res.update(dict(total_found=_max+1))
            return res

        qs._get_sphinx_results = _get_sphinx_results1

        self.assertEqual(_max, qs.count())

    def test_reset(self):
        qs = ds.SphinxQuerySet()

        qs1 = qs.query('test')
        qs1 = qs1.extra(test='test')

        self.assertNotEqual(qs.__dict__, qs1.__dict__)

        qs2 = qs1.reset()

        self.assertDictEqual(qs2.__dict__, qs.__dict__)

    def test__get_sphinx_client(self):
        qs = ds.SphinxQuerySet()

        self.assertIsInstance(qs._get_sphinx_client(), sphinxapi.SphinxClient)

    def test__clone(self):
        qs = ds.SphinxQuerySet()

        qs1 = qs._clone()
        self.assertDictEqual(qs.__dict__, qs1.__dict__)
        self.assertNotEqual(qs, qs1)

        qs2 = qs._clone(_passages=not qs._passages)
        self.assertNotEqual(qs.__dict__, qs2.__dict__)

    def test__get_data(self):
        qs = ds.SphinxQuerySet()

        self.assertRaises(AssertionError, qs._get_data)

        qs = ds.SphinxQuerySet(index='test')

        def _get_results(*args):
            return dict(test='test')
        qs._get_results = _get_results

        self.assertIsNone(qs._result_cache)

        self.assertDictEqual(_get_results(), qs._get_data(False))
        self.assertIsNone(qs._result_cache)

        self.assertDictEqual(_get_results(), qs._get_data(True))
        self.assertDictEqual(_get_results(), qs._result_cache)

    def test__get_sphinx_results(self):
        qs = ds.SphinxQuerySet()
        qs = qs._clone(_offset=100, _limit=100, _maxmatches=100)

        self.assertRaises(AssertionError, qs._get_sphinx_results)

        qs = ds.SphinxQuerySet()
        qs = qs._clone(_limit = 0)

        self.assertDictEqual(ds.EMPTY_RESULT_SET, qs._get_sphinx_results())

        #TODO: дописать


    def test__chekc_field(self):
        self._prepare_models()

        qs = Search.search.query('test')

        int_field_name = 'uint'
        int_field = Search._meta.get_field(int_field_name)
        str_field = 'name'

        self.assertRaises(TypeError, qs._check_field, str_field)
        self.assertEqual(int_field, qs._check_field(int_field_name))

    def test__check_related_field(self):
        self._prepare_models()

        qs = Search.search.query('test')

        non_rel_field = Search._meta.get_field('name')
        fk_field = Search._meta.get_field('related')
        m2m_field = Search._meta.get_field('m2m')

        fk_obj = Related.objects.all()[0]
        m2m_obj = M2M.objects.all()[0]

        self.assertRaises(TypeError, qs._check_related_field, non_rel_field, None)

        self.assertRaises(TypeError, qs._check_related_field, fk_field, m2m_obj)
        self.assertRaises(TypeError, qs._check_related_field, m2m_field, fk_obj)

        self.assertEqual(fk_field, qs._check_related_field(fk_field, fk_obj))
        self.assertEqual(m2m_field, qs._check_related_field(m2m_field, m2m_obj))

    def test__process_single_obj_operation(self):
        self.fail('Test not implemented')

    def test__process_obj_list_operation(self):
        self.fail('Test not implemented')

    def test__process_filter(self):
        self._prepare_models()

        qs = Search.search.query('test')

        fk_obj = Related.objects.all()[0]
        fk_qs = Related.objects.all()
        m2m_qs = M2M.objects.all()

        # только числа и даты могут быть переданы в эту функцию (в том числе списками)

        # фильтровать можно только по нестроковым полям
        self.assertRaises(TypeError, qs._process_filter, [], False, name='string')
        # только по существующим полям модели
        #TODO: добавить проверку существования поля в индексе
        self.assertRaises(FieldDoesNotExist, qs._process_filter, [], False, some_field=1)
        # и не по строкам
        self.assertRaises(ValueError, qs._process_filter, [], False, uint='string')

        # если не указана операция, аргумент не может быть списком
        self.assertRaises(TypeError, qs._process_filter, [], False, uint=[])
        # для операций сравнения так же аргумент не может быть списком
        self.assertRaises(TypeError, qs._process_filter, [], False, uint__gt=[])
        self.assertRaises(TypeError, qs._process_filter, [], False, uint__gte=[])
        self.assertRaises(TypeError, qs._process_filter, [], False, uint__lt=[])
        self.assertRaises(TypeError, qs._process_filter, [], False, uint__lte=[])
        #self.assertRaises(TypeError, qs._process_filter, [], False, uint__exact=[])
        #self.assertRaises(TypeError, qs._process_filter, [], False, uint__iexact=[])
        # диапазон не может быть единственным значением
        self.assertRaises(TypeError, qs._process_filter, [], False, uint__range=1)
        # и списком с количеством значений, не равным 2
        self.assertRaises(ValueError, qs._process_filter, [], False, uint__range=[1])
        self.assertRaises(ValueError, qs._process_filter, [], False, uint__range=[1,2,3])
        # список значений не может быть пустым
        self.assertRaises(ValueError, qs._process_filter, [], False, uint__in=[])

        # по идентификатору
        item_id = 1
        item_filter_args = ('filter', 'uint', [item_id], False)
        self.assertEqual(item_filter_args, tuple(qs._process_filter([], False, uint=1)[0]))
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, uint__exact=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, uint__iexact=1)

        # по списку идентификаторов
        item_list = [1,2,3,5]
        item_list_filter_args = ('filter', 'uint', item_list, False)
        self.assertEqual(item_list_filter_args, tuple(qs._process_filter([], False, uint__in=item_list)[0]))

        # по диапазону идентификаторов
        item_range = [1,2]
        item_range_filter_args = ('range', 'uint', 1, 2, False)
        self.assertEqual(item_range_filter_args, tuple(qs._process_filter([], False, uint__range=item_range)[0]))

        # сравнение
        item_filter_gt_args = ('range', 'uint', 6, MAX_INT, False)
        item_filter_gte_args = ('range', 'uint', 5, MAX_INT, False)
        item_filter_lt_args = ('range', 'uint', 0, 4, False)
        item_filter_lte_args = ('range', 'uint', 0, 5, False)
        self.assertEqual(item_filter_gt_args, tuple(qs._process_filter([], False, uint__gt=5)[0]))
        self.assertEqual(item_filter_gte_args, tuple(qs._process_filter([], False, uint__gte=5)[0]))
        self.assertEqual(item_filter_lt_args, tuple(qs._process_filter([], False, uint__lt=5)[0]))
        self.assertEqual(item_filter_lte_args, tuple(qs._process_filter([], False, uint__lte=5)[0]))

        # по private_keys фильтрация пока не поддерживается
        #item_pk_range_filter_args = ('id_range', 1, 2)
        #self.assertEqual(item_pk_range_filter_args, tuple(qs._process_filter([], False, pk=item_range)[0]))
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, id=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__gt=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__gte=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__lt=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__lte=1)
        #self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__exact=1)
        #self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__iexact=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__in=[1,2,3])
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__range=[1,2])


        # float-значения

        # одно значение
        item_float = 5.0
        item_float_filter_args = ('filter', 'float', [item_float], False)

        self.assertEqual(item_float_filter_args, tuple(qs._process_filter([], False, float=item_float)[0]))

        # сравнение
        _float_delta = (1.0/MAX_FLOAT)
        item_float_filter_gt_args = ('float_range', 'float', item_float+_float_delta, MAX_FLOAT, False)
        item_float_filter_gte_args = ('float_range', 'float', item_float, MAX_FLOAT, False)
        item_float_filter_lt_args = ('float_range', 'float', 0, item_float-_float_delta, False)
        item_float_filter_lte_args = ('float_range', 'float', 0, item_float, False)

        self.assertEqual(item_float_filter_gt_args, tuple(qs._process_filter([], False, float__gt=item_float)[0]))
        self.assertEqual(item_float_filter_gte_args, tuple(qs._process_filter([], False, float__gte=item_float)[0]))
        self.assertEqual(item_float_filter_lt_args, tuple(qs._process_filter([], False, float__lt=item_float)[0]))
        self.assertEqual(item_float_filter_lte_args, tuple(qs._process_filter([], False, float__lte=item_float)[0]))

        # по диапазону float
        item_float_range = (1.0, 5.0)
        item_float_range_args = ('float_range', 'float', item_float_range[0], item_float_range[1], False)
        self.assertEqual(item_float_range_args, tuple(qs._process_filter([], False, float__range=item_float_range)[0]))

        item_float_list = [1.0, 5.5, 58.1]
        item_float_list_args = ('filter', 'float', item_float_list, False)
        self.assertEqual(item_float_list_args, tuple(qs._process_filter([], False, float__in=item_float_list)[0]))


        # даты
        # все даты преобразуются к float, поэтому проверим только, что функция их принимает


        item_dt_args = ('filter', 'datetime', [sphinx_dt], False)
        item_d_args = ('filter', 'date', [sphinx_d], False)
        self.assertEqual(item_dt_args, tuple(qs._process_filter([], False, datetime=dt)[0]))
        self.assertEqual(item_d_args, tuple(qs._process_filter([], False, date=d)[0]))


        # а так же QuerySet`s и различные объекты
        # для переданного объекта должен возвращать список с его первичным ключем внутри
        item_related_args = ('filter', 'related', [fk_obj.pk], False)
        self.assertEqual(item_related_args, tuple(qs._process_filter([], False, related=fk_obj)[0]))
        # в том числе для запросов по спискам
        item_related_in_args = ('filter', 'related', [fk_obj.pk], False)
        self.assertEqual(item_related_in_args, tuple(qs._process_filter([], False, related__in=fk_obj)[0]))

        item_related_qs_args = ('filter', 'related', [obj.pk for obj in fk_qs], False)
        # для QuerySet должен возвращать список первичных ключей из выборки
        self.assertEqual(item_related_qs_args, tuple(qs._process_filter([], False, related__in=fk_qs)[0]))
        # но при этом должен выдавать ошибку, если в QuerySet содержатся объекты не того типа
        self.assertRaises(TypeError, qs._process_filter, [], False, related__in=m2m_qs)

        # фильтрация по полям связанных моделей пока не реализована
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, related__name__in=fk_qs)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, related__name=fk_obj)
        #self.assertRaises(NotImplementedError, qs._process_filter, [], False, related__name__exact=fk_obj)

    def test_get(self):
        self.fail('Test not implemented')

    def test__decode_document_id(self):
        qs = ds.SphinxQuerySet()

        doc_id = 123 << ds.DOCUMENT_ID_SHIFT | 12345

        data = dict(id=doc_id,
            attrs=dict()
        )

        res = dict(id=12345,
            attrs=dict(content_type=123)
        )

        self.assertDictEqual(res, qs._decode_document_id(data))
        #TODO: дописать?

    def test__get_results(self):
        self.fail('Test not implemented')

    def test__get_doc_fields(self):
        self._prepare_models()

        obj = Search.objects.all()[0]
        qs = Search.search.none()

        inc_fields = ['text', 'excluded_field']
        exc_fields = ['name', 'text', 'excluded_field']

        self.assertEqual(inc_fields, qs._get_doc_fields(obj))

        _inc_f = obj.__sphinx_options__['included_fields'] # сохраняем значение
        obj.__sphinx_options__['included_fields'] = []
        qs._fields_cache = {}

        self.assertEqual(exc_fields, qs._get_doc_fields(obj))
        obj.__sphinx_options__['included_fields'] = _inc_f # возвращаем обратно

    def test__get_passages(self):
        passages = {
            'text': 'text',
        }
        passages2 = passages.copy()
        passages2.update({
            'excluded_field': 'exc',
        })

        obj = Search(
            name='name',
            text='text',
            excluded_field='exc',
            bool=False,
        )
        qs = Search.search.none()

        # поля по заданному списку
        self.assertEqual(passages, qs._get_passages(obj, '', ['text']))

        # поля на основании опций SphinxSearch
        self.assertEqual(passages2, qs._get_passages(obj, ''))

        # несуществующее поле
        self.assertRaises(AttributeError, qs._get_passages, obj, '', ['attr'])

    def _prepare_models(self):
        for x in range(0, 10):
            r = any_model(Related)
            m = any_model(M2M)
            any_model(Search, related=r, m2m=m)

    def _get_test_opts(self):

        opts = {'_rankmode': sphinxapi.SPH_RANK_NONE,
            '_mode': sphinxapi.SPH_MATCH_ALL,
            '_weights': {},
            '_maxmatches': 100,
            '_passages': True,
            '_passages_opts': {}
        }

        kwargs = dict(rankmode='SPH_RANK_NONE',
            mode='SPH_MATCH_ALL',
            weights={},
            maxmatches=100,
            passages=True,
            passages_opts={},
            wrong_opt1=1,
            wrong_opt2=1
        )

        return (opts, kwargs)


class TestSphinxQLQueryset(TestCase):

    def test__parse_index(self):
        qs = ds.SphinxQLQuerySet()

        self.assertEqual(0, len(qs._indexes))

        qs = ds.SphinxQLQuerySet(index='one1_-')

        self.assertListEqual(['one1_-'], qs._indexes)

        qs = ds.SphinxQLQuerySet(index='one two')

        self.assertListEqual(['one', 'two'], qs._indexes)

        qs = ds.SphinxQLQuerySet(index='onE!@#$%^&*(){}?/+=|\\:;tWo!!!')

        self.assertListEqual(['one', 'two'], qs._indexes)

    def test_add_index(self):
        qs = ds.SphinxQLQuerySet(index='one')

        qs1 = qs.add_index('two')

        self.assertListEqual(['one', 'two'], qs1._indexes)
        self.assertListEqual(['one'], qs._indexes)

    def test_remove_index(self):
        qs = ds.SphinxQLQuerySet(index='one two')

        qs1 = qs.remove_index('one')

        self.assertListEqual(['two'], qs1._indexes)
        self.assertListEqual(['one', 'two'], qs._indexes)

    def test_query(self):
        qs = ds.SphinxQLQuerySet()

        qs1 = qs.query('test')

        self.assertEqual('test', qs1._query)
        self.assertEqual('', qs._query)

    def test__process_single_object_operation(self):
        self._prepare_models()

        model_qs = ds.SphinxQLQuerySet(model=Search)
        qs = ds.SphinxQLQuerySet()

        obj = Related.objects.all()[0]

        self.assertEqual(obj.pk, model_qs._process_single_obj_operation(obj))
        self.assertRaises(ValueError, qs._process_single_obj_operation, obj)



        self.assertEqual(sphinx_d, model_qs._process_single_obj_operation(d))
        self.assertEqual(sphinx_d, qs._process_single_obj_operation(d))

        self.assertEqual(sphinx_dt, model_qs._process_single_obj_operation(dt))
        self.assertEqual(sphinx_dt, qs._process_single_obj_operation(dt))

        mqs = Related.objects.all()
        for x in [mqs, list(), tuple(), dict()]:
            self.assertRaises(TypeError, qs._process_single_obj_operation, mqs)

    def test__process_obj_list_operation(self):
        self._prepare_models()

        model_qs = ds.SphinxQLQuerySet(model=Search)
        qs = ds.SphinxQLQuerySet()

        obj = Related.objects.all()[0]
        obj_list = Related.objects.all()

        self.assertListEqual([obj.pk], model_qs._process_obj_list_operation(obj))
        self.assertListEqual([o.pk for o in obj_list], model_qs._process_obj_list_operation(obj_list))
        self.assertRaises(ValueError, qs._process_obj_list_operation, obj)
        self.assertRaises(ValueError, qs._process_obj_list_operation, obj_list)

        self.assertListEqual([1], qs._process_obj_list_operation(1))
        self.assertListEqual([sphinx_d], qs._process_obj_list_operation(d))
        self.assertListEqual([sphinx_dt], qs._process_obj_list_operation(dt))
        self.assertListEqual([4.2], qs._process_obj_list_operation(4.2))
        self.assertListEqual([1,2,3], qs._process_obj_list_operation([1,2,3]))
        self.assertListEqual([1,2,3], qs._process_obj_list_operation((1,2,3)))
        self.assertListEqual([1,2,3], qs._process_obj_list_operation(iter([1,2,3])))

        self.assertRaises(ValueError, qs._process_obj_list_operation, dict(a=1,b=2))

    def test__process_filters(self):
        qs = ds.SphinxQLQuerySet()

        self.assertDictEqual({}, qs._filters)

        self.assertDictEqual({'field': '`field` = 1'}, qs._process_filters({}, False, field=1))
        self.assertDictEqual({'field__in': '`field` IN (1,2,3)'}, qs._process_filters({}, False, field__in=[1,2,3]))
        self.assertDictEqual({'field__gt': '`field` > 1'}, qs._process_filters({}, False, field__gt=1))
        self.assertDictEqual({'field__gte': '`field` >= 1'}, qs._process_filters({}, False, field__gte=1))
        self.assertDictEqual({'field__lt': '`field` < 1'}, qs._process_filters({}, False, field__lt=1))
        self.assertDictEqual({'field__lte': '`field` <= 1'}, qs._process_filters({}, False, field__lte=1))
        self.assertDictEqual({'field__range': '`field` BETWEEN 1 AND 2'}, qs._process_filters({}, False, field__range=[1,2]))

        self.assertDictEqual({'field': '`field` != 1'}, qs._process_filters({}, True, field=1))
        self.assertDictEqual({'field__in': '`field` NOT IN (1,2,3)'}, qs._process_filters({}, True, field__in=[1,2,3]))
        self.assertDictEqual({'field__gt': '`field` <= 1'}, qs._process_filters({}, True, field__gt=1))
        self.assertDictEqual({'field__gte': '`field` < 1'}, qs._process_filters({}, True, field__gte=1))
        self.assertDictEqual({'field__lt': '`field` >= 1'}, qs._process_filters({}, True, field__lt=1))
        self.assertDictEqual({'field__lte': '`field` > 1'}, qs._process_filters({}, True, field__lte=1))
        self.assertDictEqual({'field__range': 'NOT `field` BETWEEN 1 AND 2'}, qs._process_filters({}, True, field__range=[1,2]))

        self.assertRaises(ValueError, qs._process_filters, {}, False, field__range=[1])
        self.assertRaises(ValueError, qs._process_filters, {}, False, field__range=[1,2,3])

    def test__filter(self):
        qs = ds.SphinxQLQuerySet()

        self.assertDictEqual({}, qs._filters)

        qs1 = qs.filter(field=1)

        self.assertDictEqual({'field': '`field` = 1'}, qs1._filters)
        self.assertDictEqual({}, qs._filters)

        self._is_cloned(qs, qs1)

    def test__exclude(self):
        qs = ds.SphinxQLQuerySet()

        self.assertDictEqual({}, qs._excludes)

        qs1 = qs.exclude(field=1)

        self.assertDictEqual({'field': '`field` != 1'}, qs1._excludes)
        self.assertDictEqual({}, qs._excludes)

        self._is_cloned(qs, qs1)

    def test_values(self):
        qs = ds.SphinxQLQuerySet()

        self.assertEqual('*', qs._fields)
        self.assertDictEqual({}, qs._aliases)

        qs1 = qs.values('field1', 'field2')
        self.assertEqual('`field1`, `field2`', qs1._fields)

        qs2 = qs.values(x='karma*100+user_id')
        self.assertDictEqual({'x': 'karma*100+user_id AS `x`'}, qs2._aliases)

        self._is_cloned(qs, qs1)
        self._is_cloned(qs, qs2)

    def test_group_by(self):
        qs = ds.SphinxQLQuerySet()

        qs1 = qs.group_by('title')

        self.assertEqual('GROUP BY `title`', qs1._group_by)
        self.assertEqual('', qs._group_by)

        # группировка только по одному полю или по вычисленному значению
        self.assertRaises(TypeError, qs.group_by, 'field1', 'field2')

    def test_order_by(self):
        qs = ds.SphinxQLQuerySet()

        qs1 = qs.order_by()
        self.assertEqual(qs, qs1)

        qs2 = qs.order_by('pk')
        self.assertEqual('ORDER BY `id` ASC', qs2._order_by)

        qs3 = qs.order_by('-title')
        self.assertEqual('ORDER BY `title` DESC', qs3._order_by)

        qs4 = qs.order_by('field1', '-field2')
        self.assertEqual('ORDER BY `field1` ASC, `field2` DESC', qs4._order_by)

    def test_group_order_by(self):
        qs = ds.SphinxQLQuerySet()

        qs1 = qs.group_order()
        self.assertEqual(qs, qs1)

        qs2 = qs.group_order('pk')
        self.assertEqual('WITHIN GROUP ORDER BY `id` ASC', qs2._group_order_by)

        qs3 = qs.group_order('-title')
        self.assertEqual('WITHIN GROUP ORDER BY `title` DESC', qs3._group_order_by)

        qs4 = qs.group_order('field1', '-field2')
        self.assertEqual('WITHIN GROUP ORDER BY `field1` ASC, `field2` DESC', qs4._group_order_by)

    def test_all(self):
        qs = ds.SphinxQLQuerySet()

        self.assertEqual([], list(qs))

        qs2 = qs.all()

        self.assertEqual(qs2, qs)

    def test_none(self):
        qs = ds.SphinxQLQuerySet()
        qs1 = qs.none()

        self.assertIsInstance(qs1, ds.EmptySphinxQLQuerySet)
        self.assertListEqual([], list(qs1))

    def test_reset(self):
        qs = ds.SphinxQLQuerySet(model=Search, using='somedb', index='one, two')

        self.assertEqual(qs.model, Search)
        self.assertEqual('somedb', qs.using)
        self.assertListEqual(['one', 'two'], qs._indexes)

        qs1 = qs.reset()
        self.assertEqual(qs.model, qs1.model)
        self.assertEqual(qs.using, qs1.using)
        self.assertListEqual(qs._indexes, qs1._indexes)

        self._is_cloned(qs, qs1)

    def test_set_options(self):
        qs = ds.SphinxQLQuerySet()

        qs1 = qs.set_options(ranker='bm25')
        self.assertEqual('OPTION ranker=bm25', qs1._query_opts)

        qs2 = qs.set_options(max_matches=1)
        self.assertEqual('OPTION max_matches=1', qs2._query_opts)

        qs3 = qs.set_options(cutoff=1)
        self.assertEqual('OPTION cutoff=1', qs3._query_opts)

        qs4 = qs.set_options(max_query_time=1)
        self.assertEqual('OPTION max_query_time=1', qs4._query_opts)

        qs5 = qs.set_options(retry_delay=1)
        self.assertEqual('OPTION retry_delay=1', qs5._query_opts)

        qs6 = qs.set_options(field_weights={'title': 100})
        self.assertEqual('OPTION field_weights=(title=100)', qs6._query_opts)
        #TODO: тест с regexp

        qs7 = qs.set_options(index_weights={'one': 100})
        self.assertEqual('OPTION index_weights=(one=100)', qs7._query_opts)
        #TODO: тест с regexp

        qs8 = qs.set_options(reverse_scan=True)
        self.assertEqual('OPTION reverse_scan=1', qs8._query_opts)
        qs9 = qs.set_options(reverse_scan=False)
        self.assertEqual('OPTION reverse_scan=0', qs9._query_opts)
        qs10 = qs.set_options(reverse_scan=1)
        self.assertEqual('OPTION reverse_scan=1', qs10._query_opts)
        qs11 = qs.set_options(reverse_scan=0)
        self.assertEqual('OPTION reverse_scan=0', qs11._query_opts)

        qs12 = qs.set_options(comment='some comment')
        self.assertEqual('OPTION comment=\'some comment\'', qs12._query_opts)

        opts = dict(ranker='bm25x', max_matches=list(), cutoff='sth', max_query_time=dict(),
            retry_delay='aoe', field_weights=('title', 'text'),
            index_weights=['one'], reverse_scan='stn', comment=1)

        for x in opts:
            self.assertRaises(AssertionError, qs.set_options, **{x: opts[x]})

        Search.objects.update()


    # internal
    def _prepare_models(self):
        for x in range(0, 10):
            r = any_model(Related)
            m = any_model(M2M)
            any_model(Search, related=r, m2m=m)

    def _is_cloned(self, qs1, qs2):
        qs1.__dict__ = qs2.__dict__

        self.assertNotEqual(qs1, qs2)
