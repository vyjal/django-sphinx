This is a layer that functions much like the Django ORM does except it works on top of the Sphinx (http://www.sphinxsearch.com) full-text search engine.

Please Note: You will need to create your own sphinx indexes and install sphinx on your server to use this app.

*There will no longer be release packages available. Please use SVN to checkout the latest trunk version, as it should always be stable and current.*

Installation
------------

*Note:* You will need to install the `sphinxapi.py` package into your Python Path. In previous version of djangosphinx, Sphinx Python APIs were provided in the djangosphinx package. This has been dropped in favor of versioned PIP packages for each Sphinx API that is available, or a manual installation of the "sphinxapi.py" file in your Python path. If you prefer the manual method, and are using Virtualenv, you can simply create a directory called "sphinxapi" in your site-packages and drop the (included with your download of the Sphinx source) sphinxapi.py file in inside. Also, create an empty __init__.py file in the "sphinxapi" directory so Python knows that the API is an importable package.


Usage
-----

The following is some example usage::

	from djangosphinx.models import SphinxSearch

	class RelatedModel(models.Model)
	    name = models.CharField(max_length = 100)

	class M2MModel(models.Model)
	    name = models.CharField(max_length = 100)
	
	class MyModel(models.Model):

	    related_field = models.ForeignKey(RelatedModel)
	    m2m_field = models.ManyToManyField(M2MModel)
	    bool_field = models.BooleanField()

	    search = SphinxSearch() # optional: defaults to db_table
	    # If your index name does not match MyModel._meta.db_table
	    # Note: You can only generate automatic configurations from the ./manage.py script
	    # if your index name matches.
	    search = SphinxSearch('index_name')

	    # Or maybe we want to be more.. specific
	    searchdelta = SphinxSearch(
	        index='index_name delta_name',
	        weights={
	            'name': 100,
	            'description': 10,
	            'tags': 80,
	        },
	        mode='SPH_MATCH_ALL',
	        rankmode='SPH_RANK_NONE',
	    )

	    # все возможные способы указания полей
	    mysearch = SphinxSearch(
	        'included_fields': [    # список индексируемых полей
	            'field1',           # для нестроковых полей stored-атрибуты
	            'field2',           # создаются автоматически
	            'field3',           # за исключением первичного ключа (primary_key)
	        ],
	        'excluded_fields': [    # если список included_fields не заполнен, по-умолчанию индексируются все поля модели
	            'field4',           # укажите названия полей, которые нужно исключить из индекса, в этом списке
	            'field5',           # ВАЖНО: этот список имеет приоритет над included_fields, и поля, указанные в нём
	                                # будут удалены из included_fields
	        ],
	        'stored_attributes': [  # если нужно сделать stored строковые поля,
                'string_field1',    # их следует указывать в данном списке
                'field1',           # если поле не является строковым и уже указано в included_fields
                'field2',           # оно будет проигнорировано. если его нет в included_fields, оно будет туда
                                    # добавлено
            ],
            'related_fields': [     # в этом списке необходимо указать список полей типа FK и One2One
                'related_field',    # это позволит фильтровать по списку объектов из связанной таблице (см. ниже)
            ],
            'mva_fields': {         # Список MVA атрибутов (поля M2M)
                'sections',
                'subsections',
            },
	    )

	queryset = MyModel.search.query('query')
	results1 = queryset.order_by('@weight', '@id', 'my_attribute')
	results2 = queryset.filter(my_attribute=5)
	results3 = queryset.filter(my_other_attribute=[5, 3,4])
	results4 = queryset.exclude(my_attribute=5)[0:10]
	results5 = queryset.count()

    # ForeignKey, OneToOneField, ManyToManyField можно искать как по списку идентификаторов соответствующих моделей,
    # так и по обекту или QuerySet

	# ForeignKey or OneToOneField lookup
	related_model_item = RelatedModel.objects.get(pk=1)
	related_model_items = RelatedModel.objects.get(pk__in=[1,2])

	results6 = queryset.filter(related_field=related_model_item)
	results7 = queryset.filter(related_field=100)
	results8 = queryset.filter(related_field__in=related_model_items)
	results9 = queryset.filter(related_field__in=[4,5,6])

	# ManyToManyField lookup
	m2m_related_model_item = M2MModel.objects.get(pk=1)
	m2m_related_model_items = M2MModel.objects.filter(pk__in=[1,2,3])

	results10 = queryset.filter(m2m_field=m2m_related_model_item)
	results11 = queryset.filter(m2m_field=23)
	results12 = queryset.filter(m2m_field__in=m2m_related_model_items)
	results13 = queryset.filter(m2m_field__in=[2,6,9])

	# Other fields lookup
	result14 = queryset.filter(bool_field=False)

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
* New in 3.0*
A new "options" key has been added to SphinxSearch. These new options allow you to specify various aspects of your generated configuration file.

Allowed keys are:
"excluded_fields" 
"included_fields"
"stored_string_attributes"
"related_fields"
"related_stored_attributes"

"excluded_fields", "included_fields", and "stored_string_attributes"
--------------------------------------------------------------------

The "excluded_fields" and "included_fields" keys are mutually exclusive, meaning the following SphinxSearch configuration will throw a command error when you try to execute "generate_sphinx_config --all":

search = SphinxSearch(
	options = {
		'excluded_fields': ['name', 'address'],
		'included_fields': ['phone', 'address']
	}
)

Either whitelist fields you want, or blacklist fields you don't - not both. By default, leaving these options out will result in the configuration generator making all model fields available for full-text indexing, if those fields are the right type (string).

The "stored_string_attributes" option (Sphinx v1.10beta or higher) allows you to specify string fields of your Django model to be stored inside the document for each result of that model type. This can result in a non-trivial increase in the size of your index, so be judicious about what size strings you're putting in as string attributes. If you put in models.TextField fields as string attributes, be prepared for many orders of magnitude higher index times and index size. You've been warned!


"related_fields" and "related_stored_attributes"
------------------------------------------------

These two options allow the configuration generator to look ONE-level deep through one-to-many (ForeignKey) relationships on the Django model for your index. ManyToMany relations are not supported - you'll have to write that configuration yourself. In practice, a field specified in "related_stored_attributes" option is dependent on the presence of that field name in the "related_fields" option. An example:

search = SphinxSearch(
	options = {
		'related_fields': ['car.make', 'car.model'],
		'related_stored_attributes': ['car.model']
	}
)

In this example, 'car' is the name of the ForeignKey field on the model for this index. Any fields you specify in 'related_fields' will be placed in the main Sphinx sql_query, and therefore eligible for full-text searching (if it's the right field type). Any fields in 'related_fields' that are also present in 'related_stored_attributes' will be stored in each Sphinx document.

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
