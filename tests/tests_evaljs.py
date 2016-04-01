# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import dukpy


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