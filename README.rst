Это прослойка, подобная Django ORM, работающая поверх Sphinx full-text поискового движка (http://www.sphinxsearch.com)

=========
Установка
=========

*В данный момент нет пакетов, доступных для установки. Используйте Git, чтобы скачать актуальную версию пакета.*
**Note**: для пользователей Gentoo есть ebuild: https://github.com/Yuego/overlay/tree/master/dev-python/django-sphinx

Зависимости
===========

Необходимы следующие пакеты:

- django
- PyMySQL
- sphinx, собранный с поддержкой 64-битных идентификаторов


=========
Настройка
=========
  ``pip install django PyMySQL six``
  ``pip install git+git://github.com/projektai/django-sphinx``

Настройка sphinx
=================

SPHINX_LOG_PATH
---------------
**по-умолчанию:** ``/var/log/sphinx/``

Путь к каталогу с логами Sphinx.

SPHINX_DATA_PATH
----------------
**по-умолчанию:** ``/var/data/sphinx/``

Путь к каталогу, где Sphinx будет хранить индексы

SPHINX_PID_FILE
---------------
**по-умолчанию:** ``/var/run/searchd.pid``

Файл с PID демона sphinx

SPHINX_HOST
-----------
**по-умолчанию:** ``127.0.0.1``

Интерфейс, который будет слушать сфинкс.
В данный момент доступно подключение только через TCP/IP, хотя Sphinx поддерживает сокеты

SPHINX_PORT
-----------
**по-умолчанию:** ``9306``

Порт, который будет слушать сфинкс на указанном выше интерфейсе.


SPHINX_MAX_MATCHES
------------------
**по-умолчанию:** ``1000``

Максимальное количество документов, которое сможет держать в оперативной памяти Sphinx. А так же максимальное количество возвращаемых результатов поиска.
Глобальный параметр, который можно переопределить из кода только в **меньшую** сторону.

DOCUMENT_ID_SHIFT
-----------------
**по-умолчанию:** ``52``

Указывает, сколько бит из доступных 64 в идентификаторе документа будут содержать идентификатор объекта модели. Оставшиеся биты используются для хранения идентификатора объекта ContentType.
Для значения 52 в индексе возможно хранить до 4095 ContentType по 4503599627370495 объектов на каждый из них.

Настройка поиска
================

SPHINX_SNIPPETS
---------------
**по-умолчанию:** ``False``

Создавать сниппеты для всех моделей по-умолчанию или нет. Применяется ко всем моделям глобально. Может быть переопределено для каждой модели в индивидуальном порядке.

SPHINX_SNIPPETS_OPTS
--------------------
**по-умолчанию:** ``{}`` (пустой dict())

Глобальные параметры выделения сниппетов в тексте. Могут быть переопределены в дальнейшем.
Если не задано, используются значения Sphinx по-умолчанию, за исключением параметра ``html_strip_mode``, который установлен в значение **strip** в конфигурации Sphinx.
Доступные для конфигурирования параметры и их значения по-умолчанию см. в `документации Sphinx <http://sphinxsearch.com/docs/2.0.4/api-func-buildexcerpts.html>`_.

SPHINX_QUERY_OPTIONS
--------------------
**по-умолчанию:** ``dict(ranker='bm25')``


Глобальные параметры запросов к индексу Sphinx.
Если не указано или пусто, используются параметры по-умолчанию самого Sphinx.
Если параметр ``ranker`` не задан явно, используется значение **bm25**. Может быть переопределён.
Доступные для конфигурирования параметры и их значения по-умолчанию см. `документацию Sphinx <http://sphinxsearch.com/docs/2.0.4/sphinxql-select.html>`_.

SPHINX_QUERY_LIMIT
------------------
**по-умолчанию:** ``20``

Лимит количества результатов поиска по-умолчанию.

Дополнительные настройки
========================

-//-

=================
Настройка моделей
=================

**Note**: для каждой модели можно указать только одно поле типа SphinxSearch!::

    # Пример настройки и использования:

    from django.db import models
    from djangosphinx.models import SphinxSearch

    class RelatedModel(models.Model)
        name = models.CharField(max_length = 100)

    class City(models.Model)
        title = models.CharField(max_length = 100)

    class M2MModel(models.Model)
        name = models.CharField(max_length = 100)

    class MyModel(models.Model):

        related_field = models.ForeignKey(RelatedModel)
        city = models.OneToOneField(City)
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

        # выбор полей для индексации
        my_search = SphinxSearch(
            options = {
                'realtime': True,

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

                    'city__title',
                ],
                'mva_fields': {
                    'm2m_field',
                },
            },
            query_options = {
                ranker = 'proximity_bm25',
                reverse_scan = True,
            },
            snippets = True,
            snippets_options = {
                before_match = '<span class="snippet">',
                after_match = '</span>',
            }
            maxmatches = 2000,
            limit = 100,
        )


