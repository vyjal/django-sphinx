Это прослойка, подобная Django ORM, работающая поверх Sphinx full-text поискового движка (http://www.sphinxsearch.com)


Установка
---------

*В данный момент нет пакетов, доступных для установки. Используйте Git, чтобы скачать актуальную версию пакета.*
**Note**: для пользователей Gentoo есть ebuild: https://github.com/Yuego/overlay/tree/master/dev-python/django-sphinx

*SphinxAPI не входит в состав данного пакета. Пожалуйста используйте `sphinxapi.py` из архива соответствующей версии sphinx. Необходимо в Вашем Python Path создать пакет с именем `sphinxapi`, в который поместить `sphinxapi.py`.*
**Note**: для пользователей Gentoo так же есть ebuild: https://github.com/Yuego/overlay/tree/master/dev-python/sphinx-api

Настройка
---------

**Note**: для каждой модели можно указать только одино поле типа SphinxSearch!::

    # Пример настройки и использования:

    from django.db import models
    from djangosphinx.models import SphinxSearch

    class RelatedModel(models.Model)
        name = models.CharField(max_length = 100)

    class M2MModel(models.Model)
        name = models.CharField(max_length = 100)

    class MyModel(models.Model):

        related_field = models.ForeignKey(RelatedModel)
        related_field2 = models.OneToOneField(RelatedModel)
        m2m_field = models.ManyToManyField(M2MModel)

        name = models.CharField(max_length=10)
        text = models.TextField()
        stored_string = models.CharField(max_length=100)
        stored_string2 = models.CharField(max_length=100)

        datetime = models.DateTimeField()
        bool = models.BooleanField()
        uint = models.IntegerField()

        excluded_field = models.CharField(max_length=10)
        excluded_field2 = models.CharField(max_length=10)

        search = SphinxSearch() # можно не указывать никаких аргументов.
        # В этом случае будут проиндексированы все поля модели,
        # название индекса будет приравнено к MyModel._meta.db_table
        # Однако, вы можете дать индексу собственное название
        search = SphinxSearch('index_name')

        # Или, быть может, что-то более... специфичное
        searchdelta = SphinxSearch(
            index='index_name delta_name',
            weights={                   # см.
                'name': 100,
                'description': 10,
                'tags': 80,
            },
            mode='SPH_MATCH_ALL',       # см. http://sphinxsearch.com/docs/2.0.4/matching-modes.html
            rankmode='SPH_RANK_NONE',   # см. http://sphinxsearch.com/docs/2.0.4/weighting.html
        )

        # выбор полей для индексации
        my_search = SphinxSearch(
            'included_fields': [
                'text',
                'bool',
                'uint',
            ],
            'excluded_fields': [
                'excluded_field2',
            ],
            'stored_attributes': [
                'stored_string',
                'datetime',
            ],
            'stored_fields': [
                'stored_string2',
            ]
            'related_fields': [
                'related_field',
                'related_field2',

            ],
            'mva_fields': {
                'm2m_field',
            },
        )


**included_fields**

Список полей, которые необходимо включить в индекс. Все текстовые поля будут проиндексированы как full-text (но не как атрибуты). Все нетекстовые поля (за некоторыми исключениями, см. ниже) будут проиндексированы как stored attributes.

**excluded_fields**

Список исключенных из индекса полей. Может быть использован, чтобы внести в индекс все поля модели, за исключением указанных здесь.
Имеет приоритет над `included_fields`, `stored_attributes`, `stored_fields`. Все поля, перечисленные в `excluded_fields`, будут удалены из этих списков.
Вот только ума не приложу, кому это может быть надо...

**stored_attributes**   # см. http://sphinxsearch.com/docs/2.0.4/confgroup-source.html, разделы 11.1.17-11.1.25, кроме 11.1.23

Список полей, которые необходимо проиндексировать как stored attributes.
Данный список может быть полезен, если требуется индексировать текстовое поле как атрибут документа, но не как full-text.
Этот список не требуется дублировать в `included_fields` - его содержимое автоматически будет туда добавлено.

**stored_fields**       # см. http://sphinxsearch.com/docs/2.0.4/conf-sql-field-string.html

Список текстовых полей, которые необходимо проиндексировать и как атрибуты, и как full-text.
Этот список не требуется дублировать в `included_fields` - его содержимое автоматически будет туда добавлено.

**related_fields**

Список полей, связанных с другими моделями. Должен содержать только отношения один-к-одному (OneToOneField) и один-ко-многим (ForeignKey)
В индекс помещаются ключи соответствующих объектов связанных моделей в виде stored-атрибутов.
По этим объектам можно фильтровать выборку (см. примеры ниже)

**mva_fields**      # см. http://sphinxsearch.com/docs/2.0.4/conf-sql-attr-multi.html

Список MVA-атрибутов.

**WARNING**
Будьте осторожны в использовании stored-атрибутов, особенно текстовых. Все атрибуты sphinx загружает в память, поэтому поля, содержащие много текста, могут съесть всю память Вашего сервера.
Заполняйте `included_fields` только необходимыми полями, но не оставляйте его пустым.
Я Вас предупредил!


Использование
-------------

**Note**: все примеры будут даны для указанной выше модели::

    queryset = MyModel.my_search.query('query')

    # простые выборки
    results1 = queryset.order_by('@weight', '@id', 'uint')
    results2 = queryset.filter(uint=[1,2,5,7,10])
    results3 = queryset.filter(bool=False)
    results4 = queryset.exclude(uint=5)[0:10]
    results5 = queryset.count()

    # примеры посложнее

    # ForeignKey или OneToOneField
    related_item = RelatedModel.objects.get(pk=1)
    related_queryset = RelatedModel.objects.get(pk__in=[1,2])

    # фильтр по идентификатору объекта из связанной модели
    results6 = queryset.filter(related_field=100)
    # или можно передать в качестве аргумента сам объект
    results7 = queryset.filter(related_field=related_item)

    # фильтр по списку идентификаторов нескольких объектов из связанной модели
    results8 = queryset.filter(related_field__in=[4,5,6])
    # или QuerySet
    results9 = queryset.filter(related_field__in=related_queryset)

    # однако, можно и так
    results10 = queryset.filter(related_field__in=related_item)


    # ManyToManyField
    m2m_item = M2MModel.objects.get(pk=1)
    m2m_queryset = M2MModel.objects.filter(pk__in=[1,2,3])

    # аналогично для MVA-атрибутов
    results11 = queryset.filter(m2m_field=23)
    results12 = queryset.filter(m2m_field=m2m_item)
    results13 = queryset.filter(m2m_field__in=[2,6,9])
    results14 = queryset.filter(m2m_field__in=m2m_queryset)
    results15 = queryset.filter(m2m_field__in=m2m_item)


    # as of 2.0 you can now access an attribute to get the weight and similar arguments
    for result in results1:
        print result, result._sphinx
    # you can also access a similar set of meta data on the queryset itself (once it's been sliced or executed in any way)
    print results1._sphinx

    # as of 3.0 you can specify 'options', which are described in detail below.


Some additional methods:
* count()
* extra() (passed to the queryset)
* all() (does nothing)
* select_related() (passed to the queryset)
* group_by(field, field, field)
* set_options(index='', weights={}, weights=[], mode='SPH_MODE_*', rankmode='SPH_MATCH_*', passages=True, passages_opts={})

The django-sphinx layer also supports some basic querying over multiple indexes. To use this you first need to understand the rules of a UNION. As of djangosphinx 3.0, it is no longer necessary to store a "content_type" attribute in your index, as it is encoded in the 32-bit doc_id along with object pk. Additionally, ContentType queries are stored in cache under the format "djangosphinx_content_type_xxx", where xxx is the pk of the ContentType object. In general, you needn't bother with these cache values - just be aware if you're trying to set a cache key for an unrelated object/value to something of this format, you're going to get some strange results.

You can then do something like this::

    from djangosphinx.models import SphinxSearch

    SphinxSearch('index1 index2 index3').query('hello')

This will return a list of all matches, ordered by weight, from all indexes. This performs one SQL query per index with matches in it, as Django's ORM does not support SQL UNION.

Be aware that making queries in this manner has a couple of gotchas. First, you must have globally unique document IDs. This is largely taken care of internally by djangosphinx 3.0 with SQL bitwise arithmetic, but just be aware of this inherent limitation of SphinxClient's Query() function when used outside of djangosphinx.

Second, you must have "homogeneous" index schemas. What this means is that the "fields" (not attributes) you perform a search on must have the same name across indexes. If these requirement is not met, in the above "SphinxSearch('index1 index2 index3').query('hello')" example the searchable field AND attribute values of the last index (in this case 'index3') will be used for all results, even those from 'index1' and 'index2'. The result is that weight, searched field, and attribute values will be completely wrong for all results that aren't from 'index3'. In all likelihood, your attributes will be empty, weight will be "100", and you'll just get back document IDs from Sphinx.

If you intend to use the built in djangosphinx.shortcuts.sphinx_query() function, be aware that it is using this Query() function to perform searches across all of the models that have a SphinxSearch() manager. The best way to avoid this issue if you've got a simple schema (i.e. you're searching only one field per index) is to pick an arbitrary name like "text", and in your sql_query, change the field to be searched on to have the name text. Example: "SELECT ..., tablename.name as 'text'"". Do this for every index, and you can perform Query() searches across them. For anything more complex, you're going to have to be creative.

