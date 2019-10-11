# flake8: noqa
from __future__ import absolute_import, division, print_function, unicode_literals

# Originally taken from https://pypi.python.org/pypi/ProxyTypes
# Inlined due to python3 issues with setup.py


class AbstractProxy(object):
    """Delegates all operations (except ``.__subject__``) to another object"""

    __slots__ = ()

    def __call__(self, *args, **kw):
        return self.__subject__(*args, **kw)

    def __getattribute__(self, attr, oga=object.__getattribute__):
        subject = oga(self, "__subject__")
        if attr == "__subject__":
            return subject
        return getattr(subject, attr)

    def __setattr__(self, attr, val, osa=object.__setattr__):
        if attr == "__subject__":
            osa(self, attr, val)
        else:
            setattr(self.__subject__, attr, val)

    def __delattr__(self, attr, oda=object.__delattr__):
        if attr == "__subject__":
            oda(self, attr)
        else:
            delattr(self.__subject__, attr)

    def __nonzero__(self):
        return bool(self.__subject__)

    def __getitem__(self, arg):
        return self.__subject__[arg]

    def __setitem__(self, arg, val):
        self.__subject__[arg] = val

    def __delitem__(self, arg):
        del self.__subject__[arg]

    def __getslice__(self, i, j):
        return self.__subject__[i:j]

    def __setslice__(self, i, j, val):
        self.__subject__[i:j] = val

    def __delslice__(self, i, j):
        del self.__subject__[i:j]

    def __contains__(self, ob):
        return ob in self.__subject__

    for name in "repr str hash len abs complex int long float iter oct hex".split():
        exec("def __%s__(self): return %s(self.__subject__)" % (name, name))

    for name in "cmp", "coerce", "divmod":
        exec("def __%s__(self,ob): return %s(self.__subject__,ob)" % (name, name))

    for name, op in [
        ("lt", "<"),
        ("gt", ">"),
        ("le", "<="),
        ("ge", ">="),
        ("eq", "=="),
        ("ne", "!="),
    ]:
        exec("def __%s__(self,ob): return self.__subject__ %s ob" % (name, op))

    for name, op in [("neg", "-"), ("pos", "+"), ("invert", "~")]:
        exec("def __%s__(self): return %s self.__subject__" % (name, op))

    for name, op in [
        ("or", "|"),
        ("and", "&"),
        ("xor", "^"),
        ("lshift", "<<"),
        ("rshift", ">>"),
        ("add", "+"),
        ("sub", "-"),
        ("mul", "*"),
        ("div", "/"),
        ("mod", "%"),
        ("truediv", "/"),
        ("floordiv", "//"),
    ]:
        exec(
            (
                "def __%(name)s__(self,ob):\n"
                "    return self.__subject__ %(op)s ob\n"
                "\n"
                "def __r%(name)s__(self,ob):\n"
                "    return ob %(op)s self.__subject__\n"
                "\n"
                "def __i%(name)s__(self,ob):\n"
                "    self.__subject__ %(op)s=ob\n"
                "    return self\n"
            )
            % locals()
        )

    del name, op

    # Oddball signatures

    def __rdivmod__(self, ob):
        return divmod(ob, self.__subject__)

    def __pow__(self, *args):
        return pow(self.__subject__, *args)

    def __ipow__(self, ob):
        self.__subject__ **= ob
        return self

    def __rpow__(self, ob):
        return pow(ob, self.__subject__)


class ObjectProxy(AbstractProxy):
    """Proxy for a specific object"""

    __slots__ = "__subject__"

    def __init__(self, subject):
        self.__subject__ = subject


class AbstractWrapper(AbstractProxy):
    """Mixin to allow extra behaviors and attributes on proxy instance"""

    __slots__ = ()

    def __getattribute__(self, attr, oga=object.__getattribute__):
        if attr.startswith("__"):
            subject = oga(self, "__subject__")
            if attr == "__subject__":
                return subject
            return getattr(subject, attr)
        return oga(self, attr)

    def __getattr__(self, attr, oga=object.__getattribute__):
        return getattr(oga(self, "__subject__"), attr)

    def __setattr__(self, attr, val, osa=object.__setattr__):
        if (
            attr == "__subject__"
            or hasattr(type(self), attr)
            and not attr.startswith("__")
        ):
            osa(self, attr, val)
        else:
            setattr(self.__subject__, attr, val)

    def __delattr__(self, attr, oda=object.__delattr__):
        if (
            attr == "__subject__"
            or hasattr(type(self), attr)
            and not attr.startswith("__")
        ):
            oda(self, attr)
        else:
            delattr(self.__subject__, attr)


class ObjectWrapper(ObjectProxy, AbstractWrapper):
    __slots__ = ()


#######################
#  MONKEYS DOWN HERE  #
#######################


class CallableProxy(ObjectWrapper):
    __slots__ = "_eop_wrapper_"

    def __init__(self, wrapped, wrapper):
        super(CallableProxy, self).__init__(wrapped)
        self._eop_wrapper_ = wrapper

    def __call__(self, *args, **kwargs):
        return self._eop_wrapper_(self.__subject__, *args, **kwargs)


class BoundMethodProxy(ObjectWrapper):
    __slots__ = ("_eop_wrapper_", "_eop_instance_")

    def __init__(self, wrapped, instance, wrapper):
        super(BoundMethodProxy, self).__init__(wrapped)
        self._eop_instance_ = instance
        self._eop_wrapper_ = wrapper

    def __call__(self, *args, **kwargs):
        return self._eop_wrapper_(
            self.__subject__, self._eop_instance_, *args, **kwargs
        )


class UnboundMethodProxy(CallableProxy):
    __slots__ = "_eop_wrapper_"

    def __get__(self, instance, owner):
        return BoundMethodProxy(
            self.__subject__.__get__(instance, owner),
            instance or owner,
            self._eop_wrapper_,
        )

    def __getattribute__(self, attr, oga=object.__getattribute__):
        """
        We need to return our own version of __get__ or we may end up
        never being called if the member we are wrapping is wrapped
        again by someone else
        """
        if attr == "__get__":
            return oga(self, attr)
        return super(UnboundMethodProxy, self).__getattribute__(attr)


def monkeypatch_method(cls, method_name=None):
    def decorator(func):
        method_to_patch = method_name or func.__name__
        original = cls.__dict__[method_to_patch]
        replacement = UnboundMethodProxy(original, func)
        type.__setattr__(cls, method_to_patch, replacement)  # Avoid overrides
        return func

    return decorator


# Slightly annoying signature because there are no unbound methods in Python 3.
def unpatch_method(cls, method_name):
    type.__setattr__(cls, method_name, getattr(cls, method_name).__subject__)