Аргументы SphinxSearch
======================

options
-------

Словарь, который может включать в себя следующие элементы:

realtime
^^^^^^^^
Включает использование `RealTime-индексов <http://sphinxsearch.com/docs/manual-2.0.6.html#rt-indexes>`_. Если включен, доступны методы для работы с RT-индексами.

included_fields
^^^^^^^^^^^^^^^

Список полей, которые необходимо включить в индекс. Все текстовые поля будут проиндексированы как full-text (но не как атрибуты). Все нетекстовые поля (за некоторыми исключениями, см. ниже) будут проиндексированы как stored attributes.

excluded_fields
^^^^^^^^^^^^^^^

Список исключенных из индекса полей. Может быть использован, чтобы внести в индекс все поля модели, за исключением указанных здесь.
Имеет приоритет над `included_fields`, `stored_attributes`, `stored_fields`. Все поля, перечисленные в `excluded_fields`, будут удалены из этих списков.
Вот только ума не приложу, кому это может быть надо...

stored_attributes
^^^^^^^^^^^^^^^^^
`см. документацию <http://sphinxsearch.com/docs/2.0.4/confgroup-source.html>`_, разделы 11.1.17-11.1.25, кроме 11.1.23

Список полей, которые необходимо проиндексировать как stored attributes.
Данный список может быть полезен, если требуется индексировать текстовое поле как атрибут документа, но не как full-text.
Этот список не требуется дублировать в `included_fields` - его содержимое автоматически будет туда добавлено.

stored_fields
^^^^^^^^^^^^^
`см. документацию <http://sphinxsearch.com/docs/2.0.4/conf-sql-field-string.html>`_

Список текстовых полей, которые необходимо проиндексировать и как атрибуты, и как full-text.
Этот список не требуется дублировать в `included_fields` - его содержимое автоматически будет туда добавлено.

related_fields
^^^^^^^^^^^^^^

Список полей, связанных с другими моделями. Должен содержать только отношения один-к-одному (OneToOneField) и один-ко-многим (ForeignKey)
В индекс помещаются ключи соответствующих объектов связанных моделей в виде stored-атрибутов.
По этим объектам можно фильтровать выборку (см. примеры ниже)

Кроме того, если данные разбиты на несколько таблиц, связанных отношением один-к-одному, можно поместить в индекс так же поля связанной таблицы. Для этого нужно добавить список полей по принципу, аналогичному тому, что используется в Django ORM:

*Пример*
Если в модели имеется поле city, связанное с моделью City и необходимо поместить в индекс название города (поле title), то в список нужно добавить строку 'city__title'.

mva_fields
^^^^^^^^^^
`см. документацию <http://sphinxsearch.com/docs/2.0.4/conf-sql-attr-multi.html>`_

Список MVA-атрибутов.

**WARNING**
Будьте осторожны в использовании stored-атрибутов, особенно текстовых. Все атрибуты sphinx загружает в память, поэтому поля, содержащие много текста, могут съесть всю память Вашего сервера.
Заполняйте `included_fields` только необходимыми полями, но не оставляйте его пустым.
Я Вас предупредил!

query_options
-------------

Словарь, включающий в себя параметры поисковых запросов к Sphinx. Аналогичен ``SPHINX_QUERY_OPTIONS``, но распространяется только на данную модель.

snippets
--------

Включает и отключает автоматическую генерацию сниппетов.

snippets_options
----------------

Параметры генерации сниппетов. Аналогичен ``SPHINX_SNIPPETS_OPTS``, но распространяется только на данную модель.

maxmatches
----------

Максимальное количество результатов, которое может вернуть Sphinx. Аналогичен ``SPHINX_MAX_MATCHES``, но распространяется только на данную модель.
**Note** Может быть не больше ``SPHINX_MAX_MATCHES``

limit
-----

Лимит по-умолчанию на запрос. Аналогичен ``SPHINX_QUERY_LIMIT``, но распространяется только на данную модель.
**Note** Может быть не больше ``SPHINX_MAX_MATCHES``

=============
Использование
=============


Поиск и фильтрация выборки
==========================

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



