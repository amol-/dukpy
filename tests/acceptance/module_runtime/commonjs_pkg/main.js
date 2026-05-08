var dep = require('./dep');
exports.answer = dep.value + 1;
module.exports.keywordNames = {export: 1, import: 2};
module.exports.keywordPropertyAccess = ({import: {meta: 7}}).import.meta;
const asyncArrow = async () => await Promise.resolve(100);
exports.asyncArrowType = typeof asyncArrow;
exports.moduleId = module.id;
exports.requireId = require.id;
exports.thisIsExports = this === exports;
