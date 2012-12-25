from django.core.management.base import BaseCommand, CommandError
from django.db import models
import itertools
from optparse import make_option
from sphinxapi import sphinxapi
from django.conf import settings

from djangosphinx.models import SphinxModelManager


class Command(BaseCommand):
    help = "Prints generic configuration for any models which use a standard SphinxSearch manager."
    option_list = BaseCommand.option_list + (
        make_option('--all', action='store_true', default=False, dest='find_all', help='generate config for all models in all INSTALLED_APPS'),
    )

    output_transaction = True

    def handle(self, *args, **options):
        from djangosphinx.utils.config import generate_config_for_model, generate_sphinx_config

        # warn the user to remove SPHINX_API_VERSION, because we no longer pull from bundled apis
        if getattr(settings, 'SPHINX_API_VERSION', None) is not None:
            raise CommandError("SPHINX_API_VERSION is deprecated, please use pip for installing the appropriate Sphinx API.")

        model_classes = []
        if options['find_all']:
            model_classes = itertools.chain(*(models.get_models(app) for app in models.get_apps()))
        elif len(args):
            app_list = [models.get_app(app_label) for app_label in args]
            for app in app_list:
                model_classes.extend([getattr(app, n) for n in dir(app) if hasattr(getattr(app, n), '_meta')])
        else:
            raise CommandError("You must specify an app name or use --all")

        unsafe_options = []

        def _optionsAreSafe(options):
            try:
                options['excluded_fields'] and options['included_fields']
                unsafe_options.append(['excluded_fields', 'included_fields'])
                return False
            except:
                return True

        def _clobberExcludedFieldsFromAttrs(excluded_fields, stored_string_attrs):
            for field in excluded_fields:
                if field in stored_string_attrs:
                    stored_string_attrs.pop(stored_string_attrs.index(field))
            return stored_string_attrs

        found = 0
        for model in model_classes:
            if getattr(model._meta, 'proxy', False) or getattr(model._meta, 'abstract', False):
                continue
            indexes = getattr(model, '__sphinx_indexes__', [])
            opts = getattr(model, '__sphinx_options__', None)

            # excluded_fields takes precedence over manual string stored field declarations!
            try:
                excluded_fields = opts['excluded_fields']
                try:
                    stored_string_attrs = opts['stored_string_attributes']
                    if sphinxapi.VER_COMMAND_SEARCH >= 0x117:
                        opts['stored_string_attributes'] = _clobberExcludedFieldsFromAttrs(excluded_fields, opts)
                    else:
                        raise CommandError("Stored string attributes require a Sphinx API for version 1.10beta or above.")
                except:
                    pass
            except:
                pass

            # related_stored_attributes have to be in related_fields in order to be used
            try:
                related_fields = opts['related_fields']
            except:
                related_fields = None

            if related_fields is not None:
                try:
                    related_stored_attributes = opts['related_stored_attributes']
                except:
                    related_stored_attributes = None
                if related_stored_attributes is not None:
                    for attribute in related_stored_attributes:
                        if attribute not in related_fields:
                            raise CommandError(
                                "related_stored_attribute '%s' on model '%s' must also exist in the related_fields option." % (attribute, model)
                            )

            if _optionsAreSafe(opts):
                for index in indexes:
                    found += 1
                    print generate_config_for_model(model, index)
            else:
                raise CommandError("Unsafe options for model '%s': %s" % (model.__name__, [u for u in unsafe_options[0]]))
        if found == 0:
            raise CommandError("Unable to find any models in application which use standard SphinxSearch configuration.")

        print generate_sphinx_config()
        #return u'\n'.join(sql_create(app, self.style)).encode('utf-8')
