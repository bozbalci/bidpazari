var UglifyJsPlugin = require('uglifyjs-webpack-plugin');

var baseConfig = require('./base');

baseConfig.mode = 'production';

baseConfig.optimization.minimizer = [new UglifyJsPlugin()];

module.exports = baseConfig;
