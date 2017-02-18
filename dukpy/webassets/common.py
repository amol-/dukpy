# encoding: utf-8

"""WebAssets integration common base filter."""

from __future__ import unicode_literals

from pkg_resources import resource_string
from dukpy import JSInterpreter

try:
	from webassets.filter import Filter, register_filter

except ImportError:
	raise ImportError('You must install the "webassets" package to use this.')


__all__ = ['DukpyFilter', 'register']

log = __import__('logging').getLogger(__name__)


def register(cls):
	"""Work around the issue that register_filter doesn't return the class passed in."""
	register_filter(cls)
	return cls


class DukpyFilter(Filter):
	"""JavaScript-based Filter framework.
	
	Subclasses may optionally define an iterable attribute `PATH` to either add explicit paths (starting with `/` or
	`.`) or package-relative paths (in `package:path` notation) to add to the runtime's loader paths.
	
	Subclasses may also define an iterable attribute `PREPARE` containing elements in one of three forms:
	
	1. A 2-tuple containing a variable name to assign the result of a call to `require()` with the second tuple value
		passed as the string value to that call.
	2. Code to execute which must contain a semicolon. (I.e. complete expression.)
	3. A package-relative path to a file on-disk containing JavaScript code to execute, in `package:path` notation.
	
	Access the interpreter as `self.js`.
	"""
	
	PATH = []
	PREPARE = []
	
	def setup(self):
		super(DukpyFilter, self).setup()
		
		self._js = None  # A prepared JavaScript runtime for our filter.
	
	def _js_init(self):
		"""A stream of code to execute on runtime startup."""
		
		for pre in self.PREPARE:
			if isinstance(pre, tuple):  # A require() statement.
				name, script = pre  # Extract the component values.
				yield "var " + name + " = require('" + script + "');"  # Reconstitute the equivalent code.
				del name, script  # Clean up after ourselves.
				continue
			
			if ';' in pre:  # One or more custom lines of code to execute directly.
				yield pre
				continue
			
			# The final acceptable case, here, is a package + path reference separated by a colon. This represents a
			# package-relative path, which will be retrieved (in a zip-safe manner!) and executed inline.
			
			package, _, path = pre.partition(':')  # Extract the component values.
			
			if __debug__:
				log.debug("Loading script from: " + package + ":" + path)
			
			yield resource_string(package, path).decode('utf-8')  # Retrieve the file from the package.
			
			del package, _, path  # Clean up after ourselves.
		
		if __debug__:
			log.debug("JavaScript runtime initialization code prepared.")
	
	@property
	def js(self):
		"""Return, or initialize, a JavaScript runtime for filter processing."""
		
		if not self._js:
			if __debug__:
				log.debug("Initializing JavaScript runtime.", extra=dict(asset_filter=repr(self), js_path=self.PATH))
			
			self._js = JSInterpreter()  # Construct a fresh interpreter.
			
			for path in self.PATH:  # Register any paths required by the filter.
				self._js.loader.register_path(path)
			
			if self.PREPARE:  # Execute the stream of initialization code.
				self._js.evaljs(self._js_init())
			
			if __debug__:
				log.debug("JavaScript runtime prepared.", extra=dict(asset_filter=repr(self)))
		
		return self._js

