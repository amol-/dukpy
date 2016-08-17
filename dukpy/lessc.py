from .nodelike import NodeLikeInterpreter


def less_compile(source, options=None):
    """Compiles the given ``source`` from LESS to CSS"""
    options = options or {}
    res = NodeLikeInterpreter().evaljs(
        ('var result = null;'
         'var less = require("less/less-node");',
         'less.render(dukpy.lesscode, dukpy.lessoptions, function(error, output) {'
         '  result = {"error": error, "output": output};'
         '});'
         'result;'),
        lesscode=source,
        lessoptions=options
    )
    if not res:
        raise RuntimeError('Results or errors unavailable')

    if res.get('error'):
        raise LessCompilerError(res['error']['message'])

    return res['output']['css']


class LessCompilerError(Exception):
    pass

