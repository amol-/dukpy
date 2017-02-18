# encoding: utf-8

"""WebAssets integration for Rollup as executed in Python using Dukpy."""

from __future__ import unicode_literals

import os
import sys

from dukpy.webassets.common import DukpyFilter, register


@register
class RollupJS(DukpyFilter):
	# WebAssets filter metadata.
	name = 'rollupjs'
	options = {
			'module_format': "ROLLUP_FORMAT",
			'module_name': "ROLLUP_MODULE_NAME",
			'module_entry': "ROLLUP_ENTRY",
		}
	max_debug_level = None
	
	# Dukpy filter configuration.
	PREPARE = [
			'dukpy.webassets:js/polyfill.min.js',
			'dukpy.webassets:js/mock-promises.js',
			'dukpy.webassets:js/rollup.browser.js',
		]
	
	def __init__(self, *args, **kw):
		super(RollupJS, self).__init__(*args, **kw)
		self._modules = {}
	
	def setup(self):
		super(RollupJS, self).setup()
		
		if not self.module_format:
			self.module_format = 'iife'
		
		if not self.module_entry:
			self.module_entry = '__jsmain__.js'
	
	def _translate_name(self, hunk, data, names):
		"""Translate path names into reasonable Python-like imports.
		
		/path/to/illico/common/illico/common/js/lib/dom4.js
		illico/common/js/lib/dom4.js
		
		http://example.com/foo/bar.js
		example.com/foo/bar.js
		"""
		
		if 'source_path' in data:
			# Explicitly passed to us.
			src_name = data['source_path']
		
		elif hasattr(hunk, 'url'):
			names.append(hunk.url)
			return hunk.url.partition('://')[2]  # XXX: Cheap hack.
		
		elif hasattr(hunk, 'files'):
			assert len(hunk.files) == 1
			names.append(hunk.files[0])
			src_name = hunk.files[0]
		
		elif hasattr(hunk, 'filename'):
			names.append(hunk.filename)
			src_name = hunk.filename
		
		else:
			raise ValueError("Unable to determine filename for hunk: " + repr(hunk))
		
		candidates = {src_name[len(path)+1:] for path in sys.path if path and src_name.startswith(path)}
		
		cwd = os.getcwd()
		if not candidates and src_name.startswith(cwd):  # Fall back on CWD prefix stripping.
			candidates = {src_name[len(cwd)+1:]}
		
		if not candidates:  # Welp, we tried. Best of luck to you.
			candidates = {src_name[1:]}
		
		candidates = list(sorted(candidates))
		return candidates[0]
	
	def concat(self, out, hunks, **kw):
		names = []
		modules = {self._translate_name(hunk, data, names): hunk.data() for hunk, data in hunks}
		options = {'format': self.module_format}
		
		if self.module_name:
			options['moduleName'] = self.module_name
		
		__import__('pudb').set_trace()
		
		result = self.js.evaljs('''var result; result = do_rollup(dukpy.entry, dukpy.modules, dukpy.options);''',
				entry = self.module_entry,
				modules = modules,
				options = options
			)
		
		while not result.get('done', False):
			result = self.js.evaljs('window._runTimeouts()')
			if result == 0:
				result = self.js.evaljs('result')
				break
		
		out.write(result['code'])

