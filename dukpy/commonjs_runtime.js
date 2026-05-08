// Host runtime shim: provide CommonJS require/module/exports compatibility.
// Python resolves and loads module source; QuickJS compiles and runs module bodies.
;(function() {
    var _dukpy_modules = {};

    function _dukpy_make_require(base) {
        function _dukpy_require(id) {
            var resolved = call_python('dukpy.normalize_module', base || '', id) || id;
            if (_dukpy_modules[resolved]) {
                return _dukpy_modules[resolved].exports;
            }

            var m = call_python('dukpy.load_module', resolved);
            if (!m || !m[1]) {
                throw new Error('cannot find module: ' + id);
            }

            return _dukpy_eval_cjs_source(m[0], resolved, m[1]).exports;
        }
        _dukpy_require.id = base || '';
        return _dukpy_require;
    }

    function _dukpy_eval_cjs_source(module_id, resolved, source) {
        if (_dukpy_modules[module_id]) {
            return _dukpy_modules[module_id];
        }

        var func = new Function('require', 'exports', 'module', source);
        var module = { id: module_id, exports: {} };
        var cache_keys = [module_id];
        _dukpy_modules[module_id] = module;
        if (module_id !== resolved) {
            _dukpy_modules[resolved] = module;
            cache_keys.push(resolved);
        }

        module.require = _dukpy_make_require(module_id);
        var exports = module.exports;
        try {
            func.call(exports, module.require, exports, module);
        } catch (e) {
            for (var i = 0; i < cache_keys.length; i++) {
                delete _dukpy_modules[cache_keys[i]];
            }
            throw e;
        }
        return module;
    }

    globalThis.require = _dukpy_make_require('');
    globalThis._dukpy_eval_cjs_source = _dukpy_eval_cjs_source;
})();
