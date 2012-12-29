# coding: utf-8
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import datetime
import time

from django.test import TestCase

from django_any import any_model

from models import *


class TestSphinxQuerySet(TestCase):

    def test_model_queryset_filter(self):

        qs = Search.search.query('test')

        # test _check_field
        non_rel_field = Search._meta.get_field('name')
        fk_field = Search._meta.get_field('related')
        m2m_field = Search._meta.get_field('m2m')

        fk_obj = Related.objects.get(pk=2)

        m2m_obj = M2M.objects.get(pk=2)

        self.assertRaises(ValueError, qs._check_field, non_rel_field, None)

        self.assertRaises(TypeError, qs._check_field, fk_field, m2m_obj)
        self.assertRaises(TypeError, qs._check_field, m2m_field, fk_obj)

        self.assertTrue(qs._check_field(fk_field, fk_obj))
        self.assertTrue(qs._check_field(m2m_field, m2m_obj))


        # test _process_filter
        # только числа и даты могут быть переданы в эту функцию (в том числе списками)
        d = datetime.datetime.now()
        sphinx_time = time.mktime(d.timetuple())
        self.assertRaises(ValueError, qs._process_filter, {}, field='string')
        self.assertEqual({'field': [1]}, qs._process_filter({}, field=1))
        self.assertEqual({'field': [1]}, qs._process_filter({}, field=[1]))
        self.assertEqual({'field': [1.0]}, qs._process_filter({}, field=1.0))
        self.assertEqual({'field': [1.0]}, qs._process_filter({}, field=[1.0]))
        self.assertEqual({'field': [sphinx_time]}, qs._process_filter({}, field=d))
        self.assertEqual({'field': [sphinx_time]}, qs._process_filter({}, field=[d]))



        # а так же QuerySet`s и различные объекты

