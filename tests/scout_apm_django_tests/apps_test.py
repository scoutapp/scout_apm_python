import scout_apm.django
import scout_apm.django.apps


def test_default_django_config():
    assert(scout_apm.django.default_app_config == 'scout_apm.django.apps.ScoutApmDjangoConfig')


def test_apps():
    assert(scout_apm.django.apps.ScoutApmDjangoConfig.name == 'scout_apm')
