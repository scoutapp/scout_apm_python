import scout_apm_django
import scout_apm_django.apps


def test_default_django_config():
    assert(scout_apm_django.default_app_config == 'scout_apm_django.apps.ScoutApmDjangoConfig')


def test_apps():
    assert(scout_apm_django.apps.ScoutApmDjangoConfig.name == 'scout_apm')
