import warnings

import django
from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import ProgrammingError

from tenant_schemas.utils import get_public_schema_name, get_tenant_model


class TenantSchemasConfig(AppConfig):
    name = 'tenant_schemas'
    verbose_name = 'Tenant Schemas'

    recommended_config = """
    Warning: You should put 'tenant_schemas' at the end of
    INSTALLED_APPS like this: INSTALLED_APPS = TENANT_APPS + SHARED_APPS +
    ('tenant_schemas',) This is necessary to overwrite built-in django
    management commands with their schema-aware implementations.
    """

    def ready(self):
        # Make a bunch of tests for configuration recommendations
        # These are best practices basically, to avoid hard to find bugs,
        # unexpected behaviour
        if not hasattr(settings, 'TENANT_APPS'):
            print ImproperlyConfigured('TENANT_APPS setting not set')

        if not settings.TENANT_APPS:
            raise ImproperlyConfigured("TENANT_APPS is empty. Maybe you don't"
                                       " need this app?")

        if settings.INSTALLED_APPS[-1] != 'tenant_schemas':
            print self.recommended_config

        if hasattr(settings, 'PG_EXTRA_SEARCH_PATHS'):
            if get_public_schema_name() in settings.PG_EXTRA_SEARCH_PATHS:
                raise ImproperlyConfigured(
                    "%s can not be included on PG_EXTRA_SEARCH_PATHS." %
                    get_public_schema_name())

            # make sure no tenant schema is in settings.PG_EXTRA_SEARCH_PATHS
            # and if tenants table has not been synched yet then provide a
            # helpful warning
            TenantModel = get_tenant_model()
            try:
                schemas = list(TenantModel.objects.all().values_list(
                    'schema_name', flat=True))
            except ProgrammingError, e:
                table = TenantModel._meta.db_table
                if 'relation "{}" does not exist'.format(table) not in e:
                    warnings.warn(self.get_missing_tenants_table_message())

                schemas = []
            invalid_schemas = set(settings.PG_EXTRA_SEARCH_PATHS).intersection(
                schemas)
            if invalid_schemas:
                raise ImproperlyConfigured(
                    "Do not include tenant schemas (%s) on "
                    "PG_EXTRA_SEARCH_PATHS." % list(invalid_schemas))

    def get_missing_tenants_table_message(self):
        if django.VERSION >= (1, 7, 0):
            return ("""
=======================================================================
    Looks like the tenants table has not been synched to the DB yet.
    Run `python manage.py migrate_schemas --shared` to do so.
=======================================================================""")
        else:
            return ("""
=======================================================================
    Looks like the tenants table has not been synched to the DB yet.
    Run `python manage.py sync_schemas --shared` and `python manage.py migrate_schemas --shared` to do so.
=======================================================================""")
