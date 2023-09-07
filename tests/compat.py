# coding=utf-8

import gzip
from contextlib import nullcontext, suppress
from tempfile import TemporaryDirectory
from unittest import mock


def gzip_decompress(data):
    return gzip.decompress(data)


try:
    from contextvars import copy_context
except ImportError:
    copy_context = None


__all__ = [
    "gzip_decompress",
    "mock",
    "nullcontext",
    "suppress",
    "TemporaryDirectory",
    "copy_context",
]
