.PHONY: ALL

ALL: dukpy/webassets/js/autoprefixer.js dukpy/webassets/js/polyfill.min.js dukpy/webassets/js/babel.min.js dukpy/webassets/js/babili.min.js

build/js:
	mkdir -p build/js


dukpy/webassets/js/autoprefixer.js:
	wget -O $@ https://raw.github.com/ai/autoprefixer-rails/master/vendor/autoprefixer.js

dukpy/webassets/js/polyfill.min.js: build/js
	dukpy-install -d build/js babel-polyfill
	cp build/js/babel-polyfill/dist/polyfill.min.js $@

dukpy/webassets/js/babel.min.js: build/js
	dukpy-install -d build/js babel-standalone
	cp build/js/babel-standalone/babel.min.js $@

dukpy/webassets/js/babili.min.js: build/js
	dukpy-install -d build/js babili-standalone
	cp build/js/babili-standalone/babili.min.js $@
