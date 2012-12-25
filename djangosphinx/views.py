from django.views.generic import TemplateView
from django.views.generic.list import ListView
from django.db import models

from djangosphinx.models import SphinxQuerySet
from djangosphinx.shortcuts import sphinx_query


class SearchResultsList(ListView):
    template_name = 'search_list.html'
    paginate_by = 20

    def get_template_names(self):
        return self.template_name

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data(object_list=self.object_list)
        try:
            context['page'] = context['paginator'].page(int(request.GET['page']))
        except:
            context['page'] = context['paginator'].page(1)
        context['query'] = request.GET['q']

        return self.render_to_response(context)

    def get_queryset(self):
        query = self.request.GET['q']
        return sphinx_query(query)

    def get_context_object_name(self, request, *args, **kwargs):
        return "Search"


class SearchResults(TemplateView):
    template_name = 'search.html'

    def get_context_object_name(self, request, *args, **kwargs):
        return "Search"

    def get(self, request, *args, **kwargs):

        query = request.GET['q']
        filter_query = request.GET.get('filter', None)
        limit = 20

        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1
        else:
            qs = sphinx_query(query)

        context = self.get_context_data(params=kwargs)

        try:
            offset = limit * (page - 1)
            results = list(qs[offset:offset + limit])
            count = qs.count()
        except:
            count = -1
            results = []
            offset = 0

        context['page'] = page
        context['count'] = count
        context['num_pages'] = max(1, count / limit)
        context['object_list'] = results
        context['query'] = query
        context['filter'] = filter_query
        if context['num_pages'] > 1:
            context['is_paginated'] = True
        if page > 1:
            context['previous_page_number'] = page - 1
        if page < context['num_pages']:
            context['next_page_number'] = page + 1

        return self.render_to_response(context)