Config Generation
-----------------

django-sphinx now includes a tool to create sample configuration for your models. It will generate both a source, and index configuration for a model class. You will still need to manually tweak the output, and insert it into your configuration, but it should aid in initial setup.

To use it::


    from djangosphinx.utils import *

    from myproject.myapp.models import MyModel

    output = generate_config_for_model(MyModel)

    print output

If you have multiple models which you wish to use the UNION searching::

    model_classes = (ModelOne, ModelTwoWhichResemblesModelOne)

    output = generate_config_for_models(model_classes)

You can also now output configuration from the command line::

    ./manage.py generate_sphinx_config <appname>

This will loop through all models in <appname> and attempt to find any with a SphinxSearch instance that is using the default index name (db_table).

Using the Config Generator
--------------------------

**WARNING**
The same caveats that pertain to "stored_string_fields" apply here. Be careful about storing too much information in this manner. Attributes are meant mainly for filtering and sorting, not storage. Add too much baggage to your documents and you can make Sphinx crawl. You've been warned - again.

*New in 2.2*

django-sphinx now includes a simply python script to generate a config using your default template renderer. By default, we mean that if `coffin` is included in your INSTALLED_APPS, it uses it, otherwise it uses Django.

Two variables directly relate to the config generation:

    # The base path for sphinx files. Sub directories will include data, log, and run.
    SPHINX_ROOT = '/var/sphinx-search/'

    # Optional, defaults to 'conf/sphinx.html'. This should be configuration template.
    # See the included templates/sphinx.conf for an example.
    SPHINX_CONFIG_TEMPLATE = 'conf/sphinx.html'

