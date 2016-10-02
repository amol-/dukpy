# encoding: utf-8

"""WebAssets integration for Autoprefixer as executed within Python by Dukpy."""

from __future__ import unicode_literals

from dukpy.webassets.common import DukpyFilter, register


@register
class Autoprefixer(DukpyFilter):
	# WebAssets filter metadata.
	name = 'autoprefixer'
	options = {'browsers': 'AUTOPREFIXER_BROWSERS'}
	max_debug_level = None
	
	# Dukpy filter configuration.
	PREPARE = [
			'var global = this;',  # Bind so the wrapped module unpacks into our namespace.
			'dukpy.webassets:js/autoprefixer.js',  # Minified/combined version loaded from package.
			# This is the general processing handler.
			'''
				var process = function() {
					var result = autoprefixer.process.apply(autoprefixer, arguments);
					var warns  = result.warnings().map(function (i) {
						delete i.plugin;
						return i.toString();
					});
					var map = result.map ? result.map.toString() : null;
					return { css: result.css, map: map, warnings: warns };
				};
			'''
		]
	
	def setup(self):
		super(Autoprefixer, self).setup()
		
		if not self.browsers:  # Prepare a default set of browsers to be compatible with.
			self.browsers = 'last 2 versions, > 2%'
	
	def input(self, _in, out, **kw):
		source = _in.read()  # Read out the CSS to autoprefix.
		options = {'browsers': self.browsers}  # Prepare the configuration.
		
		# Execute and return the result of processing.
		result = self.js.evaljs('eval(process.apply(this, [dukpy.source, dukpy.options]));',
				source=source, options=options)
		
		# TODO: Do something with the warnings.
		# TODO: Do something with the sourcemap.
		
		out.write(result['css'])  # Write the result to the destination.