Методы поиска и фильтрации
--------------------------
*Note*: все перечисленные методы возвращают объект и позволяют создавать цепочки: qs = SphinxQuerySet().query('query').group_by('field')


add_index
^^^^^^^^^

Принимает единственный аргумент - список индексов. Аналогично `index` в `__init__`.
Добавляет индексы в список.
**Note** Доступен только, если SphinxQuerySet не привязан к модели.

remove_index
^^^^^^^^^^^^

Аналогично `add_index`. Удаляет переданные индексы из списка.
**Note** Доступен только, если SphinxQuerySet не привязан к модели.

query
^^^^^

Принимает строку - поисковый запрос.

filter
^^^^^^

Аналогичен методу `filter` Django ORM.
Досупны операции: `gt`, `gte`, `lt`, `lte`, `in`, `range` и `=`::

    qs = qs.filter(field=value)
    qs = qs.filter(field__gt=value)


exclude
^^^^^^^

Аналогичен `filter`, но исключает указанные значения из выборки.
Поддерживает те же операции, за исключением `range` (SphinxQL не поддерживает NOT field BETWEEN val1 AND val2)

fields
^^^^^^

По умолчанию Sphinx возвращает все поля индекса.
Данный метод принимает имена полей, которые должны быть получены. Значения в дальнейшем можно получить через атрибут `sphinx` объекта.

Кроме того можно создавать вычисляемые выражения (см. http://sphinxsearch.com/docs/2.0.6/sphinxql-select.html)
Для этого необходимо передать методу именованные параметры, где имя параметра - alias выражения, а значение - строка с выражением::

    qs = qs.fields(expr1='group_id*123+456')

*Note*: по-умолчанию поле `weight` теперь не возвращается. Чтобы его получить, нужно явно "попросить об этом" Sphinx::

    qs = qs.fields(weight='WEIGHT()')

options
^^^^^^^

Позволяет задать новые `SPHINX_QUERY_OPTIONS` путём передачи их в качестве именованных параметров данному методу.

snippets
^^^^^^^^

Принимает один необязательный позиционный атрибут и несколько словарных

*snippets* - булев параметр. Включает или отключает создание сниппетов. (если метод вызван без параметров, создание снипеетов будет включено)

Именованные параметры см выше `SPHINX_SNIPPETS_OPTS`

group_by
^^^^^^^^

Принимает один параметр - имя поля, по которому нужно группировать результаты поиска (в данный момент SpinxQL 2.0.4 не позволяет группировать более чем по одному полю)

order_by
^^^^^^^^

Принимает названия полей, по которым выборка должна быть отсортирована. Аналогично одноимённому методу Django ORM.

group_order_by
^^^^^^^^^^^^^^

Специфический для SphinxQL метод, позволяющий сортировать результаты внутри группы. Аналогично `order_by` принимает список полей.

all
^^^^

Устанавливает лимит выдачи максимально возможным (см. `SPHINX_MAX_MATCHES`)

none
^^^^

Возвращяет пустой QuerySet

reset
^^^^^

Сбрасывает все параметры к значениям по-умолчанию (или установленным в конфигурации)

Методы работы с RT-индексами
----------------------------

create
^^^^^^^

`Создаёт документы в индексе <http://sphinxsearch.com/docs/manual-2.0.6.html#sphinxql-insert>`_ на основе переданных объектов, если для SphinxQuerySet задана модель.
Принимает в качестве аргумента объект этой модели или QuerySet, содержащий несколько таких объектов.
Если индекс уже содержит документ, изменения в него не вносятся. Чтобы принудительно обновить документы в индексе, нужно передать в метод второй параметр:

*force_update=True*

**Note**
Работа с непривязанными к модели RT-индексами в данный момент не поддерживается.

update
^^^^^^^

Пока не реализован

delete
^^^^^^^

`Удаляет из индекса документы <http://sphinxsearch.com/docs/manual-2.0.6.html#sphinxql-delete>`_, отобранные с помощью метода `filter`.
Sphinx в данный момент поддерживает только фильтрацию вида {id = value | id IN (val1 [, val2 [, ...]])}


Дополнительные методы
---------------------

keywords
^^^^^^^^

Возвращает `список ключевых слов <http://sphinxsearch.com/docs/manual-2.0.6.html#sphinxql-call-keywords>`_ из переданного первым аргументом текста согласно настройкам индекса, переданного вторым аргументом.
Третий аргумент опционален - позволяет включить так же статистику по ключевым словам в список.









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
