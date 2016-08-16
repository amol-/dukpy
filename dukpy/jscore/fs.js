'use strict';

exports.statSync = function(path) {
    /* Totally fake implementation only to make less.js happy */
    if (call_python('file.exists', path))
        return {};
    else
        throw {'error': 'Unable to access file'};
};

exports.readFileSync = function(path, options) {
    /* Stripped down implementation only to make less.js happy */
    if (!options) {
        options = { encoding: null, flag: 'r' };
    } else if (typeof options === 'string') {
        options = { encoding: options, flag: 'r' };
    } else if (typeof options !== 'object') {
        throwOptionsError(options);
    }

    var encoding = options.encoding;
    var data = call_python('file.read', path, encoding);
    return data
};

function throwOptionsError(options) {
  throw new TypeError('Expected options to be either an object or a string, ' +
    'but got ' + typeof options + ' instead');
}