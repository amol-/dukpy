# encoding: utf-8

"""WebAssets integration for Babili as executed in Python using Dukpy."""

from __future__ import unicode_literals

import os

from dukpy.webassets.common import DukpyFilter, register


@register
class BabiliJS(DukpyFilter):
	# WebAssets filter metadata.
	name = 'babilijs'
	options = {'presets': "BABILI_PRESETS"}
	max_debug_level = None
	
	# Dukpy filter configuration.
	PREPARE = [
			'dukpy.webassets:js/polyfill.min.js',
			'dukpy.webassets:js/babel.min.js',
			'dukpy.webassets:js/babili.min.js',
			'''
				var process = function(source, options) {
					var result = Babili.transform(source, options);
					var map = result.map ? result.map.toString() : null;
					return { code: result.code, map: map };
				};
			'''
		]
	
	def setup(self):
		super(BabiliJS, self).setup()
		
		if not self.presets:  # Assign the default preset list.
			self.presets = ['es2015']
		elif not isinstance(self.presets, list):
			self.presets = [i.strip() for i in self.presets.split(',')]
	
	def input(self, _in, out, **kw):
		code = _in.read()
		options = {'presets': self.presets, 'filename': os.path.basename(kw['source_path'])}
		
		result = self.js.evaljs('eval(process.apply(this, [dukpy.source, dukpy.options]));',
				source=code, options=options)
		
		# TODO: Do something with the sourcemap.
		
		out.write(result['code'])  # Write the result to the destination.

