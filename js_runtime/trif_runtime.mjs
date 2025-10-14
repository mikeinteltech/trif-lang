export const runtime = {
  iterate(value) {
    if (value instanceof Map) {
      return value.entries();
    }
    return value;
  },
  makeMap(pairs) {
    return new Map(pairs);
  },
  spawn(callable) {
    setTimeout(() => callable(), 0);
  },
  defaultEntryPoint(scope) {
    if (typeof scope.main === 'function') {
      scope.main();
    }
  },
  importModule(name) {
    throw new Error(`Dynamic module loading not available in JS runtime for ${name}`);
  }
};
