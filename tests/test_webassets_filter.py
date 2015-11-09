from __future__ import unicode_literals
import json
import dukpy
from dukpy.webassets import BabelJS
try:
    from io import StringIO
except:
    from StringIO import StringIO


class TestEvalJS(object):
    def test_filter_available(self):
        es6source = StringIO('''
class Point {
    constructor(x, y) {
        this.x = x;
        this.y = y;
    }
    toString() {
        return '(' + this.x + ', ' + this.y + ')';
    }
}
''')

        out = StringIO()
        BabelJS().input(es6source, out)
        
        out.seek(0)
        ans = out.read()

        assert '''var Point = (function () {
    function Point(x, y) {
''' in ans, ans
     
