import os
import sys
import unittest
from mock import patch
from functools import wraps

datastore = "/"

XI_NAMESPACE = "http://www.w3.org/2001/XInclude"
XI = "{%s}" % XI_NAMESPACE

if sys.hexversion >= 0x03000000:
    inPy3k = True
else:
    inPy3k = False

try:
    from django.core.management import setup_environ
    has_django = True

    os.environ['DJANGO_SETTINGS_MODULE'] = "Bcfg2.settings"

    import Bcfg2.settings
    Bcfg2.settings.DATABASE_NAME = \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sqlite")
    Bcfg2.settings.DATABASES['default']['NAME'] = Bcfg2.settings.DATABASE_NAME
except ImportError:
    has_django = False

try:
    from mock import call
except ImportError:
    def call(*args, **kwargs):
        """ the Mock call object is a fairly recent addition, but it's
        very very useful, so we create our own function to create Mock
        calls """
        return (args, kwargs)

if inPy3k:
    builtins = "builtins"

    def u(x):
        return x
else:
    builtins = "__builtin__"

    import codecs
    def u(x):
        return codecs.unicode_escape_decode(x)[0]


if hasattr(unittest, "skip"):
    can_skip = True
    skip = unittest.skip
    skipIf = unittest.skipIf
    skipUnless = unittest.skipUnless
else:
    # we can't actually skip tests, we just make them pass
    can_skip = False

    def skip(msg):
        def decorator(func):
            @wraps(func)
            def inner(*args, **kwargs):
                pass
            return inner
        return decorator

    def skipIf(condition, msg):
        def decorator(func):
            if condition:
                return func

            @wraps(func)
            def inner(*args, **kwargs):
                pass
            return inner
        return decorator

    def skipUnless(condition, msg):
        def decorator(func):
            if not condition:
                return func

            @wraps(func)
            def inner(*args, **kwargs):
                pass
            return inner
        return decorator


needs_assertItemsEqual = False
needs_others = False
if not hasattr(unittest.TestCase, "assertItemsEqual"):
    # TestCase in Py3k lacks assertItemsEqual, but has the other
    # convenience methods.  this code is cribbed from the py2.7
    # unittest library
    import collections
    needs_assertItemsEqual = True

    def _count_diff_all_purpose(actual, expected):
        '''Returns list of (cnt_act, cnt_exp, elem) triples where the
        counts differ'''
        # elements need not be hashable
        s, t = list(actual), list(expected)
        m, n = len(s), len(t)
        NULL = object()
        result = []
        for i, elem in enumerate(s):
            if elem is NULL:
                continue
            cnt_s = cnt_t = 0
            for j in range(i, m):
                if s[j] == elem:
                    cnt_s += 1
                    s[j] = NULL
            for j, other_elem in enumerate(t):
                if other_elem == elem:
                    cnt_t += 1
                    t[j] = NULL
            if cnt_s != cnt_t:
                diff = _Mismatch(cnt_s, cnt_t, elem)
                result.append(diff)

        for i, elem in enumerate(t):
            if elem is NULL:
                continue
            cnt_t = 0
            for j in range(i, n):
                if t[j] == elem:
                    cnt_t += 1
                    t[j] = NULL
            diff = _Mismatch(0, cnt_t, elem)
            result.append(diff)
        return result

    def _count_diff_hashable(actual, expected):
        '''Returns list of (cnt_act, cnt_exp, elem) triples where the
        counts differ'''
        # elements must be hashable
        s, t = _ordered_count(actual), _ordered_count(expected)
        result = []
        for elem, cnt_s in s.items():
            cnt_t = t.get(elem, 0)
            if cnt_s != cnt_t:
                diff = _Mismatch(cnt_s, cnt_t, elem)
                result.append(diff)
        for elem, cnt_t in t.items():
            if elem not in s:
                diff = _Mismatch(0, cnt_t, elem)
                result.append(diff)
        return result

if not hasattr(unittest.TestCase, "assertIn"):
    # versions of TestCase before python 2.7 and python 3.1 lacked a
    # lot of the really handy convenience methods, so we provide them
    # -- at least the easy ones and the ones we use.
    needs_others = True

    def _assertion(predicate, default_msg=None):
        @wraps(predicate)
        def inner(self, *args, **kwargs):
            if 'msg' in kwargs:
                msg = kwargs['msg']
                del kwargs['msg']
            else:
                msg = default_msg % args
            assert predicate(*args, **kwargs), msg
        return inner


