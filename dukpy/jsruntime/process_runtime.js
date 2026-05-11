// Host runtime shim: expose a Node-like process.env snapshot.
// Python supplies dukpy.environ as JSON data during interpreter startup.
;globalThis.process = {};
globalThis.process.env = dukpy.environ;
