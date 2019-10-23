# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.asgi import asgi_importable


async def test_asgi_importable():
    assert asgi_importable()
