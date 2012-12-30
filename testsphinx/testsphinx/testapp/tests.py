# coding: utf-8
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import datetime
import time

from django.db.models.fields import FieldDoesNotExist
from django.test import TestCase

from django_any import any_model

from djangosphinx.models import MAX_INT, MAX_FLOAT

from models import *


class FakeSphinxClient(object):

    def __init__(self, *args, **kwargs):
        pass

    def SetSerner(*args, **kwargs):
        pass

    def BuildExcerpts(self, *args, **kwargs):
        return []

class FSCExcerpts(FakeSphinxClient):

    def BuildExcerpts(self, *args, **kwargs):
        return kwargs['docs']

class TestSphinxQuerySet(TestCase):

    def setUp(self):
        for x in range(0, 10):
            r = any_model(Related)
            m = any_model(M2M)
            any_model(Search, related=r, m2m=m)

    def test_doc_fields_list(self):

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

    def test_get_passages(self):
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

    def test_all_and_none_querysets(self):

        qs = Search.search.none()

        self.assertEqual([], list(qs))

        qs2 = qs.all()

        self.assertEqual(qs2, qs)

    def test_model_queryset_filter(self):

        qs = Search.search.query('test')

        # test _check_field
        int_field_name = 'uint'
        int_field = Search._meta.get_field(int_field_name)
        str_field = 'name'

        self.assertRaises(TypeError, qs._check_field, str_field)
        self.assertEqual(int_field, qs._check_field(int_field_name))

        # test _check_related_field
        non_rel_field = Search._meta.get_field('name')
        fk_field = Search._meta.get_field('related')
        m2m_field = Search._meta.get_field('m2m')

        fk_obj = Related.objects.all()[0]
        fk_qs = Related.objects.all()

        m2m_obj = M2M.objects.all()[0]
        m2m_qs = M2M.objects.all()

        self.assertRaises(TypeError, qs._check_related_field, non_rel_field, None)

        self.assertRaises(TypeError, qs._check_related_field, fk_field, m2m_obj)
        self.assertRaises(TypeError, qs._check_related_field, m2m_field, fk_obj)

        self.assertEqual(fk_field, qs._check_related_field(fk_field, fk_obj))
        self.assertEqual(m2m_field, qs._check_related_field(m2m_field, m2m_obj))



        # test _process_filter
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
        self.assertRaises(TypeError, qs._process_filter, [], False, uint__exact=[])
        self.assertRaises(TypeError, qs._process_filter, [], False, uint__iexact=[])
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
        self.assertEqual(item_filter_args, tuple(qs._process_filter([], False, uint__exact=1)[0]))
        self.assertEqual(item_filter_args, tuple(qs._process_filter([], False, uint__iexact=1)[0]))

        # по списку идентификаторов
        item_list = [1,2,3,5]
        item_list_filter_args = ('filter', 'uint', item_list, False)
        self.assertEqual(item_list_filter_args, tuple(qs._process_filter([], False, uint__in=item_list)[0]))

        # по диапазону идентификаторов
        item_range = [1,2]
        item_range_filter_args = ('range', 'uint', 1, 2, False)
        self.assertEqual(item_range_filter_args, tuple(qs._process_filter([], False, uint__range=item_range)[0]))


        # по private_keys фильтрация пока не поддерживается
        #item_pk_range_filter_args = ('id_range', 1, 2)
        #self.assertEqual(item_pk_range_filter_args, tuple(qs._process_filter([], False, pk=item_range)[0]))
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, id=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__gt=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__gte=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__lt=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__lte=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__exact=1)
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, pk__iexact=1)
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
        item_float_filter_lt_args = ('float_range', 'float', MAX_FLOAT, item_float-_float_delta, False)
        item_float_filter_lte_args = ('float_range', 'float', MAX_FLOAT, item_float, False)

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
        dt = datetime.datetime.now()
        d = datetime.date.today()
        sphinx_dt = time.mktime(dt.timetuple())
        sphinx_d = time.mktime(d.timetuple())

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
        self.assertRaises(NotImplementedError, qs._process_filter, [], False, related__name__exact=fk_obj)
