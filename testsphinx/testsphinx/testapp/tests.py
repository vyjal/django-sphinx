# coding: utf-8
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from __future__ import unicode_literals, absolute_import

import datetime
import time

from django.db.models.query import QuerySet
from django.db.models.fields import FieldDoesNotExist
from django.test import TestCase

from django_any import any_model

from djangosphinx import models as ds
from djangosphinx.conf import SPHINX_MAX_MATCHES, SPHINX_QUERY_LIMIT
from djangosphinx.query.queryset import EmptySphinxQuerySet, EMPTY_RESULT_SET

from .models import *

dt = datetime.datetime.now()
d = datetime.date.today()
sphinx_dt = time.mktime(dt.timetuple())
sphinx_d = time.mktime(d.timetuple())

class TestFunctions(TestCase):

    def test_to_sphinx(self):
        from djangosphinx.query.queryset import to_sphinx, decimal

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
        qs = EmptySphinxQuerySet()
        self.assertEqual(EMPTY_RESULT_SET, qs.meta);
        self.assertEqual([], list(qs));


class TestSphinxQuerySet(TestCase):

    def test__parse_indexes(self):
        qs = ds.SphinxQuerySet()

        self.assertListEqual([], qs._parse_indexes(None))

        self.assertListEqual(['one1_-'], qs._parse_indexes('one1_-'))

        self.assertListEqual(['one', 'two'], qs._parse_indexes('one two'))

        self.assertListEqual(['one', 'two'], qs._parse_indexes('onE!@#$%^&*(){}?/+=|\\:;tWo!!!'))

    def test_add_index(self):
        qs = ds.SphinxQuerySet(index='one')

        qs1 = qs.add_index('two')

        self.assertListEqual(['one', 'two'], qs1._indexes)
        self.assertListEqual(['one'], qs._indexes)

    def test_remove_index(self):
        qs = ds.SphinxQuerySet(index='one two')

        qs1 = qs.remove_index('one')

        self.assertListEqual(['two'], qs1._indexes)
        self.assertListEqual(['one', 'two'], qs._indexes)

    def test_query(self):
        qs = ds.SphinxQuerySet()

        qs1 = qs.query('test')

        self.assertEqual('test', qs1._query)
        self.assertEqual(None, qs._query)

    def test__process_single_object_operation(self):
        self._prepare_models()

        model_qs = ds.SphinxQuerySet(model=Search)
        qs = ds.SphinxQuerySet()

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

        model_qs = ds.SphinxQuerySet(model=Search)
        qs = ds.SphinxQuerySet()

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
        qs = ds.SphinxQuerySet()

        self.assertDictEqual({}, qs._filters)

        self.assertDictEqual({'field': 'field = 1'}, qs._process_filters({}, False, field=1))
        self.assertDictEqual({'field': 'field IN (1,2,3)'}, qs._process_filters({}, False, field__in=[1,2,3]))
        self.assertDictEqual({'field': 'field > 1'}, qs._process_filters({}, False, field__gt=1))
        self.assertDictEqual({'field': 'field >= 1'}, qs._process_filters({}, False, field__gte=1))
        self.assertDictEqual({'field': 'field < 1'}, qs._process_filters({}, False, field__lt=1))
        self.assertDictEqual({'field': 'field <= 1'}, qs._process_filters({}, False, field__lte=1))
        self.assertDictEqual({'field': 'field BETWEEN 1 AND 2'}, qs._process_filters({}, False, field__range=[1,2]))

        self.assertDictEqual({'field': 'field != 1'}, qs._process_filters({}, True, field=1))
        self.assertDictEqual({'field': 'field NOT IN (1,2,3)'}, qs._process_filters({}, True, field__in=[1,2,3]))
        self.assertDictEqual({'field': 'field <= 1'}, qs._process_filters({}, True, field__gt=1))
        self.assertDictEqual({'field': 'field < 1'}, qs._process_filters({}, True, field__gte=1))
        self.assertDictEqual({'field': 'field >= 1'}, qs._process_filters({}, True, field__lt=1))
        self.assertDictEqual({'field': 'field > 1'}, qs._process_filters({}, True, field__lte=1))
        self.assertDictEqual({'field': 'NOT field BETWEEN 1 AND 2'}, qs._process_filters({}, True, field__range=[1,2]))

        self.assertRaises(ValueError, qs._process_filters, {}, False, field__range=[1])
        self.assertRaises(ValueError, qs._process_filters, {}, False, field__range=[1,2,3])

    def test__filter(self):
        qs = ds.SphinxQuerySet()

        self.assertDictEqual({}, qs._filters)

        qs1 = qs.filter(field=1)

        self.assertDictEqual({'field': 'field = 1'}, qs1._filters)
        self.assertDictEqual({}, qs._filters)

        self._is_cloned(qs, qs1)

    def test__exclude(self):
        qs = ds.SphinxQuerySet()

        self.assertDictEqual({}, qs._excludes)

        qs1 = qs.exclude(field=1)

        self.assertDictEqual({'field': 'field != 1'}, qs1._excludes)
        self.assertDictEqual({}, qs._excludes)

        self._is_cloned(qs, qs1)

    def test_fields(self):
        qs = ds.SphinxQuerySet()

        self.assertEqual('*', qs._fields)
        self.assertDictEqual({}, qs._aliases)

        qs1 = qs.fields('field1', 'field2')
        self.assertEqual('`field1`, `field2`', qs1._fields)

        qs2 = qs.fields(x='karma*100+user_id')
        self.assertDictEqual({'x': 'karma*100+user_id AS `x`'}, qs2._aliases)

        self._is_cloned(qs, qs1)
        self._is_cloned(qs, qs2)

    def test__format_options(self):
        qs = ds.SphinxQuerySet()

        self.assertEqual('', qs._format_options())

        self.assertEqual('OPTION reverse_scan=1', qs._format_options(reverse_scan=True))
        self.assertEqual('OPTION field_weights=(field=100)',
            qs._format_options(field_weights={'field':100}))

    def test_options(self):
        qs = ds.SphinxQuerySet()

        qs1 = qs.options()
        self.assertEqual(qs, qs1)

        qs2 = qs.options(reverse_scan=True)
        self.assertEqual('OPTION reverse_scan=1', qs2._query_opts)

        self._is_cloned(qs, qs2)

    def test_snippets(self):
        qs = ds.SphinxQuerySet()

        qs._snippets = False
        qs1 = qs.snippets(False)

        self.assertEqual(qs1, qs)

        qs2 = qs.snippets()
        self.assertEqual(qs2._snippets, True)

        qs._snippets_opts_string = 'str'
        qs._snippets_opts = dict()

        qs3 = qs.snippets(option=1)
        self.assertEqual(None, qs3._snippets_opts_string)
        self.assertDictEqual({'option': 1}, qs3._snippets_opts)

        self._is_cloned(qs, qs3)

    def test_group_by(self):
        qs = ds.SphinxQuerySet()

        qs1 = qs.group_by('title')

        self.assertEqual('GROUP BY `title`', qs1._group_by)
        self.assertEqual('', qs._group_by)

        # группировка только по одному полю или по вычисленному значению
        self.assertRaises(TypeError, qs.group_by, 'field1', 'field2')

    def test_order_by(self):
        qs = ds.SphinxQuerySet()

        qs1 = qs.order_by()
        self.assertEqual(qs, qs1)

        qs2 = qs.order_by('pk')
        self.assertEqual('ORDER BY `id` ASC', qs2._order_by)

        qs3 = qs.order_by('-title')
        self.assertEqual('ORDER BY `title` DESC', qs3._order_by)

        qs4 = qs.order_by('field1', '-field2')
        self.assertEqual('ORDER BY `field1` ASC, `field2` DESC', qs4._order_by)

    def test_group_order_by(self):
        qs = ds.SphinxQuerySet()

        qs1 = qs.group_order_by()
        self.assertEqual(qs, qs1)

        qs2 = qs.group_order_by('pk')
        self.assertEqual('WITHIN GROUP ORDER BY `id` ASC', qs2._group_order_by)

        qs3 = qs.group_order_by('-title')
        self.assertEqual('WITHIN GROUP ORDER BY `title` DESC', qs3._group_order_by)

        qs4 = qs.group_order_by('field1', '-field2')
        self.assertEqual('WITHIN GROUP ORDER BY `field1` ASC, `field2` DESC', qs4._group_order_by)

    def test_all(self):
        qs = ds.SphinxQuerySet(maxmatches=SPHINX_MAX_MATCHES-100)

        qs2 = qs.all()

        self.assertEqual(SPHINX_MAX_MATCHES-100, qs2._limit)
        self.assertEqual(None, qs2._offset)

        self._is_cloned(qs, qs2)

    def test_none(self):
        qs = ds.SphinxQuerySet()
        qs1 = qs.none()

        self.assertIsInstance(qs1, EmptySphinxQuerySet)
        self.assertListEqual([], list(qs1))
        self.assertDictEqual(EMPTY_RESULT_SET, qs1.meta)

    def test_reset(self):
        qs = ds.SphinxQuerySet(model=Search, using='somedb', index='one, two')

        self.assertEqual(qs.model, Search)
        self.assertEqual('somedb', qs.using)
        #self.assertListEqual(['one', 'two'], qs._indexes)

        qs1 = qs.reset()
        self.assertEqual(qs.model, qs1.model)
        self.assertEqual(qs.using, qs1.using)
        self.assertListEqual(qs._indexes, qs1._indexes)

        self._is_cloned(qs, qs1)

    def test_get_query_set(self):
        pass # хз, что тут написать...

    def test_set_limits(self):
        qs = ds.SphinxQuerySet()

        self.assertEqual(SPHINX_QUERY_LIMIT, qs._limit)
        self.assertEqual(None, qs._offset)

        qs._set_limits(100)
        self.assertEqual(SPHINX_QUERY_LIMIT, qs._limit)
        self.assertEqual(100, qs._offset)

        qs._set_limits(100, 200)
        self.assertEqual(100, qs._limit)
        self.assertEqual(100, qs._offset)

    def test__get_index(self):
        qs = ds.SphinxQuerySet()

        qs._indexes = ['one', 'two']
        self.assertEqual('one two', qs._get_index())

    def test__meta(self):
        pass  # этот тест не пройдёт без подключения к sphinx и индекса в нём

    def test__fill_cache(self):
        pass

    def test__get_snippets_string(self):
        qs = ds.SphinxQuerySet()
        self.assertEqual('', qs._get_snippets_string())

        qs1 = ds.SphinxQuerySet(snippets_options={'option':1})
        self.assertEqual(', 1 AS option', qs1._get_snippets_string())

        qs1 = ds.SphinxQuerySet(snippets_options={'option':'str'})
        self.assertEqual(', \'str\' AS option', qs1._get_snippets_string())

    def test__get_data(self):
        pass # аналогично не пройдёт без Sphinx

    def test__get_snippets(self):
        pass

    def test__get_doc_fields(self):
        self._prepare_models()

        obj = Search.objects.all()[0]
        qs = Search.search.none()

        inc_fields = ['text', 'excluded_field']
        exc_fields = ['name', 'text', 'excluded_field']

        self.assertEqual(inc_fields, qs._get_doc_fields(obj))

        _inc_f = obj.__sphinx_options__['included_fields'] # сохраняем значение
        obj.__sphinx_options__['included_fields'] = []
        qs._doc_fields_cache = {}

        self.assertEqual(exc_fields, qs._get_doc_fields(obj))
        obj.__sphinx_options__['included_fields'] = _inc_f # возвращаем обратно

    def test__decode_document_id(self):
        """
        >>> (123 << 52) | 3456
        553942754166574464
        """

        qs = ds.SphinxQuerySet()

        self.assertEqual((3456, 123), qs._decode_document_id(553942754166574464))
        self.assertRaises(AssertionError, qs._decode_document_id, 'str')



    # internal
    def _prepare_models(self):
        for x in range(0, 10):
            r = any_model(Related)
            m = any_model(M2M)
            any_model(Search, related=r, m2m=m)

    def _is_cloned(self, qs1, qs2):
        qs1.__dict__ = qs2.__dict__

        self.assertNotEqual(qs1, qs2)
