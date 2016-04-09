import os
from .evaljs import evaljs

TS_COMPILER = os.path.join(os.path.dirname(__file__), 'jsmodules', 'typescriptServices.js')
TSC_OPTIONS = '{ module: ts.ModuleKind.System, target: ts.ScriptTarget.ES5, newLine: 1 }'


def typescript_compile(source):
    """Compiles the given ``source`` from TypeScript to ES5 using TypescriptServices.js"""
    with open(TS_COMPILER, 'r') as tsservices_js:
        return evaljs(
            (tsservices_js.read(),
             'ts.transpile(dukpy.tscode, {options});'.format(options=TSC_OPTIONS)),
            tscode=source
        )
