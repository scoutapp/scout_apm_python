# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import django

if django.VERSION < (3, 2, 0):
    # Only define default_app_config when using a version earlier than 3.2
    default_app_config = "scout_apm.django.apps.ScoutApmDjangoConfig"
