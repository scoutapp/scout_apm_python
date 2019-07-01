# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals


def octal(value):
    """
    Takes an integer or a string containing an integer and returns the octal
    value. Raises a ValueError if the value cannot be converted to octal.
    """
    return int("{}".format(value), 8)