Once done, your config can be passed via any sphinx command like so:

    # Index your stuff
    DJANGO_SETTINGS_MODULE=myproject.settings indexer --config /path/to/djangosphinx/config.py --all --rotate

    # Start the daemon
    DJANGO_SETTINGS_MODULE=myproject.settings searchd --config /path/to/djangosphinx/config.py

    # Query the daemon
    DJANGO_SETTINGS_MODULE=myproject.settings search --config /path/to/djangosphinx/config.py my query

    # Kill the daemon
    kill -9 $(cat /var/sphinx-search/run/searchd.pid)

For now, we recommend you setup some basic bash aliases or scripts to deal with this. This is just the first step in embedded config generation, so stay tuned!

* Note: Make sure your PYTHON_PATH is setup properly!

Using Sphinx in Admin
---------------------

Sphinx includes it's own ModelAdmin class to allow you to use it with Django's built-in admin app.

To use it, see the following example::

    from djangosphinx.admin import SphinxModelAdmin

    class MyAdmin(SphinxModelAdmin):
        index = 'my_index_name' # defaults to Model._meta.db_table
        weights = {'field': 100}

Limitations? You know it.

- Only shows your max sphinx results (defaults to 1000)
- Filters currently don't work.
- This is a huge hack, so it may or may not continue working when Django updates.

Frequent Questions
------------------

*How do I run multiple copies of Sphinx using django-sphinx?*

The easiest way is to just run a different SPHINX_PORT setting in your settings.py. If you are using the above config generation, just modify the PORT, and start up the daemon

Resources
---------

* http://groups.google.com/group/django-sphinx
* http://www.davidcramer.net/code/65/setting-up-django-with-sphinx.html
