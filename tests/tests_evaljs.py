# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import dukpy
import mock


class TestEvalJS(object):
    def test_object_return(self):
        ans = dukpy.evaljs(["var o = {'value': 5}",
                            "o['value'] += 3",
                            "o"])
        assert ans == {'value': 8}

    def test_sum(self):
        n = dukpy.evaljs("dukpy['value'] + 3", value=7)
        assert n == 10

    def test_unicode(self):
        s = dukpy.evaljs("dukpy.c + 'A'", c="華")
        assert s == '華A'

    def test_unicode_jssrc(self):
        s = dukpy.evaljs("dukpy.c + '華'", c="華")
        assert s == '華華'

    def test_eval_files(self):
        testfile = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'test.js')
        with open(testfile) as f:
            s = dukpy.evaljs(f)
        assert s == 8, s

    def test_eval_files_multi(self):
        testfile = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'test.js')
        with open(testfile) as f:
            with open(testfile) as f2:
                s = dukpy.evaljs([f, f2])
        assert s == 11, s

    def test_logging(self):
        log = logging.getLogger('dukpy.interpreter')

        with mock.patch.object(log, 'info', return_value=None) as fakelog:
            dukpy.evaljs('console.log("HI")')
            assert fakelog.call_count == 1

        with mock.patch.object(log, 'info', return_value=None) as fakelog:
            dukpy.evaljs('console.info("HI")')
            assert fakelog.call_count == 1

        with mock.patch.object(log, 'error', return_value=None) as fakelog:
            dukpy.evaljs('console.error("HI")')
            assert fakelog.call_count == 1

        with mock.patch.object(log, 'warn', return_value=None) as fakelog:
            dukpy.evaljs('console.warn("HI")')
            assert fakelog.call_count == 1