var path = require('path');
var webpack = require('webpack');
var BundleTracker = require('webpack-bundle-tracker');

module.exports = {
  context: __dirname,

  entry: ['entry/main'],

  output: {
    path: path.resolve('./static/build/'),
    // publicPath: '/static/build/',
    publicPath: 'http://localhost:3000/static/build/',
    filename: '[name]-[hash].js',
    chunkFilename: '[name].[chunkhash].js',
  },

  plugins: [
    new webpack.HotModuleReplacementPlugin(),
    new webpack.NoEmitOnErrorsPlugin(),
    new BundleTracker({filename: './webpack-stats.json'}),
  ],

  module: {
    rules: [
      {
        test: /\.css$/i,
        use: ['style-loader', 'css-loader'],
      },
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env', '@babel/preset-react'],
            plugins: [
              [
                '@babel/plugin-proposal-decorators',
                {
                  legacy: true,
                },
              ],
              [
                '@babel/plugin-proposal-class-properties',
                {
                  loose: true,
                },
              ],
            ],
          },
        },
      },
    ],
  },

  optimization: {
    splitChunks: {
      minSize: 100 * 1024,
      cacheGroups: {
        'main-vendor': {
          chunks: chunk => chunk.name === 'main',
          minChunks: 1,
          name: 'main-vendor',
          test: /[\\/]node_modules[\\/]/i,
          // TODO This is a hack, get rid of it.
          enforce: true,
        },
      },
    },
  },

  resolve: {
    modules: [path.resolve(__dirname, './js'), 'node_modules'],
    extensions: ['.js', '.jsx'],
  },

  mode: 'development',
};
