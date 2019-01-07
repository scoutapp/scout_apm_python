from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.core.util import octal


def test_octal_with_valid_integer():
    assert 0o700 == octal(700)


def test_octal_with_valid_string():
    assert 0o700 == octal("700")


def test_octal_raises_valueerror_on_invalid_value():
    try:
        octal("THIS IS INVALID")
    except ValueError:
        pass
