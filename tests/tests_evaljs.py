import json
import dukpy

class TestEvalJS(object):
    def test_object_return(self):
        ans = dukpy.evaljs(["var o = {'value': 5}",
                            "o['value'] += 3",
                            "o"])
        assert ans == {'value': 8}

    def test_coffee(self):
        ans = dukpy.coffee_compile('''
    fill = (container, liquid = "coffee") ->
        "Filling the #{container} with #{liquid}..."
''')
        assert ans == '''(function() {
  var fill;

  fill = function(container, liquid) {
    if (liquid == null) {
      liquid = "coffee";
    }
    return "Filling the " + container + " with " + liquid + "...";
  };

}).call(this);
'''

    def test_sum(self):
        n = dukpy.evaljs("dukpy['value'] + 3", value=7)
        assert n == 10

    def test_babel(self):
        ans = dukpy.babel_compile('''
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
        assert '''var Point = (function () {
    function Point(x, y) {
''' in ans, ans