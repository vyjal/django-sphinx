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

    def test_doc_fields_list(self):

        obj = Search.objects.get(pk=2)
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
        non_rel_field = 'name'
        fk_field_name = 'related'
        fk_field = Search._meta.get_field(fk_field_name)
        m2m_field_name = 'm2m'
        m2m_field = Search._meta.get_field(m2m_field_name)

        fk_obj = Related.objects.get(pk=2)
        fk_qs = Related.objects.filter(pk__in=[2,3])

        m2m_obj = M2M.objects.get(pk=2)
        m2m_qs = M2M.objects.filter(pk__in=[2,3])

        self.assertRaises(AttributeError, qs._check_related_field, non_rel_field, None)

        self.assertRaises(TypeError, qs._check_related_field, fk_field_name, m2m_obj)
        self.assertRaises(TypeError, qs._check_related_field, m2m_field_name, fk_obj)

        self.assertEqual(fk_field, qs._check_related_field(fk_field_name, fk_obj))
        self.assertEqual(m2m_field, qs._check_related_field(m2m_field_name, m2m_obj))



        # test _process_filter
        # только числа и даты могут быть переданы в эту функцию (в том числе списками)
        d = datetime.datetime.now()
        sphinx_time = time.mktime(d.timetuple())
        self.assertRaises(ValueError, qs._process_filter, {}, False, field='string')
        self.assertEqual({'field': [1]}, qs._process_filter({}, False, field=1))
        self.assertEqual({'field': [1]}, qs._process_filter({}, False, field=[1]))
        self.assertEqual({'field': [1.0]}, qs._process_filter({}, False, field=1.0))
        self.assertEqual({'field': [1.0]}, qs._process_filter({}, False, field=[1.0]))
        self.assertEqual({'field': [sphinx_time]}, qs._process_filter({}, False, field=d))
        self.assertEqual({'field': [sphinx_time]}, qs._process_filter({}, False, field=[d]))



        # а так же QuerySet`s и различные объекты
        # для переданного объекта должен возвращать список с его первичным ключем внутри
        self.assertEqual({'related': [2]}, qs._process_filter({}, False, related=fk_obj))
        # в том числе для range-запросов
        self.assertEqual({'related__in': [2]}, qs._process_filter({}, False, related__in=fk_obj))
        # но при этом должен выдавать ошибку, если поле не связано с переданным объектом
        self.assertRaises(AttributeError, qs._process_filter, {}, False, name=fk_obj)
        # а так же если поле отсутствует в модели
        self.assertRaises(FieldDoesNotExist, qs._process_filter, {}, False, some_field=fk_obj)

        # для QuerySet должен возвращать список первичных ключей из выборки
        self.assertEqual({'related__in': [2,3]}, qs._process_filter({}, False, related__in=fk_qs))
        # но при этом должен выдавать ошибку, если в QuerySet содержатся объекты не того типа
        self.assertRaises(TypeError, qs._process_filter, {}, False, related__in=m2m_qs)

        # фильтрация по полям связанных моделей пока не реализована
        self.assertRaises(NotImplementedError, qs._process_filter, {}, False, related__name__in=fk_qs)
        self.assertRaises(NotImplementedError, qs._process_filter, {}, False, related__name=fk_obj)
        self.assertRaises(NotImplementedError, qs._process_filter, {}, False, related__name__exact=fk_obj)