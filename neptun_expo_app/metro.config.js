const path = require('path');
const fs = require('fs');
const { getDefaultConfig } = require('expo/metro-config');
const { resolve: metroResolve } = require('metro-resolver');

/** @type {import('expo/metro-config').MetroConfig} */
const config = getDefaultConfig(__dirname);

const originalResolveRequest = config.resolver.resolveRequest;
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (moduleName.endsWith('.geojson')) {
    const originDir = path.dirname(context.originModulePath);
    const geoPath = path.resolve(originDir, moduleName);
    if (fs.existsSync(geoPath)) {
      return { type: 'sourceFile', filePath: geoPath };
    }
    const jsonName = moduleName.replace(/\.geojson$/, '.json');
    if (originalResolveRequest) {
      return originalResolveRequest(context, jsonName, platform);
    }
    return metroResolve(context, jsonName, platform);
  }
  if (originalResolveRequest) {
    return originalResolveRequest(context, moduleName, platform);
  }
  return metroResolve(context, moduleName, platform);
};

module.exports = config;
