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
            if (!m || m[1] === null || m[1] === undefined) {
                throw new Error('cannot find module: ' + id);
            }

            if (m[2] === 'commonjs') {
                return _dukpy_eval_cjs_source(m[0], resolved, m[1]).exports;
            }
            if (m[2] === 'detect') {
                if (_dukpy_cjs_source_compiles(m[1])) {
                    return _dukpy_eval_cjs_source(m[0], resolved, m[1]).exports;
                }
                throw new Error('require() of ES modules is not supported: ' + id);
            }
            if (m[2] === 'module') {
                throw new Error('require() of ES modules is not supported: ' + id);
            }
            throw new TypeError('Invalid module format: ' + m[2]);
        }
        _dukpy_require.id = base || '';
        return _dukpy_require;
    }

    function _dukpy_compile_cjs_source(source) {
        return new Function(
            'exports', 'require', 'module', '__filename', '__dirname', source
        );
    }

    function _dukpy_cjs_source_compiles(source) {
        try {
            _dukpy_compile_cjs_source(source);
            return true;
        } catch (e) {
            if (e && e.name === 'SyntaxError') {
                return false;
            }
            throw e;
        }
    }

    function _dukpy_eval_cjs_source(module_id, resolved, source) {
        if (_dukpy_modules[module_id]) {
            return _dukpy_modules[module_id];
        }

        var func = _dukpy_compile_cjs_source(source);
        var module = { id: module_id, exports: {}, filename: module_id };
        var cache_keys = [module_id];
        _dukpy_modules[module_id] = module;
        if (module_id !== resolved) {
            _dukpy_modules[resolved] = module;
            cache_keys.push(resolved);
        }

        module.require = _dukpy_make_require(module_id);
        var exports = module.exports;
        try {
            var slash = Math.max(module_id.lastIndexOf('/'), module_id.lastIndexOf('\\'));
            var dirname = slash >= 0 ? module_id.slice(0, slash) : '';
            func.call(exports, exports, module.require, module, module_id, dirname);
        } catch (e) {
            for (var i = 0; i < cache_keys.length; i++) {
                delete _dukpy_modules[cache_keys[i]];
            }
            throw e;
        }
        return module;
    }

    globalThis.require = _dukpy_make_require('');
    globalThis._dukpy_cjs_source_compiles = _dukpy_cjs_source_compiles;
    globalThis._dukpy_eval_cjs_source = _dukpy_eval_cjs_source;
})();
