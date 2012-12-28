# coding: utf-8

import itertools
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import models


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

        found = 0
        for model in model_classes:
            if getattr(model._meta, 'proxy', False) or getattr(model._meta, 'abstract', False):
                continue
            indexes = getattr(model, '__sphinx_indexes__', [])

            for index in indexes:
                found += 1
                print generate_config_for_model(model, index)

        if found == 0:
            raise CommandError("Unable to find any models in application which use standard SphinxSearch configuration.")

        print generate_sphinx_config()
