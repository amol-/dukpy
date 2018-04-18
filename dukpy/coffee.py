import os
from .evaljs import evaljs

COFFEE_COMPILER = os.path.join(os.path.dirname(__file__), 'jsmodules', 'coffeescript.js')


def coffee_compile(source):
    """Compiles the given ``source`` from CoffeeScript to JavaScript"""
    with open(COFFEE_COMPILER, 'rb') as coffeescript_js:
        return evaljs(
            (coffeescript_js.read().decode('utf-8'),
             'CoffeeScript.compile(dukpy.coffeecode)'),
            coffeecode=source
        )
