var path = require('path');
var webpack = require('webpack');
var MiniCssExtractPlugin = require('mini-css-extract-plugin');
var BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;
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
    // Uncomment the following line to analyze bundles.
    // new BundleAnalyzerPlugin(),
    new webpack.HotModuleReplacementPlugin(),
    new webpack.NoEmitOnErrorsPlugin(),
    new MiniCssExtractPlugin({
      chunkFilename: '[name].[contenthash].css',
      filename: '[name].[contenthash].css',
      ignoreOrder: true,
    }),
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
        test: /\.global\.scss$/,
        use: [
          {
            loader: MiniCssExtractPlugin.loader,
          },
          {
            loader: 'css-loader',
          },
          {
            loader: 'postcss-loader',
            options: {
              plugins: function() {
                return [require('autoprefixer')];
              },
            },
          },
          {
            loader: 'sass-loader',
          },
        ],
      },
      {
        test: /\.(scss)$/,
        exclude: [/\.global\.scss$/],
        use: [
          {
            loader: MiniCssExtractPlugin.loader,
          },
          {
            loader: 'css-loader',
            options: {
              modules: {
                localIdentName: '[name]__[local]___[hash:base64:5]',
              },
            },
          },
          {
            loader: 'postcss-loader',
            options: {
              plugins: function() {
                return [require('autoprefixer')];
              },
            },
          },
          {
            loader: 'sass-loader',
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
    modules: [
      path.resolve(__dirname, '../../src/js'),
      path.resolve(__dirname, '../../src/scss'),
      'node_modules',
    ],
    extensions: ['.js', '.jsx', '.scss'],
  },
};
