const syntaxLookingText = "import value from './missing.js'; export default value; await value;";
/* export const ignored = 1; import ignored from './ignored.js'; */
module.exports = {
  value: 40,
  moduleId: module.id,
  requireId: require.id,
  thisIsExports: this === exports,
  syntaxLookingText,
};
