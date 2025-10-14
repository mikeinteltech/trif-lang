export const runtime = {
  _exports: new Map(),
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
  registerModuleExports(exports, defaultValue) {
    this._exports.set('current', { exports, default: defaultValue });
  },
  extractExport(module, name) {
    if (module && name in module) {
      return module[name];
    }
    return undefined;
  },
  extractDefault(module) {
    if (module && 'default' in module) {
      return module.default;
    }
    return module;
  },
  importModule(name) {
    throw new Error(`Dynamic module loading not available in JS runtime for ${name}`);
  }
};
