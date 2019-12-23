var path = require('path');
var webpack = require('webpack');
var BundleTracker = require('webpack-bundle-tracker');

module.exports = {
  context: __dirname,

  entry: ['entry/main'],

  output: {
    path: path.resolve(__dirname, '../../build/bidpazari/js/webpack'),
    publicPath: '/staticx/bidpazari/js/webpack/',
    filename: '[name]-[hash].js',
    chunkFilename: '[name].[chunkhash].js',
  },

  plugins: [
    new webpack.HotModuleReplacementPlugin(),
    new webpack.NoEmitOnErrorsPlugin(),
    new BundleTracker({
      filename: 'build/bidpazari/js/webpack/webpack-stats.json',
    }),
  ],

  module: {
    rules: [
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
      {
        test: /\.less$/,
        use: [
          {
            loader: 'style-loader',
          },
          {
            loader: 'css-loader',
            options: {
              sourceMap: true,
              modules: {
                localIdentName: '[name]__[local]___[hash:base64:5]',
              },
            },
          },
          {
            loader: 'less-loader',
          },
        ],
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
    modules: [path.resolve(__dirname, '../../src/js'), 'node_modules'],
    extensions: ['.js', '.jsx'],
  },
};
