// Host runtime shim: route console output through DukPy's Python logger.
// The argument join preserves the legacy console.log/info/warn/error behavior.
;globalThis.console = {
    log: function() {
        globalThis.call_python('dukpy.log.info', Array.prototype.join.call(arguments, ' '));
    },
    info: function() {
        globalThis.call_python('dukpy.log.info', Array.prototype.join.call(arguments, ' '));
    },
    warn: function() {
        globalThis.call_python('dukpy.log.warn', Array.prototype.join.call(arguments, ' '));
    },
    error: function() {
        globalThis.call_python('dukpy.log.error', Array.prototype.join.call(arguments, ' '));
    }
};
