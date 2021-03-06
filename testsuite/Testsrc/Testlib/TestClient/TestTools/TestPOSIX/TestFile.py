# -*- coding: utf-8 -*-
import os
import sys
import copy
import difflib
import lxml.etree
from Bcfg2.Compat import b64encode, u_str
from mock import Mock, MagicMock, patch
from Bcfg2.Client.Tools.POSIX.File import *

# add all parent testsuite directories to sys.path to allow (most)
# relative imports in python 2.4
path = os.path.dirname(__file__)
while path != "/":
    if os.path.basename(path).lower().startswith("test"):
        sys.path.append(path)
    if os.path.basename(path) == "testsuite":
        break
    path = os.path.dirname(path)
from TestPOSIX.Testbase import TestPOSIXTool
from common import *


class TestPOSIXFile(TestPOSIXTool):
    test_obj = POSIXFile

    def test_fully_specified(self):
        ptool = self.get_obj()

        entry = lxml.etree.Element("Path", name="/test", type="file")
        self.assertFalse(ptool.fully_specified(entry))

        entry.set("empty", "true")
        self.assertTrue(ptool.fully_specified(entry))

        entry.set("empty", "false")
        entry.text = "text"
        self.assertTrue(ptool.fully_specified(entry))

    def test_is_string(self):
        ptool = self.get_obj()

        for char in list(range(8)) + list(range(14, 32)):
            self.assertFalse(ptool._is_string("foo" + chr(char) + "bar",
                                              'UTF-8'))
        for char in list(range(9, 14)) + list(range(33, 128)):
            self.assertTrue(ptool._is_string("foo" + chr(char) + "bar",
                                             'UTF-8'))
        ustr = 'é'
        self.assertTrue(ptool._is_string(ustr, 'UTF-8'))
        if not inPy3k:
            self.assertFalse(ptool._is_string("foo" + chr(128) + "bar",
                                              'ascii'))
            self.assertFalse(ptool._is_string(ustr, 'ascii'))

    def test_get_data(self):
        orig_entry = lxml.etree.Element("Path", name="/test", type="file")
        ptool = self.get_obj(setup=dict(encoding="ascii", ppath='/',
                                        max_copies=5))

        entry = copy.deepcopy(orig_entry)
        entry.text = b64encode("test")
        entry.set("encoding", "base64")
        self.assertEqual(ptool._get_data(entry), ("test", True))

        entry = copy.deepcopy(orig_entry)
        entry.set("empty", "true")
        self.assertEqual(ptool._get_data(entry), ("", False))

        entry = copy.deepcopy(orig_entry)
        entry.text = "test"
        self.assertEqual(ptool._get_data(entry), ("test", False))

        if inPy3k:
            ustr = 'é'
        else:
            ustr = u_str('é', 'UTF-8')
        entry = copy.deepcopy(orig_entry)
        entry.text = ustr
        self.assertEqual(ptool._get_data(entry), (ustr, False))

    @patch("%s.open" % builtins)
    @patch("Bcfg2.Client.Tools.POSIX.base.POSIXTool.verify")
    def test_verify(self, mock_verify, mock_open):
        entry = lxml.etree.Element("Path", name="/test", type="file")
        ptool = self.get_obj(setup=dict(interactive=False, ppath='/',
                                        max_copies=5))
        ptool._exists = Mock()
        ptool._get_data = Mock()
        ptool._get_diffs = Mock()

        def reset():
            ptool._get_diffs.reset_mock()
            ptool._get_data.reset_mock()
            ptool._exists.reset_mock()
            mock_verify.reset_mock()
            mock_open.reset_mock()

        ptool._get_data.return_value = ("test", False)
        ptool._exists.return_value = False
        mock_verify.return_value = True
        self.assertFalse(ptool.verify(entry, []))
        ptool._exists.assert_called_with(entry)
        mock_verify.assert_called_with(ptool, entry, [])
        ptool._get_diffs.assert_called_with(entry, interactive=False,
                                          sensitive=False, is_binary=False,
                                          content="")

        reset()
        exists_rv = MagicMock()
        exists_rv.__getitem__.return_value = 5
        ptool._exists.return_value = exists_rv
        ptool._get_data.return_value = ("test", True)
        self.assertFalse(ptool.verify(entry, []))
        ptool._exists.assert_called_with(entry)
        mock_verify.assert_called_with(ptool, entry, [])
        ptool._get_diffs.assert_called_with(entry, interactive=False,
                                          sensitive=False, is_binary=True,
                                          content=None)

        reset()
        ptool._get_data.return_value = ("test", False)
        exists_rv.__getitem__.return_value = 4
        entry.set("sensitive", "true")
        mock_open.return_value.read.return_value = "tart"
        self.assertFalse(ptool.verify(entry, []))
        ptool._exists.assert_called_with(entry)
        mock_verify.assert_called_with(ptool, entry, [])
        mock_open.assert_called_with(entry.get("name"))
        mock_open.return_value.read.assert_called_with()
        ptool._get_diffs.assert_called_with(entry, interactive=False,
                                          sensitive=True, is_binary=False,
                                          content="tart")

        reset()
        mock_open.return_value.read.return_value = "test"
        self.assertTrue(ptool.verify(entry, []))
        ptool._exists.assert_called_with(entry)
        mock_verify.assert_called_with(ptool, entry, [])
        mock_open.assert_called_with(entry.get("name"))
        mock_open.return_value.read.assert_called_with()
        self.assertFalse(ptool._get_diffs.called)

        reset()
        mock_open.side_effect = IOError
        self.assertFalse(ptool.verify(entry, []))
        ptool._exists.assert_called_with(entry)
        mock_open.assert_called_with(entry.get("name"))

    @patch("os.fdopen")
    @patch("tempfile.mkstemp")
    def test_write_tmpfile(self, mock_mkstemp, mock_fdopen):
        ptool = self.get_obj()
        ptool._get_data = Mock()
        entry = lxml.etree.Element("Path", name="/test", type="file",
                                   mode='0644', owner='root', group='root')
        newfile = "/foo/bar"

        def reset():
            ptool._get_data.reset_mock()
            mock_mkstemp.reset_mock()
            mock_fdopen.reset_mock()

        ptool._get_data.return_value = ("test", False)
        mock_mkstemp.return_value = (5, newfile)
        self.assertEqual(ptool._write_tmpfile(entry), newfile)
        ptool._get_data.assert_called_with(entry)
        mock_mkstemp.assert_called_with(prefix='test', dir='/')
        mock_fdopen.assert_called_with(5, 'w')
        mock_fdopen.return_value.write.assert_called_with("test")

        reset()
        mock_mkstemp.side_effect = OSError
        self.assertFalse(ptool._write_tmpfile(entry))
        mock_mkstemp.assert_called_with(prefix='test', dir='/')

        reset()
        mock_mkstemp.side_effect = None
        mock_fdopen.side_effect = OSError
        self.assertFalse(ptool._write_tmpfile(entry))
        mock_mkstemp.assert_called_with(prefix='test', dir='/')
        ptool._get_data.assert_called_with(entry)
        mock_fdopen.assert_called_with(5, 'w')

    @patch("os.rename")
    @patch("os.unlink")
    def test_rename_tmpfile(self, mock_unlink, mock_rename):
        ptool = self.get_obj()
        entry = lxml.etree.Element("Path", name="/test", type="file",
                                   mode='0644', owner='root', group='root')
        newfile = "/foo/bar"

        self.assertTrue(ptool._rename_tmpfile(newfile, entry))
        mock_rename.assert_called_with(newfile, entry.get("name"))

        mock_rename.reset_mock()
        mock_unlink.reset_mock()
        mock_rename.side_effect = OSError
        self.assertFalse(ptool._rename_tmpfile(newfile, entry))
        mock_rename.assert_called_with(newfile, entry.get("name"))
        mock_unlink.assert_called_with(newfile)

        # even if the unlink fails, return false gracefully
        mock_rename.reset_mock()
        mock_unlink.reset_mock()
        mock_unlink.side_effect = OSError
        self.assertFalse(ptool._rename_tmpfile(newfile, entry))
        mock_rename.assert_called_with(newfile, entry.get("name"))
        mock_unlink.assert_called_with(newfile)

    @patch("%s.open" % builtins)
    def test__get_diffs(self, mock_open):
        orig_entry = lxml.etree.Element("Path", name="/test", type="file",
                                        mode='0644', owner='root',
                                        group='root')
        orig_entry.text = "test"
        ondisk = "test2"
        ptool = self.get_obj(setup=dict(encoding="utf-8", ppath='/',
                                        max_copies=5))
        ptool._get_data = Mock()
        ptool._diff = Mock()
        ptool._is_string = Mock()

        def reset():
            ptool._is_string.reset_mock()
            ptool._get_data.reset_mock()
            ptool._diff.reset_mock()
            mock_open.reset_mock()
            return copy.deepcopy(orig_entry)

        ptool._is_string.return_value = True
        ptool._get_data.return_value = (orig_entry.text, False)
        mock_open.return_value.read.return_value = ondisk
        ptool._diff.return_value = ["-test2", "+test"]

        # binary data in the entry
        entry = reset()
        ptool._get_diffs(entry, is_binary=True)
        mock_open.assert_called_with(entry.get("name"))
        mock_open.return_value.read.assert_any_call()
        self.assertFalse(ptool._diff.called)
        self.assertEqual(entry.get("current_bfile"), b64encode(ondisk))

        # binary data on disk
        entry = reset()
        ptool._is_string.return_value = False
        ptool._get_diffs(entry, content=ondisk)
        self.assertFalse(mock_open.called)
        self.assertFalse(ptool._diff.called)
        self.assertEqual(entry.get("current_bfile"), b64encode(ondisk))

        # sensitive, non-interactive -- do nothing
        entry = reset()
        ptool._is_string.return_value = True
        ptool._get_diffs(entry, sensitive=True, interactive=False)
        self.assertFalse(mock_open.called)
        self.assertFalse(ptool._diff.called)
        self.assertXMLEqual(entry, orig_entry)

        # sensitive, interactive
        entry = reset()
        ptool._get_diffs(entry, sensitive=True, interactive=True)
        mock_open.assert_called_with(entry.get("name"))
        mock_open.return_value.read.assert_any_call()
        ptool._diff.assert_called_with(ondisk, entry.text,
                                       difflib.unified_diff,
                                       filename=entry.get("name"))
        self.assertIsNotNone(entry.get("qtext"))
        del entry.attrib['qtext']
        self.assertItemsEqual(orig_entry.attrib, entry.attrib)

        # non-sensitive, non-interactive
        entry = reset()
        ptool._get_diffs(entry, content=ondisk)
        self.assertFalse(mock_open.called)
        ptool._diff.assert_called_with(ondisk, entry.text, difflib.ndiff,
                                     filename=entry.get("name"))
        self.assertIsNone(entry.get("qtext"))
        self.assertEqual(entry.get("current_bdiff"),
                         b64encode("\n".join(ptool._diff.return_value)))
        del entry.attrib["current_bdiff"]
        self.assertItemsEqual(orig_entry.attrib, entry.attrib)

        # non-sensitive, interactive -- do everything. also test
        # appending to qtext
        entry = reset()
        entry.set("qtext", "test")
        ptool._get_diffs(entry, interactive=True)
        mock_open.assert_called_with(entry.get("name"))
        mock_open.return_value.read.assert_any_call()
        self.assertItemsEqual(ptool._diff.call_args_list,
                              [call(ondisk, entry.text, difflib.unified_diff,
                                    filename=entry.get("name")),
                               call(ondisk, entry.text, difflib.ndiff,
                                    filename=entry.get("name"))])
        self.assertIsNotNone(entry.get("qtext"))
        self.assertTrue(entry.get("qtext").startswith("test\n"))
        self.assertEqual(entry.get("current_bdiff"),
                         b64encode("\n".join(ptool._diff.return_value)))
        del entry.attrib['qtext']
        del entry.attrib["current_bdiff"]
        self.assertItemsEqual(orig_entry.attrib, entry.attrib)

        # non-sensitive, interactive with unicode data
        entry = reset()
        entry.text = u("tëst")
        encoded = entry.text.encode(ptool.setup['encoding'])
        ptool._diff.return_value = ["-test2", "+tëst"]
        ptool._get_data.return_value = (encoded, False)
        ptool._get_diffs(entry, interactive=True)
        mock_open.assert_called_with(entry.get("name"))
        mock_open.return_value.read.assert_any_call()
        self.assertItemsEqual(ptool._diff.call_args_list,
                              [call(ondisk, encoded, difflib.unified_diff,
                                    filename=entry.get("name")),
                               call(ondisk, encoded, difflib.ndiff,
                                    filename=entry.get("name"))])
        self.assertIsNotNone(entry.get("qtext"))
        self.assertEqual(entry.get("current_bdiff"),
                         b64encode("\n".join(ptool._diff.return_value)))
        del entry.attrib['qtext']
        del entry.attrib["current_bdiff"]
        self.assertItemsEqual(orig_entry.attrib, entry.attrib)

    @patch("os.path.exists")
    @patch("Bcfg2.Client.Tools.POSIX.base.POSIXTool.install")
    def test_install(self, mock_install, mock_exists):
        ptool = self.get_obj()
        ptool._makedirs = Mock()
        ptool._set_perms = Mock()
        ptool._write_tmpfile = Mock()
        ptool._rename_tmpfile = Mock()
        entry = lxml.etree.Element("Path", name="/test", type="file",
                                   mode='0644', owner='root', group='root')

        def reset():
            ptool._rename_tmpfile.reset_mock()
            ptool._write_tmpfile.reset_mock()
            ptool._set_perms.reset_mock()
            ptool._makedirs.reset_mock()
            mock_install.reset_mock()
            mock_exists.reset_mock()

        mock_exists.return_value = False
        ptool._makedirs.return_value = False
        self.assertFalse(ptool.install(entry))
        mock_exists.assert_called_with("/")
        ptool._makedirs.assert_called_with(entry, path="/")

        reset()
        ptool._makedirs.return_value = True
        ptool._write_tmpfile.return_value = False
        self.assertFalse(ptool.install(entry))
        mock_exists.assert_called_with("/")
        ptool._makedirs.assert_called_with(entry, path="/")
        ptool._write_tmpfile.assert_called_with(entry)

        reset()
        newfile = '/test.X987yS'
        ptool._write_tmpfile.return_value = newfile
        ptool._set_perms.return_value = False
        ptool._rename_tmpfile.return_value = False
        self.assertFalse(ptool.install(entry))
        mock_exists.assert_called_with("/")
        ptool._makedirs.assert_called_with(entry, path="/")
        ptool._write_tmpfile.assert_called_with(entry)
        ptool._set_perms.assert_called_with(entry, path=newfile)
        ptool._rename_tmpfile.assert_called_with(newfile, entry)

        reset()
        ptool._rename_tmpfile.return_value = True
        mock_install.return_value = False
        self.assertFalse(ptool.install(entry))
        mock_exists.assert_called_with("/")
        ptool._makedirs.assert_called_with(entry, path="/")
        ptool._write_tmpfile.assert_called_with(entry)
        ptool._set_perms.assert_called_with(entry, path=newfile)
        ptool._rename_tmpfile.assert_called_with(newfile, entry)
        mock_install.assert_called_with(ptool, entry)

        reset()
        mock_install.return_value = True
        self.assertFalse(ptool.install(entry))
        mock_exists.assert_called_with("/")
        ptool._makedirs.assert_called_with(entry, path="/")
        ptool._write_tmpfile.assert_called_with(entry)
        ptool._set_perms.assert_called_with(entry, path=newfile)
        ptool._rename_tmpfile.assert_called_with(newfile, entry)
        mock_install.assert_called_with(ptool, entry)

        reset()
        ptool._set_perms.return_value = True
        self.assertTrue(ptool.install(entry))
        mock_exists.assert_called_with("/")
        ptool._makedirs.assert_called_with(entry, path="/")
        ptool._write_tmpfile.assert_called_with(entry)
        ptool._set_perms.assert_called_with(entry, path=newfile)
        ptool._rename_tmpfile.assert_called_with(newfile, entry)
        mock_install.assert_called_with(ptool, entry)

        reset()
        mock_exists.return_value = True
        self.assertTrue(ptool.install(entry))
        mock_exists.assert_called_with("/")
        self.assertFalse(ptool._makedirs.called)
        ptool._write_tmpfile.assert_called_with(entry)
        ptool._set_perms.assert_called_with(entry, path=newfile)
        ptool._rename_tmpfile.assert_called_with(newfile, entry)
        mock_install.assert_called_with(ptool, entry)

    @patch("time.time")
    def test_diff(self, mock_time):
        ptool = self.get_obj()
        content1 = "line1\nline2"
        content2 = "line3"

        self.now = 1345640723

        def time_rv():
            self.now += 1
            return self.now
        mock_time.side_effect = time_rv

        rv = ["line1", "line2", "line3"]
        func = Mock()
        func.return_value = rv
        self.assertItemsEqual(ptool._diff(content1, content2, func), rv)
        func.assert_called_with(["line1", "line2"], ["line3"])

        func.reset_mock()
        mock_time.reset_mock()
        def time_rv():
            self.now += 5
            return self.now
        mock_time.side_effect = time_rv

        def slow_diff(content1, content2):
            for i in range(1, 10):
                yield "line%s" % i
        func.side_effect = slow_diff
        self.assertFalse(ptool._diff(content1, content2, func), rv)
        func.assert_called_with(["line1", "line2"], ["line3"])