class Bcfg2TestCase(unittest.TestCase):
    if needs_assertItemsEqual:
        def assertItemsEqual(self, expected_seq, actual_seq, msg=None):
            first_seq, second_seq = list(actual_seq), list(expected_seq)
            try:
                first = collections.Counter(first_seq)
                second = collections.Counter(second_seq)
            except TypeError:
                # Handle case with unhashable elements
                differences = _count_diff_all_purpose(first_seq, second_seq)
            else:
                if first == second:
                    return
                differences = _count_diff_hashable(first_seq, second_seq)

            if differences:
                standardMsg = 'Element counts were not equal:\n'
                lines = ['First has %d, Second has %d:  %r' % diff
                         for diff in differences]
                diffMsg = '\n'.join(lines)
                standardMsg = self._truncateMessage(standardMsg, diffMsg)
                msg = self._formatMessage(msg, standardMsg)
                self.fail(msg)

    if needs_others:
        assertIs = _assertion(lambda a, b: a is b, "%s is not %s")
        assertIsNot = _assertion(lambda a, b: a is not b, "%s is %s")
        assertIsNone = _assertion(lambda x: x is None, "%s is not None")
        assertIsNotNone = _assertion(lambda x: x is not None, "%s is None")
        assertIn = _assertion(lambda a, b: a in b, "%s is not in %s")
        assertNotIn = _assertion(lambda a, b: a not in b, "%s is in %s")
        assertIsInstance = _assertion(isinstance, "%s is not instance of %s")
        assertNotIsInstance = _assertion(lambda a, b: not isinstance(a, b),
                                         "%s is instance of %s")
        assertGreater = _assertion(lambda a, b: a > b,
                                   "%s is not greater than %s")
        assertGreaterEqual = _assertion(lambda a, b: a >= b,
                                        "%s is not greater than or equal to %s")
        assertLess = _assertion(lambda a, b: a < b, "%s is not less than %s")
        assertLessEqual = _assertion(lambda a, b: a <= b,
                                     "%s is not less than or equal to %s")


    def assertXMLEqual(self, el1, el2, msg=None):
        self.assertEqual(el1.tag, el2.tag, msg=msg)
        self.assertEqual(el1.text, el2.text, msg=msg)
        self.assertItemsEqual(el1.attrib, el2.attrib, msg=msg)
        self.assertEqual(len(el1.getchildren()),
                         len(el2.getchildren()))
        for child1 in el1.getchildren():
            cname = child1.get("name")
            self.assertIsNotNone(cname,
                                 msg="Element %s has no 'name' attribute" %
                                 child1.tag)
            children2 = el2.xpath("*[@name='%s']" % cname)
            self.assertEqual(len(children2), 1,
                             msg="More than one element named %s" % cname)
            self.assertXMLEqual(child1, children2[0], msg=msg)        


class DBModelTestCase(Bcfg2TestCase):
    models = []

    @skipUnless(has_django, "Django not found, skipping")
    def test_syncdb(self):
        # create the test database
        setup_environ(Bcfg2.settings)
        from django.core.management.commands import syncdb
        cmd = syncdb.Command()
        cmd.handle_noargs(interactive=False)
        self.assertTrue(os.path.exists(Bcfg2.settings.DATABASE_NAME))

    @skipUnless(has_django, "Django not found, skipping")
    def test_cleandb(self):
        """ ensure that we a) can connect to the database; b) start with a
        clean database """
        for model in self.models:
            model.objects.all().delete()
            self.assertItemsEqual(list(model.objects.all()), [])


def syncdb(modeltest):
    inst = modeltest(methodName='test_syncdb')
    inst.test_syncdb()
    inst.test_cleandb()


def patchIf(condition, entity, **kwargs):
    """ perform conditional patching.  this is necessary because some
    libraries might not be installed (e.g., selinux, pylibacl), and
    patching will barf on that.  Other workarounds are not available
    to us; e.g., context managers aren't in python 2.4, and using
    inner functions doesn't work because python 2.6 applies all
    decorators at compile-time, not at run-time, so decorating inner
    functions does not prevent the decorators from being run. """
    if condition:
        return patch(entity, **kwargs)
    else:
        return lambda f: f